from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import hashlib
import json
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class ManifestError(ValueError):
    pass


_CAPABILITIES = {
    "P2P_RELAY",
    "CONTENT_CACHE",
    "NEXUS_COMPUTE",
    "BLOCKCHAIN_VALIDATOR",
    "METAPAY_GATEWAY",
    "FINANCIAL_SERVICE",
    "AUTOPILOT_SERVICE",
}
_SERVICE_KINDS = {
    "SYNERGYNET",
    "NEXUS",
    "BLOCKCHAIN",
    "METAPAY",
    "FINANCIAL_OS",
    "AUTOPILOT",
    "CONTENT_CACHE",
}
_REQUIRED_BY_KIND = {
    "SYNERGYNET": {"P2P_RELAY"},
    "NEXUS": {"NEXUS_COMPUTE"},
    "BLOCKCHAIN": {"BLOCKCHAIN_VALIDATOR"},
    "METAPAY": {"METAPAY_GATEWAY"},
    "FINANCIAL_OS": {"FINANCIAL_SERVICE"},
    "AUTOPILOT": {"AUTOPILOT_SERVICE"},
    "CONTENT_CACHE": {"CONTENT_CACHE"},
}


def _safe_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        if isinstance(value, bool) or abs(value) > 2**53 - 1:
            raise ManifestError("unsafe integer in manifest")
        return
    if isinstance(value, float):
        raise ManifestError("floating point values are forbidden in signed manifest bytes")
    if isinstance(value, list):
        for item in value:
            _safe_json(item)
        return
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ManifestError("manifest object keys must be strings")
        for item in value.values():
            _safe_json(item)
        return
    raise ManifestError(f"unsupported signed-manifest value: {type(value)!r}")


def canonical_json(value: Any) -> bytes:
    _safe_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ManifestError("timestamps must use RFC3339 UTC Z form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestError("invalid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise ManifestError("timestamp must be UTC")
    return parsed


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ManifestError(f"{label} must be sha256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ManifestError(f"{label} must be sha256 hex") from exc
    if value.lower() != value:
        raise ManifestError(f"{label} must be lowercase sha256 hex")


def _validate_body(body: dict[str, Any], *, now: datetime | None = None) -> None:
    expected = {"schema", "node_id", "generation", "issued_at", "expires_at", "capabilities", "services"}
    if set(body) != expected:
        raise ManifestError("unexpected manifest body shape")
    if body["schema"] != "synergy.node-manifest/v1":
        raise ManifestError("unexpected node manifest schema")
    if not isinstance(body["node_id"], str) or not body["node_id"]:
        raise ManifestError("node_id is required")
    generation = body["generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or not (1 <= generation <= 2**53 - 1):
        raise ManifestError("generation must be a positive safe integer")
    issued = _parse_utc(body["issued_at"])
    expires = _parse_utc(body["expires_at"])
    if expires <= issued:
        raise ManifestError("expires_at must follow issued_at")
    if now is not None:
        if now.tzinfo is None:
            raise ManifestError("now must be timezone-aware")
        if now.astimezone(timezone.utc) >= expires:
            raise ManifestError("manifest expired")
    caps = body["capabilities"]
    if not isinstance(caps, list) or caps != sorted(set(caps)) or any(cap not in _CAPABILITIES for cap in caps):
        raise ManifestError("capabilities must be sorted, unique and known")
    services = body["services"]
    if not isinstance(services, list):
        raise ManifestError("services must be a list")
    ids: set[str] = set()
    for service in services:
        expected_service = {"service_id", "kind", "repository", "artifact_digest", "required_capabilities", "desired_state"}
        if not isinstance(service, dict) or set(service) != expected_service:
            raise ManifestError("unexpected service shape")
        sid = service["service_id"]
        if not isinstance(sid, str) or not sid or sid in ids:
            raise ManifestError("service_id must be unique and non-empty")
        ids.add(sid)
        kind = service["kind"]
        if kind not in _SERVICE_KINDS:
            raise ManifestError("unknown service kind")
        if service["desired_state"] not in {"ENABLED", "DISABLED"}:
            raise ManifestError("unknown desired state")
        if not isinstance(service["repository"], str) or not service["repository"].startswith("Shtenco/"):
            raise ManifestError("service repository must be explicit")
        _validate_digest(service["artifact_digest"], "artifact_digest")
        required = service["required_capabilities"]
        if not isinstance(required, list) or required != sorted(set(required)):
            raise ManifestError("required capabilities must be sorted and unique")
        if any(cap not in _CAPABILITIES for cap in required):
            raise ManifestError("unknown required capability")
        if not _REQUIRED_BY_KIND[kind].issubset(set(required)):
            raise ManifestError("service omits mandatory capability for kind")
    canonical_json(body)


def sign_manifest(body: dict[str, Any], private_key: Ed25519PrivateKey, *, key_id: str) -> dict[str, Any]:
    _validate_body(body)
    if not isinstance(key_id, str) or not key_id:
        raise ManifestError("key_id is required")
    body_bytes = canonical_json(body)
    signature = private_key.sign(body_bytes)
    return {
        "body": body,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "value_b64": base64.b64encode(signature).decode("ascii"),
        },
        "body_digest": hashlib.sha256(body_bytes).hexdigest(),
        "execution_authority": "NONE",
    }


def verify_manifest(
    envelope: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    expected = {"body", "signature", "body_digest", "execution_authority"}
    if set(envelope) != expected:
        raise ManifestError("unexpected signed-manifest envelope shape")
    if envelope["execution_authority"] != "NONE":
        raise ManifestError("manifest bytes do not execute services by themselves")
    body = envelope["body"]
    if not isinstance(body, dict):
        raise ManifestError("body must be an object")
    _validate_body(body, now=now)
    body_bytes = canonical_json(body)
    if hashlib.sha256(body_bytes).hexdigest() != envelope["body_digest"]:
        raise ManifestError("manifest body digest mismatch")
    signature = envelope["signature"]
    if not isinstance(signature, dict) or set(signature) != {"algorithm", "key_id", "value_b64"}:
        raise ManifestError("unexpected signature shape")
    if signature["algorithm"] != "Ed25519":
        raise ManifestError("v1 bootstrap signature must be Ed25519")
    try:
        raw_signature = base64.b64decode(signature["value_b64"], validate=True)
    except Exception as exc:
        raise ManifestError("invalid base64 signature") from exc
    public_key = key_resolver(signature["key_id"])
    try:
        public_key.verify(raw_signature, body_bytes)
    except Exception as exc:
        raise ManifestError("signature verification failed") from exc
    return body


@dataclass(frozen=True)
class ServiceDecision:
    service_id: str
    state: str
    blockers: tuple[str, ...]


def reconcile_services(body: dict[str, Any]) -> tuple[ServiceDecision, ...]:
    _validate_body(body)
    capabilities = set(body["capabilities"])
    decisions: list[ServiceDecision] = []
    for service in body["services"]:
        if service["desired_state"] == "DISABLED":
            decisions.append(ServiceDecision(service["service_id"], "DISABLED", ()))
            continue
        missing = sorted(set(service["required_capabilities"]) - capabilities)
        if missing:
            decisions.append(ServiceDecision(service["service_id"], "BLOCKED_CAPABILITY", tuple(missing)))
        else:
            decisions.append(ServiceDecision(service["service_id"], "RUNNABLE", ()))
    return tuple(decisions)
