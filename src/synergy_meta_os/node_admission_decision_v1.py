from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .manifest import canonical_json
from .node_build_lock_consumer_v1 import evaluate_research_node_readiness


class NodeAdmissionDecisionError(ValueError):
    pass


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA = "synergy.node-admission-decision/v1"


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise NodeAdmissionDecisionError("evaluated_at must use UTC Z form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise NodeAdmissionDecisionError("invalid evaluated_at") from exc
    if parsed.tzinfo != timezone.utc:
        raise NodeAdmissionDecisionError("evaluated_at must be UTC")
    return parsed


def decision_digest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("decision_digest", None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


def build_node_admission_decision_v1(
    *,
    profile: dict[str, Any],
    source_lock: dict[str, Any],
    signed_manifest: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
    evaluated_at: datetime,
) -> dict[str, Any]:
    if evaluated_at.tzinfo is None:
        raise NodeAdmissionDecisionError("evaluated_at must be timezone-aware")
    evaluated_at = evaluated_at.astimezone(timezone.utc)
    readiness = evaluate_research_node_readiness(
        profile=profile,
        source_lock=source_lock,
        signed_manifest=signed_manifest,
        key_resolver=key_resolver,
        now=evaluated_at,
    )
    body = signed_manifest["body"]
    profile_status = readiness.profile_status
    if profile_status == "PROFILE_CONFORMANT":
        admission_status = "BLOCKED_BUILD_EVIDENCE"
    else:
        admission_status = "BLOCKED_PROFILE"
    payload = {
        "schema": _SCHEMA,
        "node_id": body["node_id"],
        "manifest_generation": body["generation"],
        "manifest_body_digest": signed_manifest["body_digest"],
        "profile_digest": readiness.profile_digest,
        "source_lock_digest": readiness.source_lock_digest,
        "evaluated_at": evaluated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile_status": profile_status,
        "source_lock_status": readiness.source_lock_status,
        "build_evidence_status": readiness.build_evidence_status,
        "admission_status": admission_status,
        "blockers": list(readiness.blockers),
        "financial_authority": "NONE",
        "payment_authority": "NONE",
        "accounting_authority": "NONE",
        "execution_authority": "NONE",
    }
    payload["decision_digest"] = decision_digest(payload)
    return payload


def verify_node_admission_decision_v1(
    payload: dict[str, Any],
    *,
    profile: dict[str, Any],
    source_lock: dict[str, Any],
    signed_manifest: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
) -> dict[str, Any]:
    expected = {
        "schema", "node_id", "manifest_generation", "manifest_body_digest",
        "profile_digest", "source_lock_digest", "evaluated_at", "profile_status",
        "source_lock_status", "build_evidence_status", "admission_status", "blockers",
        "financial_authority", "payment_authority", "accounting_authority",
        "execution_authority", "decision_digest"
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise NodeAdmissionDecisionError("unexpected node-admission shape")
    if payload["schema"] != _SCHEMA:
        raise NodeAdmissionDecisionError("unexpected node-admission schema")
    generation = payload["manifest_generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or not (1 <= generation <= 2**53 - 1):
        raise NodeAdmissionDecisionError("manifest_generation must be positive safe integer")
    for field in ("manifest_body_digest", "profile_digest", "source_lock_digest", "decision_digest"):
        value = payload[field]
        if not isinstance(value, str) or not _HEX64.fullmatch(value):
            raise NodeAdmissionDecisionError(f"{field} must be lowercase sha256")
    blockers = payload["blockers"]
    if not isinstance(blockers, list) or blockers != sorted(set(blockers)):
        raise NodeAdmissionDecisionError("blockers must be sorted unique")
    for field in ("financial_authority", "payment_authority", "accounting_authority", "execution_authority"):
        if payload[field] != "NONE":
            raise NodeAdmissionDecisionError(f"admission decision cannot grant {field}")
    evaluated_at = _parse_utc(payload["evaluated_at"])
    rebuilt = build_node_admission_decision_v1(
        profile=profile,
        source_lock=source_lock,
        signed_manifest=signed_manifest,
        key_resolver=key_resolver,
        evaluated_at=evaluated_at,
    )
    if payload != rebuilt:
        raise NodeAdmissionDecisionError("node-admission decision does not match raw evidence")
    if payload["decision_digest"] != decision_digest(payload):
        raise NodeAdmissionDecisionError("node-admission decision digest mismatch")
    return payload
