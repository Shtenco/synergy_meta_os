from __future__ import annotations

import base64
import ctypes
import fcntl
import hashlib
import json
import os
import re
import resource
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


SAFE_INT_MAX = 2**53 - 1
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SERVICE_ID = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
NODE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,126}$")

MANIFEST_SCHEMA = "synergy.node-manifest/v31"
GRANT_SCHEMA = "synergy.activation-grant/v1"
CAPABILITY_SCHEMA = "synergy.capability-registry/v31"
STATE_SCHEMA = "synergy.supervisor-state/v31"
AUDIT_SCHEMA = "synergy.audit-record/v31"


class ManifestError(ValueError):
    pass


class ActivationError(RuntimeError):
    pass


def _safe_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > SAFE_INT_MAX:
            raise ManifestError("integer exceeds deterministic JSON safe range")
        return
    if isinstance(value, float):
        raise ManifestError("floating point values are forbidden in signed/state bytes")
    if isinstance(value, list):
        for item in value:
            _safe_json(item)
        return
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ManifestError("object keys must be strings")
        for item in value.values():
            _safe_json(item)
        return
    raise ManifestError(f"unsupported canonical value: {type(value)!r}")


def canonical_json(value: Any) -> bytes:
    _safe_json(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: bytes | bytearray | memoryview) -> str:
    return hashlib.sha256(bytes(value)).hexdigest()


def object_digest(value: Any) -> str:
    return sha256_hex(canonical_json(value))


