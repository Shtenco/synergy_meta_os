from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .capability_registry_consumer_v1 import canonical_json
from .node_build_lock_consumer_v2 import verify_science_build_lock_v2
from .science_node_profile_consumer_v1 import evaluate_signed_manifest_v2_for_science_profile


class NodeAdmissionV2Error(ValueError):
    pass


def _utc_text(now: datetime) -> str:
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise NodeAdmissionV2Error("evaluation time must be timezone-aware")
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def evaluate_science_node_admission_v2(*, profile: dict[str, Any], signed_manifest: dict[str, Any], capability_registry: dict[str, Any], build_lock: dict[str, Any], key_resolver: Callable[[str], Ed25519PublicKey], now: datetime) -> dict[str, Any]:
    profile_result = evaluate_signed_manifest_v2_for_science_profile(
        profile=profile,
        signed_manifest=signed_manifest,
        capability_registry=capability_registry,
        key_resolver=key_resolver,
        now=now,
    )
    verified_lock = verify_science_build_lock_v2(build_lock)

    blockers = list(profile_result.blockers)
    if profile_result.status != "PROFILE_CONFORMANT":
        blockers.append("PROFILE_NONCONFORMANT")
    if verified_lock["profile_digest"] != profile_result.profile_digest:
        blockers.append("BUILD_LOCK_PROFILE_MISMATCH")
    if verified_lock["capability_registry_digest"] != profile_result.capability_registry_digest:
        blockers.append("BUILD_LOCK_CAPABILITY_REGISTRY_MISMATCH")
    if verified_lock["verification_status"] != "BUILD_VERIFIED":
        blockers.append("BUILD_EVIDENCE_MISSING")

    blockers = sorted(set(blockers))
    if profile_result.status != "PROFILE_CONFORMANT":
        status = "BLOCKED_PROFILE"
    elif "BUILD_EVIDENCE_MISSING" in blockers:
        status = "BLOCKED_BUILD_EVIDENCE"
    else:
        status = "ADMISSION_REVIEWABLE"

    body = {
        "schema": "synergy.node-admission-decision/v2",
        "profile_id": profile_result.profile_id,
        "profile_digest": profile_result.profile_digest,
        "capability_registry_digest": profile_result.capability_registry_digest,
        "signed_manifest_digest": _sha(signed_manifest),
        "manifest_body_digest": profile_result.manifest_body_digest,
        "build_lock_digest": verified_lock["lock_digest"],
        "build_verification_status": verified_lock["verification_status"],
        "evaluated_at": _utc_text(now),
        "status": status,
        "blockers": blockers,
        "deployment_authority": "NONE",
        "execution_authority": "NONE",
        "financial_authority": "NONE",
        "payment_authority": "NONE",
        "accounting_authority": "NONE",
        "scientific_truth_authority": "NONE",
    }
    return body | {"decision_digest": _sha(body)}


def verify_science_node_admission_decision_v2(decision: dict[str, Any], *, profile: dict[str, Any], signed_manifest: dict[str, Any], capability_registry: dict[str, Any], build_lock: dict[str, Any], key_resolver: Callable[[str], Ed25519PublicKey], now: datetime) -> dict[str, Any]:
    rebuilt = evaluate_science_node_admission_v2(
        profile=profile,
        signed_manifest=signed_manifest,
        capability_registry=capability_registry,
        build_lock=build_lock,
        key_resolver=key_resolver,
        now=now,
    )
    if decision != rebuilt:
        raise NodeAdmissionV2Error("admission decision does not match re-verified raw evidence")
    return decision
