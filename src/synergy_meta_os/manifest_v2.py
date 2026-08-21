from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .capability_registry_consumer_v1 import canonical_json, verify_capability_registry_v1


class ManifestV2Error(ValueError):
    pass


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ManifestV2Error("timestamps must use RFC3339 UTC Z form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestV2Error("invalid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise ManifestV2Error("timestamp must be UTC")
    return parsed


def _digest(value: str, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise ManifestV2Error(f"{label} must be lowercase sha256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ManifestV2Error(f"{label} must be lowercase sha256 hex") from exc


def validate_manifest_body_v2(body: dict[str, Any], registry: dict[str, Any], *, now: datetime | None = None) -> str:
    registry_digest, cap_map, kind_map = verify_capability_registry_v1(registry)
    expected = {"schema", "node_id", "generation", "issued_at", "expires_at", "capability_registry_digest", "capabilities", "services"}
    if set(body) != expected:
        raise ManifestV2Error("unexpected manifest v2 body shape")
    if body["schema"] != "synergy.node-manifest/v2":
        raise ManifestV2Error("unexpected manifest v2 schema")
    if not isinstance(body["node_id"], str) or not body["node_id"]:
        raise ManifestV2Error("node_id is required")
    generation = body["generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or not 1 <= generation <= 2**53 - 1:
        raise ManifestV2Error("generation must be a positive safe integer")
    issued = _utc(body["issued_at"])
    expires = _utc(body["expires_at"])
    if expires <= issued:
        raise ManifestV2Error("expires_at must follow issued_at")
    if now is not None:
        if now.tzinfo is None:
            raise ManifestV2Error("now must be timezone-aware")
        if now.astimezone(timezone.utc) >= expires:
            raise ManifestV2Error("manifest expired")
    _digest(body["capability_registry_digest"], "capability_registry_digest")
    if body["capability_registry_digest"] != registry_digest:
        raise ManifestV2Error("manifest pins a different capability registry")

    caps = body["capabilities"]
    if not isinstance(caps, list) or caps != sorted(set(caps)) or any(cap not in cap_map for cap in caps):
        raise ManifestV2Error("capabilities must be sorted, unique and registry-known")
    cap_set = set(caps)

    services = body["services"]
    if not isinstance(services, list):
        raise ManifestV2Error("services must be a list")
    ids: list[str] = []
    for service in services:
        expected_service = {"service_id", "kind", "repository", "artifact_digest", "required_capabilities", "desired_state"}
        if not isinstance(service, dict) or set(service) != expected_service:
            raise ManifestV2Error("unexpected service shape")
        sid = service["service_id"]
        if not isinstance(sid, str) or not sid:
            raise ManifestV2Error("service_id is required")
        ids.append(sid)
        kind = service["kind"]
        if kind not in kind_map:
            raise ManifestV2Error("unknown service kind")
        contract = kind_map[kind]
        if service["repository"] != contract["repository"]:
            raise ManifestV2Error("service repository does not match capability registry")
        if service["required_capabilities"] != contract["required_capabilities"]:
            raise ManifestV2Error("service capabilities do not exactly match registry contract")
        if any(cap not in cap_set for cap in service["required_capabilities"]):
            raise ManifestV2Error("node lacks required service capability")
        _digest(service["artifact_digest"], "artifact_digest")
        if service["desired_state"] not in {"ENABLED", "DISABLED"}:
            raise ManifestV2Error("unknown desired state")
    if ids != sorted(set(ids)):
        raise ManifestV2Error("services must be sorted by unique service_id")
    canonical_json(body)
    return registry_digest


def sign_manifest_v2(body: dict[str, Any], registry: dict[str, Any], private_key: Ed25519PrivateKey, *, key_id: str) -> dict[str, Any]:
    validate_manifest_body_v2(body, registry)
    if not isinstance(key_id, str) or not key_id:
        raise ManifestV2Error("key_id is required")
    body_bytes = canonical_json(body)
    signature = private_key.sign(body_bytes)
    return {
        "body": body,
        "signature": {"algorithm": "Ed25519", "key_id": key_id, "value_b64": base64.b64encode(signature).decode("ascii")},
        "body_digest": hashlib.sha256(body_bytes).hexdigest(),
        "execution_authority": "NONE",
    }


def verify_manifest_v2(envelope: dict[str, Any], registry: dict[str, Any], key_resolver: Callable[[str], Ed25519PublicKey], *, now: datetime | None = None) -> dict[str, Any]:
    if set(envelope) != {"body", "signature", "body_digest", "execution_authority"}:
        raise ManifestV2Error("unexpected signed manifest v2 envelope shape")
    if envelope["execution_authority"] != "NONE":
        raise ManifestV2Error("manifest does not execute services")
    body = envelope["body"]
    if not isinstance(body, dict):
        raise ManifestV2Error("body must be an object")
    validate_manifest_body_v2(body, registry, now=now)
    body_bytes = canonical_json(body)
    if hashlib.sha256(body_bytes).hexdigest() != envelope["body_digest"]:
        raise ManifestV2Error("body digest mismatch")
    signature = envelope["signature"]
    if not isinstance(signature, dict) or set(signature) != {"algorithm", "key_id", "value_b64"} or signature["algorithm"] != "Ed25519":
        raise ManifestV2Error("invalid signature descriptor")
    try:
        raw = base64.b64decode(signature["value_b64"], validate=True)
        key_resolver(signature["key_id"]).verify(raw, body_bytes)
    except Exception as exc:
        raise ManifestV2Error("signature verification failed") from exc
    return body


@dataclass(frozen=True)
class ServiceDecisionV2:
    service_id: str
    state: str


def reconcile_services_v2(body: dict[str, Any], registry: dict[str, Any]) -> tuple[ServiceDecisionV2, ...]:
    validate_manifest_body_v2(body, registry)
    return tuple(
        ServiceDecisionV2(service["service_id"], "DISABLED" if service["desired_state"] == "DISABLED" else "RUNNABLE")
        for service in body["services"]
    )