def _hex(value: Any, size: int, label: str) -> str:
    regex = HEX40 if size == 40 else HEX64
    if not isinstance(value, str) or regex.fullmatch(value) is None:
        raise ManifestError(f"{label} must be lowercase hex{size}")
    return value


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ManifestError(f"{label} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise ManifestError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _validate_window(issued_at: Any, expires_at: Any, now: datetime | None) -> None:
    issued = _parse_utc(issued_at, "issued_at")
    expires = _parse_utc(expires_at, "expires_at")
    if expires <= issued:
        raise ManifestError("expires_at must follow issued_at")
    if (expires - issued).total_seconds() > 7 * 24 * 3600:
        raise ManifestError("signed object lifetime exceeds seven days")
    check = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if check < issued:
        raise ManifestError("signed object is not valid yet")
    if check >= expires:
        raise ManifestError("signed object expired")


CAPABILITY_REGISTRY: dict[str, Any] = {
    "schema": CAPABILITY_SCHEMA,
    "execution_authority": "NONE",
    "capabilities": {
        "agents.propose": {"risk": "MEDIUM", "authority": "PROPOSAL_ONLY"},
        "audio.output": {"risk": "LOW", "authority": "DEVICE_BOUNDED"},
        "blockchain.read": {"risk": "LOW", "authority": "READ_ONLY"},
        "blockchain.validate": {"risk": "HIGH", "authority": "CONSENSUS_BOUNDED"},
        "content.cache": {"risk": "LOW", "authority": "CONTENT_BOUNDED"},
        "display.present": {"risk": "LOW", "authority": "SURFACE_BOUNDED"},
        "finance.execute": {"risk": "CRITICAL", "authority": "FINANCIAL"},
        "finance.read": {"risk": "MEDIUM", "authority": "READ_ONLY"},
        "input.receive": {"risk": "MEDIUM", "authority": "FOCUS_BOUNDED"},
        "network.connect": {"risk": "MEDIUM", "authority": "NETWORK_BOUNDED"},
        "network.listen": {"risk": "MEDIUM", "authority": "NETWORK_BOUNDED"},
        "nexus.infer": {"risk": "MEDIUM", "authority": "INFERENCE_ONLY"},
        "observability.emit": {"risk": "LOW", "authority": "TELEMETRY_ONLY"},
        "storage.read": {"risk": "LOW", "authority": "OBJECT_BOUNDED"},
        "storage.write": {"risk": "MEDIUM", "authority": "OBJECT_BOUNDED"},
        "treasury.sign": {"risk": "CRITICAL", "authority": "TREASURY"},
        "ui.present": {"risk": "LOW", "authority": "PRESENTATION_ONLY"},
        "update.activate": {"risk": "HIGH", "authority": "LIFECYCLE_ONLY"},
        "update.stage": {"risk": "MEDIUM", "authority": "LIFECYCLE_ONLY"},
    },
}


def capability_registry_digest() -> str:
    return object_digest(CAPABILITY_REGISTRY)


KNOWN_PROFILES = {
    "EDGE_CLIENT",
    "P2P_RELAY",
    "CONTENT_CACHE",
    "NEXUS_COMPUTE",
    "BLOCKCHAIN_PEER",
    "BLOCKCHAIN_VALIDATOR",
    "METAPAY_GATEWAY",
    "FINANCIAL_SERVICE",
    "BUSINESS_AUTOPILOT",
    "FULL_SYNERGY_NODE",
}

HIGH_VALUE_PROFILES = {
    "BLOCKCHAIN_VALIDATOR",
    "METAPAY_GATEWAY",
    "FINANCIAL_SERVICE",
    "FULL_SYNERGY_NODE",
}

KIND_REQUIRED = {
    "SYNERGYNET": {"network.connect", "network.listen", "observability.emit"},
    "CONTENT_CACHE": {"content.cache", "storage.read", "storage.write", "observability.emit"},
    "NEXUS": {"nexus.infer", "storage.read", "observability.emit"},
    "AUTOPILOT": {"agents.propose", "nexus.infer", "storage.read", "observability.emit"},
    "BLOCKCHAIN_PEER": {"blockchain.read", "network.connect", "network.listen", "storage.read", "observability.emit"},
    "BLOCKCHAIN_VALIDATOR": {"blockchain.read", "blockchain.validate", "network.connect", "network.listen", "storage.read", "storage.write", "observability.emit"},
    "METAPAY": {"finance.read", "network.connect", "observability.emit"},
    "FINANCIAL_OS": {"finance.read", "storage.read", "observability.emit"},
    "UI": {"ui.present", "display.present", "input.receive", "observability.emit"},
    "DIAGNOSTICS": {"observability.emit"},
}

KIND_CEILING = {
    "SYNERGYNET": {"network.connect", "network.listen", "storage.read", "storage.write", "content.cache", "observability.emit"},
    "CONTENT_CACHE": {"network.connect", "network.listen", "storage.read", "storage.write", "content.cache", "observability.emit"},
    "NEXUS": {"storage.read", "nexus.infer", "observability.emit"},
    "AUTOPILOT": {"network.connect", "storage.read", "storage.write", "nexus.infer", "agents.propose", "observability.emit"},
    "BLOCKCHAIN_PEER": {"network.connect", "network.listen", "storage.read", "storage.write", "blockchain.read", "observability.emit"},
    "BLOCKCHAIN_VALIDATOR": {"network.connect", "network.listen", "storage.read", "storage.write", "blockchain.read", "blockchain.validate", "observability.emit"},
    "METAPAY": {"network.connect", "network.listen", "storage.read", "storage.write", "finance.read", "finance.execute", "observability.emit"},
    "FINANCIAL_OS": {"network.connect", "storage.read", "storage.write", "finance.read", "finance.execute", "treasury.sign", "observability.emit"},
    "UI": {"ui.present", "display.present", "input.receive", "audio.output", "observability.emit"},
    "DIAGNOSTICS": {"storage.read", "observability.emit"},
}

DANGEROUS_CAPS = {
    "blockchain.validate",
    "finance.execute",
    "treasury.sign",
    "update.activate",
}


def _sorted_unique_strings(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ManifestError(f"{label} must be a string list")
    if not allow_empty and not value:
        raise ManifestError(f"{label} cannot be empty")
    if value != sorted(set(value)):
        raise ManifestError(f"{label} must be sorted and unique")
    return value


def _validate_key_ref(value: str, *, development: bool) -> None:
    lowered = value.lower()
    forbidden = ("begin ", "\\", "../", ".pem", ".key", ".ppk", "private-key")
    if any(part in lowered for part in forbidden) or any(ch.isspace() for ch in value):
        raise ManifestError("raw/path-like key material is forbidden")
    allowed = ("tpm2://", "pkcs11:", "vault://", "kernel-keyring://")
    if development:
        allowed += ("dev://",)
    if not value.startswith(allowed):
        raise ManifestError("key reference must use an approved non-raw provider URI")


def _validate_limits(value: Any) -> None:
    expected = {"memory_mib", "cpu_seconds", "open_files", "processes", "file_mib"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ManifestError("service limits must use the exact v31 shape")
    checks = {
        "memory_mib": (16, 65536),
        "cpu_seconds": (1, 86400),
        "open_files": (16, 65536),
        "processes": (1, 4096),
        "file_mib": (1, 1048576),
    }
    for key, (low, high) in checks.items():
        item = value[key]
        if isinstance(item, bool) or not isinstance(item, int) or not (low <= item <= high):
            raise ManifestError(f"service limit {key} is out of range")


def _topological_services(services: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(item["service_id"]): dict(item) for item in services}
    incoming = {sid: set(item["depends_on"]) for sid, item in by_id.items()}
    for sid, dependencies in incoming.items():
        if sid in dependencies:
            raise ManifestError("service cannot depend on itself")
        unknown = dependencies - set(by_id)
        if unknown:
            raise ManifestError(f"service {sid} has unknown dependencies: {sorted(unknown)}")
    ready = sorted(sid for sid, deps in incoming.items() if not deps)
    result: list[dict[str, Any]] = []
    while ready:
        sid = ready.pop(0)
        result.append(by_id[sid])
        for other in sorted(incoming):
            if sid in incoming[other]:
                incoming[other].remove(sid)
                if not incoming[other] and other not in {x["service_id"] for x in result} and other not in ready:
                    ready.append(other)
                    ready.sort()
    if len(result) != len(by_id):
        raise ManifestError("service dependency graph contains a cycle")
    return result


def _validate_service(service: Any, *, development: bool, attestation_level: str) -> None:
    expected = {
        "service_id",
        "kind",
        "repository",
        "artifact_digest",
        "argv",
        "capabilities",
        "depends_on",
        "desired_state",
        "limits",
        "health",
        "key_refs",
    }
    if not isinstance(service, dict) or set(service) != expected:
        raise ManifestError("service must use the exact v31 shape")
    sid = service["service_id"]
    if not isinstance(sid, str) or SERVICE_ID.fullmatch(sid) is None:
        raise ManifestError("invalid service_id")
    kind = service["kind"]
    if kind not in KIND_REQUIRED:
        raise ManifestError("unknown service kind")
    repository = service["repository"]
    if not isinstance(repository, str) or not repository.startswith("Shtenco/") or repository.count("/") != 1:
        raise ManifestError("service repository must be an explicit Shtenco/owner pair")
    _hex(service["artifact_digest"], 64, "artifact_digest")
    argv = service["argv"]
    if not isinstance(argv, list) or not argv or argv[0] != "$ARTIFACT":
        raise ManifestError("argv must be non-empty and start with $ARTIFACT")
    if any(not isinstance(arg, str) or not arg or "\x00" in arg for arg in argv):
        raise ManifestError("argv contains invalid values")
    capabilities = set(_sorted_unique_strings(service["capabilities"], "capabilities", allow_empty=False))
    known = set(CAPABILITY_REGISTRY["capabilities"])
    if not capabilities <= known:
        raise ManifestError("unknown service capability")
    if not KIND_REQUIRED[kind] <= capabilities:
        raise ManifestError(f"{sid} omits a mandatory {kind} capability")
    if not capabilities <= KIND_CEILING[kind]:
        raise ManifestError(f"{sid} attempts cross-authority capability escalation")
    if capabilities & DANGEROUS_CAPS and attestation_level != "HARDWARE":
        raise ManifestError(f"{sid} dangerous capabilities require hardware attestation")
    _sorted_unique_strings(service["depends_on"], "depends_on")
    if service["desired_state"] not in {"ENABLED", "DISABLED"}:
        raise ManifestError("desired_state must be ENABLED or DISABLED")
    _validate_limits(service["limits"])
    health = service["health"]
    if not isinstance(health, dict) or set(health) != {"kind", "grace_ms"}:
        raise ManifestError("health must use the exact v31 shape")
    if health["kind"] != "process_alive":
        raise ManifestError("v31 supports only the fail-closed process_alive health probe")
    if isinstance(health["grace_ms"], bool) or not isinstance(health["grace_ms"], int) or not (10 <= health["grace_ms"] <= 60000):
        raise ManifestError("health grace_ms is out of range")
    key_refs = _sorted_unique_strings(service["key_refs"], "key_refs")
    for ref in key_refs:
        _validate_key_ref(ref, development=development)


def validate_manifest_body(body: Any, *, now: datetime | None = None) -> dict[str, Any]:
    expected = {
        "schema",
        "node_id",
        "generation",
        "issued_at",
        "expires_at",
        "profile",
        "development",
        "attestation",
        "host_lock",
        "capability_registry_digest",
        "services",
        "execution_authority",
        "financial_authority",
        "payment_authority",
        "accounting_authority",
    }
    if not isinstance(body, dict) or set(body) != expected:
        raise ManifestError("manifest body must use the exact v31 shape")
    if body["schema"] != MANIFEST_SCHEMA:
        raise ManifestError("unsupported manifest schema")
    if not isinstance(body["node_id"], str) or NODE_ID.fullmatch(body["node_id"]) is None:
        raise ManifestError("invalid node_id")
    generation = body["generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or not (1 <= generation <= SAFE_INT_MAX):
        raise ManifestError("generation must be a positive safe integer")
    _validate_window(body["issued_at"], body["expires_at"], now)
    if body["profile"] not in KNOWN_PROFILES:
        raise ManifestError("unknown node profile")
    if not isinstance(body["development"], bool):
        raise ManifestError("development must be boolean")
    attestation = body["attestation"]
    if not isinstance(attestation, dict) or set(attestation) != {"level", "evidence_digest"}:
        raise ManifestError("attestation must use the exact v31 shape")
    if attestation["level"] not in {"NONE", "DEVELOPMENT", "HARDWARE"}:
        raise ManifestError("unknown attestation level")
    if attestation["level"] == "HARDWARE":
        _hex(attestation["evidence_digest"], 64, "attestation evidence_digest")
    elif attestation["evidence_digest"] is not None:
        raise ManifestError("non-hardware attestation cannot carry invented hardware evidence")
    if body["profile"] in HIGH_VALUE_PROFILES and attestation["level"] != "HARDWARE":
        raise ManifestError("high-value node profile requires hardware attestation")
    host = body["host_lock"]
    if not isinstance(host, dict) or set(host) != {"repository", "ref", "commit_sha", "release_sha256"}:
        raise ManifestError("host_lock must use the exact v31 shape")
    if host["repository"] != "Shtenco/turbo_linux" or not isinstance(host["ref"], str) or not host["ref"]:
        raise ManifestError("host_lock must pin Shtenco/turbo_linux and an explicit ref")
    _hex(host["commit_sha"], 40, "host commit_sha")
    _hex(host["release_sha256"], 64, "host release_sha256")
    if body["capability_registry_digest"] != capability_registry_digest():
        raise ManifestError("capability registry digest mismatch")
    services = body["services"]
    if not isinstance(services, list) or len(services) > 64:
        raise ManifestError("services must be a list of at most 64 domains")
    ids: list[str] = []
    for service in services:
        _validate_service(service, development=body["development"], attestation_level=attestation["level"])
        ids.append(service["service_id"])
    if ids != sorted(set(ids)):
        raise ManifestError("services must be sorted by unique service_id")
    _topological_services(services)
    for field in ("execution_authority", "financial_authority", "payment_authority", "accounting_authority"):
        if body[field] != "NONE":
            raise ManifestError(f"manifest cannot grant {field}")
    canonical_json(body)
    return body


def _sign(body: dict[str, Any], private_key: Ed25519PrivateKey, *, key_id: str, envelope_schema: str) -> dict[str, Any]:
    if not isinstance(key_id, str) or not key_id:
        raise ManifestError("key_id is required")
    payload = canonical_json(body)
    return {
        "schema": envelope_schema,
        "body": body,
        "body_digest": sha256_hex(payload),
        "signature": {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "value_b64": base64.b64encode(private_key.sign(payload)).decode("ascii"),
        },
    }


def _verify_signature(
    envelope: Any,
    key_resolver: Callable[[str], Ed25519PublicKey],
    *,
    envelope_schema: str,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or set(envelope) != {"schema", "body", "body_digest", "signature"}:
        raise ManifestError("signed envelope has an unexpected shape")
    if envelope["schema"] != envelope_schema:
        raise ManifestError("signed envelope schema mismatch")
    body = envelope["body"]
    payload = canonical_json(body)
    if envelope["body_digest"] != sha256_hex(payload):
        raise ManifestError("signed body digest mismatch")
    signature = envelope["signature"]
    if not isinstance(signature, dict) or set(signature) != {"algorithm", "key_id", "value_b64"}:
        raise ManifestError("signature has an unexpected shape")
    if signature["algorithm"] != "Ed25519":
        raise ManifestError("only Ed25519 is supported by the v31 node manifest")
    try:
        raw = base64.b64decode(signature["value_b64"], validate=True)
        public_key = key_resolver(signature["key_id"])
        if not isinstance(public_key, Ed25519PublicKey):
            raise TypeError("resolver did not return Ed25519PublicKey")
        public_key.verify(raw, payload)
    except Exception as exc:
        raise ManifestError("signature verification failed") from exc
    return body


def sign_manifest(body: dict[str, Any], private_key: Ed25519PrivateKey, *, key_id: str, now: datetime | None = None) -> dict[str, Any]:
    validate_manifest_body(body, now=now)
    return _sign(body, private_key, key_id=key_id, envelope_schema="synergy.signed-node-manifest/v31")


def verify_manifest(
    envelope: Any,
    key_resolver: Callable[[str], Ed25519PublicKey],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    body = _verify_signature(envelope, key_resolver, envelope_schema="synergy.signed-node-manifest/v31")
    return validate_manifest_body(body, now=now)


def validate_grant_body(body: Any, *, now: datetime | None = None) -> dict[str, Any]:
    expected = {
        "schema",
        "node_id",
        "manifest_body_digest",
        "manifest_generation",
        "allowed_services",
        "issued_at",
        "expires_at",
        "nonce",
        "action",
        "authority_scope",
        "financial_authority",
        "payment_authority",
        "accounting_authority",
        "blockchain_submission_authority",
    }
    if not isinstance(body, dict) or set(body) != expected:
        raise ManifestError("activation grant must use the exact v1 shape")
    if body["schema"] != GRANT_SCHEMA or body["action"] != "ACTIVATE_EXACT_MANIFEST":
        raise ManifestError("activation grant schema/action mismatch")
    if not isinstance(body["node_id"], str) or NODE_ID.fullmatch(body["node_id"]) is None:
        raise ManifestError("activation grant node_id is invalid")
    _hex(body["manifest_body_digest"], 64, "manifest_body_digest")
    generation = body["manifest_generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or not (1 <= generation <= SAFE_INT_MAX):
        raise ManifestError("manifest_generation must be a positive safe integer")
    _sorted_unique_strings(body["allowed_services"], "allowed_services")
    _validate_window(body["issued_at"], body["expires_at"], now)
    if not isinstance(body["nonce"], str) or len(body["nonce"]) < 16 or len(body["nonce"]) > 128:
        raise ManifestError("activation nonce length is invalid")
    if body["authority_scope"] != "NODE_LIFECYCLE_ONLY":
        raise ManifestError("activation grant authority scope is invalid")
    for field in ("financial_authority", "payment_authority", "accounting_authority", "blockchain_submission_authority"):
        if body[field] != "NONE":
            raise ManifestError(f"activation grant cannot grant {field}")
    canonical_json(body)
    return body


def sign_activation_grant(body: dict[str, Any], private_key: Ed25519PrivateKey, *, key_id: str, now: datetime | None = None) -> dict[str, Any]:
    validate_grant_body(body, now=now)
    return _sign(body, private_key, key_id=key_id, envelope_schema="synergy.signed-activation-grant/v1")


def verify_activation_grant(
    envelope: Any,
    key_resolver: Callable[[str], Ed25519PublicKey],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    body = _verify_signature(envelope, key_resolver, envelope_schema="synergy.signed-activation-grant/v1")
    return validate_grant_body(body, now=now)


def make_manifest(
    *,
    node_id: str,
    generation: int,
    issued_at: str,
    expires_at: str,
    profile: str,
    development: bool,
    attestation_level: str,
    attestation_evidence_digest: str | None,
    host_ref: str,
    host_commit_sha: str,
    host_release_sha256: str,
    services: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "node_id": node_id,
        "generation": generation,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "profile": profile,
        "development": development,
        "attestation": {"level": attestation_level, "evidence_digest": attestation_evidence_digest},
        "host_lock": {
            "repository": "Shtenco/turbo_linux",
            "ref": host_ref,
            "commit_sha": host_commit_sha,
            "release_sha256": host_release_sha256,
        },
        "capability_registry_digest": capability_registry_digest(),
        "services": [dict(item) for item in services],
        "execution_authority": "NONE",
        "financial_authority": "NONE",
        "payment_authority": "NONE",
        "accounting_authority": "NONE",
    }


def make_activation_grant(
    *,
    node_id: str,
    manifest_body_digest: str,
    manifest_generation: int,
    allowed_services: Sequence[str],
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, Any]:
    return {
        "schema": GRANT_SCHEMA,
        "node_id": node_id,
        "manifest_body_digest": manifest_body_digest,
        "manifest_generation": manifest_generation,
        "allowed_services": sorted(set(allowed_services)),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
        "action": "ACTIVATE_EXACT_MANIFEST",
        "authority_scope": "NODE_LIFECYCLE_ONLY",
        "financial_authority": "NONE",
        "payment_authority": "NONE",
        "accounting_authority": "NONE",
        "blockchain_submission_authority": "NONE",
    }


class ArtifactStore:
    """Immutable SHA-256 content store with atomic publication and read-back verification."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path_for(self, digest: str) -> Path:
        _hex(digest, 64, "artifact digest")
        return self.root / digest[:2] / digest[2:4] / digest

    def put(self, payload: bytes | bytearray | memoryview) -> str:
        data = bytes(payload)
        digest = sha256_hex(data)
        path = self.path_for(digest)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.exists():
            if path.is_symlink() or path.read_bytes() != data:
                raise ManifestError("artifact collision or store corruption")
            return digest
        fd, temp_name = tempfile.mkstemp(prefix=".artifact-", dir=path.parent)
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "wb", closefd=True) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp, 0o400)
            os.replace(temp, path)
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temp.exists():
                temp.unlink()
        return digest

    def has_verified(self, digest: str) -> bool:
        try:
            self.get_verified(digest)
            return True
        except (FileNotFoundError, ManifestError, OSError):
            return False

    def get_verified(self, digest: str) -> bytes:
        path = self.path_for(digest)
        if path.is_symlink() or not path.is_file():
            raise ManifestError("artifact missing or not a regular file")
        data = path.read_bytes()
        if sha256_hex(data) != digest:
            raise ManifestError("artifact store digest mismatch")
        return data

    def materialize_executable(self, digest: str, target: str | Path) -> Path:
        data = self.get_verified(digest)
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temp_name = tempfile.mkstemp(prefix=".exec-", dir=target_path.parent)
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "wb", closefd=True) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp, 0o500)
            os.replace(temp, target_path)
        finally:
            if temp.exists():
                temp.unlink()
        if sha256_hex(target_path.read_bytes()) != digest:
            raise ManifestError("materialized artifact verification failed")
        return target_path


class AuditChain:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def verify(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        previous = "0" * 64
        with self.path.open("rb") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.endswith(b"\n"):
                    raise ManifestError(f"audit line {line_number} is torn")
                try:
                    record = json.loads(line)
                except Exception as exc:
                    raise ManifestError(f"audit line {line_number} is invalid JSON") from exc
                expected = {"schema", "seq", "timestamp_ns", "event", "data", "previous_digest", "record_digest"}
                if not isinstance(record, dict) or set(record) != expected or record["schema"] != AUDIT_SCHEMA:
                    raise ManifestError("audit record shape/schema mismatch")
                supplied = record["record_digest"]
                _hex(supplied, 64, "record_digest")
                body = dict(record)
                body.pop("record_digest")
                if record["seq"] != line_number or record["previous_digest"] != previous:
                    raise ManifestError("audit sequence/chain mismatch")
                if object_digest(body) != supplied:
                    raise ManifestError("audit record digest mismatch")
                previous = supplied
                records.append(record)
        return records

    def append(self, event: str, **data: Any) -> dict[str, Any]:
        if not isinstance(event, str) or not event:
            raise ManifestError("audit event is required")
        canonical_json(data)
        lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            records = self.verify()
            previous = records[-1]["record_digest"] if records else "0" * 64
            body = {
                "schema": AUDIT_SCHEMA,
                "seq": len(records) + 1,
                # Decimal string avoids cross-language loss above JSON's 53-bit safe range.
                "timestamp_ns": str(time.time_ns()),
                "event": event,
                "data": data,
                "previous_digest": previous,
            }
            record = body | {"record_digest": object_digest(body)}
            with self.path.open("ab", buffering=0) as handle:
                handle.write(canonical_json(record) + b"\n")
                os.fsync(handle.fileno())
            return record
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)


class SupervisorState:
    """SQLite FULL-synchronous state plus an independently verifiable hash chain."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS manifests(
                    slot TEXT PRIMARY KEY CHECK(slot IN ('STAGED','ACTIVE','ROLLBACK')),
                    node_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    body_digest TEXT NOT NULL,
                    envelope_json BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generation_guard(
                    node_id TEXT PRIMARY KEY,
                    generation INTEGER NOT NULL,
                    body_digest TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS used_nonces(
                    nonce TEXT PRIMARY KEY,
                    grant_digest TEXT NOT NULL,
                    used_at_ns INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS state_history(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    payload_json BLOB NOT NULL,
                    previous_digest TEXT NOT NULL,
                    state_digest TEXT NOT NULL
                );
                """
            )
        os.chmod(self.path, 0o600)

    @staticmethod
    def _append_history(db: sqlite3.Connection, event: str, payload: Mapping[str, Any]) -> str:
        row = db.execute("SELECT seq,state_digest FROM state_history ORDER BY seq DESC LIMIT 1").fetchone()
        previous = row["state_digest"] if row else "0" * 64
        seq = (row["seq"] + 1) if row else 1
        body = {
            "schema": STATE_SCHEMA,
            "seq": seq,
            "event": event,
            "payload": dict(payload),
            "previous_digest": previous,
        }
        digest = object_digest(body)
        db.execute(
            "INSERT INTO state_history(seq,event,payload_json,previous_digest,state_digest) VALUES(?,?,?,?,?)",
            (seq, event, canonical_json(dict(payload)), previous, digest),
        )
        return digest

    def verify_history(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM state_history ORDER BY seq").fetchall()
        previous = "0" * 64
        result = []
        for expected_seq, row in enumerate(rows, 1):
            payload = json.loads(row["payload_json"])
            body = {
                "schema": STATE_SCHEMA,
                "seq": expected_seq,
                "event": row["event"],
                "payload": payload,
                "previous_digest": previous,
            }
            digest = object_digest(body)
            if row["seq"] != expected_seq or row["previous_digest"] != previous or row["state_digest"] != digest:
                raise ManifestError("durable state history chain mismatch")
            previous = digest
            result.append(body | {"state_digest": digest})
        return result

    def stage(self, envelope: Mapping[str, Any], body: Mapping[str, Any]) -> None:
        node_id = str(body["node_id"])
        generation = int(body["generation"])
        digest = str(envelope["body_digest"])
        encoded = canonical_json(dict(envelope))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            guard = db.execute("SELECT generation,body_digest FROM generation_guard WHERE node_id=?", (node_id,)).fetchone()
            if guard and generation < guard["generation"]:
                db.rollback()
                raise ManifestError("manifest generation rollback blocked")
            if guard and generation == guard["generation"] and digest != guard["body_digest"]:
                db.rollback()
                raise ManifestError("same active generation cannot change bytes")
            db.execute(
                "INSERT OR REPLACE INTO manifests(slot,node_id,generation,body_digest,envelope_json) VALUES('STAGED',?,?,?,?)",
                (node_id, generation, digest, encoded),
            )
            self._append_history(db, "MANIFEST_STAGED", {"node_id": node_id, "generation": generation, "body_digest": digest})
            db.commit()

    def load_slot(self, slot: str) -> dict[str, Any] | None:
        if slot not in {"STAGED", "ACTIVE", "ROLLBACK"}:
            raise ManifestError("invalid manifest slot")
        with self.connect() as db:
            row = db.execute("SELECT envelope_json FROM manifests WHERE slot=?", (slot,)).fetchone()
        return json.loads(row["envelope_json"]) if row else None

    def nonce_used(self, nonce: str) -> bool:
        with self.connect() as db:
            return db.execute("SELECT 1 FROM used_nonces WHERE nonce=?", (nonce,)).fetchone() is not None

    def commit_activation(self, *, expected_digest: str, nonce: str, grant_digest: str) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            staged = db.execute("SELECT * FROM manifests WHERE slot='STAGED'").fetchone()
            if staged is None or staged["body_digest"] != expected_digest:
                db.rollback()
                raise ActivationError("staged manifest changed before activation commit")
            if db.execute("SELECT 1 FROM used_nonces WHERE nonce=?", (nonce,)).fetchone():
                db.rollback()
                raise ActivationError("activation nonce replay blocked")
            active = db.execute("SELECT * FROM manifests WHERE slot='ACTIVE'").fetchone()
            if active is not None:
                db.execute(
                    "INSERT OR REPLACE INTO manifests(slot,node_id,generation,body_digest,envelope_json) VALUES('ROLLBACK',?,?,?,?)",
                    (active["node_id"], active["generation"], active["body_digest"], active["envelope_json"]),
                )
            db.execute(
                "INSERT OR REPLACE INTO manifests(slot,node_id,generation,body_digest,envelope_json) VALUES('ACTIVE',?,?,?,?)",
                (staged["node_id"], staged["generation"], staged["body_digest"], staged["envelope_json"]),
            )
            db.execute(
                "INSERT INTO generation_guard(node_id,generation,body_digest) VALUES(?,?,?) "
                "ON CONFLICT(node_id) DO UPDATE SET generation=excluded.generation,body_digest=excluded.body_digest",
                (staged["node_id"], staged["generation"], staged["body_digest"]),
            )
            db.execute(
                "INSERT INTO used_nonces(nonce,grant_digest,used_at_ns) VALUES(?,?,?)",
                (nonce, grant_digest, time.time_ns()),
            )
            db.execute("DELETE FROM manifests WHERE slot='STAGED'")
            self._append_history(
                db,
                "ACTIVATION_COMMITTED",
                {"node_id": staged["node_id"], "generation": staged["generation"], "body_digest": expected_digest, "grant_digest": grant_digest},
            )
            db.commit()

    def abort_staged_activation(self, *, expected_digest: str, reason: str) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            staged = db.execute("SELECT body_digest FROM manifests WHERE slot='STAGED'").fetchone()
            if staged is not None and staged["body_digest"] == expected_digest:
                self._append_history(db, "ACTIVATION_ABORTED", {"body_digest": expected_digest, "reason": reason})
            db.commit()

    def status(self) -> dict[str, Any]:
        with self.connect() as db:
            slots = {
                row["slot"]: {"node_id": row["node_id"], "generation": row["generation"], "body_digest": row["body_digest"]}
                for row in db.execute("SELECT slot,node_id,generation,body_digest FROM manifests")
            }
            nonces = db.execute("SELECT COUNT(*) AS n FROM used_nonces").fetchone()["n"]
        return {"schema": STATE_SCHEMA, "slots": slots, "used_nonces": nonces, "history_entries": len(self.verify_history())}


def _linux_preexec(limits: Mapping[str, int]) -> Callable[[], None]:
    def apply() -> None:
        os.setsid()
        os.umask(0o077)
        memory = int(limits["memory_mib"]) * 1024 * 1024
        file_bytes = int(limits["file_mib"]) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_CPU, (int(limits["cpu_seconds"]), int(limits["cpu_seconds"])))
        resource.setrlimit(resource.RLIMIT_NOFILE, (int(limits["open_files"]), int(limits["open_files"])))
        resource.setrlimit(resource.RLIMIT_NPROC, (int(limits["processes"]), int(limits["processes"])))
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
                raise OSError(ctypes.get_errno(), "PR_SET_NO_NEW_PRIVS")
        except AttributeError as exc:
            raise OSError("prctl unavailable") from exc
    return apply


@dataclass
class RunningService:
    service_id: str
    artifact_digest: str
    process: subprocess.Popen[bytes]
    runtime_dir: Path


class NodeSupervisor:
    """Compatibility supervisor. Native TURBO capability isolation remains a host responsibility."""

    def __init__(
        self,
        *,
        root: str | Path,
        manifest_key_resolver: Callable[[str], Ed25519PublicKey],
        governance_key_resolver: Callable[[str], Ed25519PublicKey],
    ):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.artifacts = ArtifactStore(self.root / "artifacts")
        self.state = SupervisorState(self.root / "state" / "supervisor.db")
        self.audit = AuditChain(self.root / "state" / "audit.jsonl")
        self.runtime_root = self.root / "runtime"
        self.runtime_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.manifest_key_resolver = manifest_key_resolver
        self.governance_key_resolver = governance_key_resolver
        self.running: dict[str, RunningService] = {}

    def stage(self, envelope: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        body = verify_manifest(dict(envelope), self.manifest_key_resolver, now=now)
        enabled = [service for service in body["services"] if service["desired_state"] == "ENABLED"]
        missing = [service["service_id"] for service in enabled if not self.artifacts.has_verified(service["artifact_digest"])]
        if missing:
            raise ManifestError(f"verified artifacts missing: {missing}")
        self.state.stage(dict(envelope), body)
        self.audit.append(
            "MANIFEST_ADMITTED",
            node_id=body["node_id"],
            generation=body["generation"],
            body_digest=envelope["body_digest"],
            status="ADMITTED",
            execution_authority="NONE",
        )
        return {
            "status": "ADMITTED",
            "launchable": True,
            "running": False,
            "production": False,
            "body_digest": envelope["body_digest"],
            "services": len(enabled),
        }

    def plan(self, *, now: datetime | None = None) -> dict[str, Any]:
        envelope = self.state.load_slot("STAGED")
        if envelope is None:
            raise ManifestError("no staged manifest")
        body = verify_manifest(envelope, self.manifest_key_resolver, now=now)
        order = _topological_services(body["services"])
        actions = []
        for service in order:
            current = self.running.get(service["service_id"])
            if service["desired_state"] == "DISABLED":
                action = "STOPPABLE" if current else "NOOP_STOPPED"
            elif current is None:
                action = "STARTABLE"
            elif current.artifact_digest == service["artifact_digest"] and current.process.poll() is None:
                action = "NOOP_RUNNING"
            else:
                action = "UPGRADE_PENDING"
            actions.append({"service_id": service["service_id"], "action": action, "execution_authority": "NONE"})
        return {
            "status": "LAUNCHABLE",
            "manifest_body_digest": envelope["body_digest"],
            "actions": actions,
            "activation_grant_required": True,
            "production": False,
        }

    def _spawn(self, service: Mapping[str, Any], generation: int) -> RunningService:
        sid = str(service["service_id"])
        runtime_dir = self.runtime_root / f"g{generation}" / sid
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir)
        runtime_dir.mkdir(parents=True, mode=0o700)
        artifact = self.artifacts.materialize_executable(service["artifact_digest"], runtime_dir / "artifact")
        argv = [str(artifact) if item == "$ARTIFACT" else str(item) for item in service["argv"]]
        env = {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "SYNERGY_SERVICE_ID": sid,
            "SYNERGY_CAPABILITIES": ",".join(service["capabilities"]),
            "SYNERGY_MANIFEST_AUTHORITY": "NONE",
            "SYNERGY_FINANCIAL_AUTHORITY": "NONE",
        }
        stdout_path = runtime_dir / "stdout.log"
        stderr_path = runtime_dir / "stderr.log"
        with stdout_path.open("ab", buffering=0) as stdout_handle, stderr_path.open("ab", buffering=0) as stderr_handle:
            process = subprocess.Popen(
                argv,
                cwd=runtime_dir,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                preexec_fn=_linux_preexec(service["limits"]),
                shell=False,
            )
        grace = service["health"]["grace_ms"] / 1000.0
        time.sleep(grace)
        if process.poll() is not None:
            process.wait(timeout=1)
            stdout = stdout_path.read_bytes()
            stderr = stderr_path.read_bytes()
            raise ActivationError(
                f"service {sid} failed health probe rc={process.returncode} "
                f"stdout={stdout[-160:]!r} stderr={stderr[-160:]!r}"
            )
        return RunningService(sid, service["artifact_digest"], process, runtime_dir)

    @staticmethod
    def _terminate(service: RunningService) -> None:
        if service.process.poll() is None:
            try:
                os.killpg(service.process.pid, signal.SIGTERM)
                service.process.wait(timeout=2)
            except Exception:
                try:
                    os.killpg(service.process.pid, signal.SIGKILL)
                    service.process.wait(timeout=2)
                except Exception:
                    pass

    def activate(self, grant_envelope: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        manifest_envelope = self.state.load_slot("STAGED")
        if manifest_envelope is None:
            raise ActivationError("no staged manifest")
        body = verify_manifest(manifest_envelope, self.manifest_key_resolver, now=now)
        grant = verify_activation_grant(dict(grant_envelope), self.governance_key_resolver, now=now)
        if grant["node_id"] != body["node_id"]:
            raise ActivationError("activation grant node mismatch")
        if grant["manifest_body_digest"] != manifest_envelope["body_digest"]:
            raise ActivationError("activation grant manifest mismatch")
        if grant["manifest_generation"] != body["generation"]:
            raise ActivationError("activation grant generation mismatch")
        enabled = sorted(service["service_id"] for service in body["services"] if service["desired_state"] == "ENABLED")
        if grant["allowed_services"] != enabled:
            raise ActivationError("activation grant must name the exact enabled service set")
        if self.state.nonce_used(grant["nonce"]):
            raise ActivationError("activation nonce replay blocked")

        order = [service for service in _topological_services(body["services"]) if service["desired_state"] == "ENABLED"]
        new_services: dict[str, RunningService] = {}
        try:
            for service in order:
                current = self.running.get(service["service_id"])
                if current and current.artifact_digest == service["artifact_digest"] and current.process.poll() is None:
                    continue
                new_services[service["service_id"]] = self._spawn(service, body["generation"])
                self.audit.append(
                    "SERVICE_HEALTHY",
                    service_id=service["service_id"],
                    pid=new_services[service["service_id"]].process.pid,
                    artifact_digest=service["artifact_digest"],
                    sandbox="LINUX_COMPAT_RLIMIT_NO_NEW_PRIVS",
                )
            grant_digest = str(grant_envelope["body_digest"])
            self.state.commit_activation(
                expected_digest=manifest_envelope["body_digest"],
                nonce=grant["nonce"],
                grant_digest=grant_digest,
            )
        except Exception as exc:
            for service in new_services.values():
                self._terminate(service)
            self.state.abort_staged_activation(expected_digest=manifest_envelope["body_digest"], reason=type(exc).__name__)
            self.audit.append(
                "ACTIVATION_ABORTED",
                body_digest=manifest_envelope["body_digest"],
                reason=type(exc).__name__,
                old_active_preserved=True,
            )
            raise

        desired = set(enabled)
        for sid, old in list(self.running.items()):
            replacement = new_services.get(sid)
            if sid not in desired or replacement is not None:
                self._terminate(old)
                self.running.pop(sid, None)
        self.running.update(new_services)
        self.audit.append(
            "MANIFEST_RUNNING",
            node_id=body["node_id"],
            generation=body["generation"],
            body_digest=manifest_envelope["body_digest"],
            services=enabled,
            production=False,
        )
        return {
            "status": "RUNNING",
            "manifest_body_digest": manifest_envelope["body_digest"],
            "services": enabled,
            "production": False,
            "sandbox_strength": "LINUX_COMPAT_RLIMIT_NO_NEW_PRIVS",
        }

    def observed_status(self) -> dict[str, Any]:
        processes = {
            sid: {
                "pid": service.process.pid,
                "alive": service.process.poll() is None,
                "artifact_digest": service.artifact_digest,
            }
            for sid, service in sorted(self.running.items())
        }
        active = self.state.load_slot("ACTIVE")
        return {
            "status": "RUNNING_OBSERVED" if processes and all(item["alive"] for item in processes.values()) else "ACTIVE_CONFIG_ONLY" if active else "STOPPED",
            "processes": processes,
            "active_manifest_digest": active["body_digest"] if active else None,
            "production": False,
        }

    def stop_all(self) -> None:
        for sid, service in list(self.running.items()):
            self._terminate(service)
            self.audit.append("SERVICE_STOPPED", service_id=sid, artifact_digest=service.artifact_digest)
        self.running.clear()

    def verify_evidence(self) -> dict[str, Any]:
        return {
            "state_history_entries": len(self.state.verify_history()),
            "audit_records": len(self.audit.verify()),
            "state": self.state.status(),
            "observed": self.observed_status(),
        }
