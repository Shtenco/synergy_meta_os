from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .node_build_lock_consumer_v2 import canonical_json
from .science_node_build_readiness_v2 import evaluate_pinned_science_source_readiness_v2


class NodeAdmissionDecisionV2Error(ValueError):
    pass


HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "synergy.node-admission-decision/v2"


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise NodeAdmissionDecisionV2Error("evaluated_at must use UTC Z form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise NodeAdmissionDecisionV2Error("invalid evaluated_at") from exc
    if parsed.tzinfo != timezone.utc:
        raise NodeAdmissionDecisionV2Error("evaluated_at must be UTC")
    return parsed


def decision_digest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("decision_digest", None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


def build_science_node_admission_decision_v2(
    *,
    profile: dict[str, Any],
    signed_manifest: dict[str, Any],
    capability_registry: dict[str, Any],
    build_lock: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
    evaluated_at: datetime,
) -> dict[str, Any]:
    if evaluated_at.tzinfo is None:
        raise NodeAdmissionDecisionV2Error("evaluated_at must be timezone-aware")
    evaluated_at = evaluated_at.astimezone(timezone.utc)
    readiness = evaluate_pinned_science_source_readiness_v2(
        profile=profile,
        signed_manifest=signed_manifest,
        capability_registry=capability_registry,
        build_lock=build_lock,
        key_resolver=key_resolver,
        now=evaluated_at,
    )
    body = signed_manifest["body"]
    if readiness.status == "BLOCKED_PROFILE":
        admission_status = "BLOCKED_PROFILE"
    elif readiness.status == "BLOCKED_BUILD_EVIDENCE":
        admission_status = "BLOCKED_BUILD_EVIDENCE"
    else:
        raise NodeAdmissionDecisionV2Error("v2 source-only generation cannot admit a node")
    payload = {
        "schema": SCHEMA,
        "node_id": body["node_id"],
        "manifest_generation": body["generation"],
        "manifest_body_digest": readiness.manifest_body_digest,
        "profile_digest": readiness.profile_digest,
        "capability_registry_digest": readiness.capability_registry_digest,
        "build_lock_digest": readiness.build_lock_digest,
        "evaluated_at": evaluated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile_status": "PROFILE_CONFORMANT" if readiness.status != "BLOCKED_PROFILE" else "PROFILE_NONCONFORMANT",
        "build_readiness_status": readiness.status,
        "admission_status": admission_status,
        "blockers": list(readiness.blockers),
        "financial_authority": "NONE",
        "payment_authority": "NONE",
        "accounting_authority": "NONE",
        "execution_authority": "NONE",
        "deployment_authority": "NONE",
        "scientific_truth_authority": "NONE",
    }
    payload["decision_digest"] = decision_digest(payload)
    return payload


def verify_science_node_admission_decision_v2(
    payload: dict[str, Any],
    *,
    profile: dict[str, Any],
    signed_manifest: dict[str, Any],
    capability_registry: dict[str, Any],
    build_lock: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
) -> dict[str, Any]:
    expected = {
        "schema", "node_id", "manifest_generation", "manifest_body_digest",
        "profile_digest", "capability_registry_digest", "build_lock_digest",
        "evaluated_at", "profile_status", "build_readiness_status", "admission_status",
        "blockers", "financial_authority", "payment_authority", "accounting_authority",
        "execution_authority", "deployment_authority", "scientific_truth_authority",
        "decision_digest"
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise NodeAdmissionDecisionV2Error("unexpected node-admission v2 shape")
    if payload["schema"] != SCHEMA:
        raise NodeAdmissionDecisionV2Error("unexpected node-admission schema")
    generation = payload["manifest_generation"]
    if isinstance(generation, bool) or not isinstance(generation, int) or not (1 <= generation <= 2**53 - 1):
        raise NodeAdmissionDecisionV2Error("manifest_generation must be positive safe integer")
    for field in ("manifest_body_digest", "profile_digest", "capability_registry_digest", "build_lock_digest", "decision_digest"):
        if not isinstance(payload[field], str) or not HEX64.fullmatch(payload[field]):
            raise NodeAdmissionDecisionV2Error(f"{field} must be lowercase sha256")
    blockers = payload["blockers"]
    if not isinstance(blockers, list) or blockers != sorted(set(blockers)):
        raise NodeAdmissionDecisionV2Error("blockers must be sorted unique")
    for field in (
        "financial_authority", "payment_authority", "accounting_authority",
        "execution_authority", "deployment_authority", "scientific_truth_authority"
    ):
        if payload[field] != "NONE":
            raise NodeAdmissionDecisionV2Error(f"admission decision cannot grant {field}")
    evaluated_at = _parse_utc(payload["evaluated_at"])
    rebuilt = build_science_node_admission_decision_v2(
        profile=profile,
        signed_manifest=signed_manifest,
        capability_registry=capability_registry,
        build_lock=build_lock,
        key_resolver=key_resolver,
        evaluated_at=evaluated_at,
    )
    if payload != rebuilt:
        raise NodeAdmissionDecisionV2Error("node-admission v2 does not match raw evidence")
    if payload["decision_digest"] != decision_digest(payload):
        raise NodeAdmissionDecisionV2Error("node-admission v2 digest mismatch")
    return payload
