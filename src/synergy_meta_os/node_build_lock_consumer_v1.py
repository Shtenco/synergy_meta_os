from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .manifest import canonical_json
from .node_profile_consumer_v1 import (
    ProfileConformanceResult,
    evaluate_signed_manifest_for_research_profile,
)


class NodeBuildLockConsumerError(ValueError):
    pass


_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_DIGEST = "406740705e853fa51ad4eacf7a01925fbe4b5cec491be35ea12ba777d217d714"
_LOCK_DIGEST = "14c763218602585d49e12060e1e6cf21d33815fda0cb18711a6522a26157ace2"
_EXPECTED_SOURCE = {
    "content-cache": ("Shtenco/synergynet", "a8fde01c19420dbe63ca30e1da3b009c0c10064d", "feat/persistent-store-codec-v3-20260821", "SYNERGYNET_PERSISTENT_CACHE_CANDIDATE"),
    "nexus": ("Shtenco/agi_nexus", "cbc06e83f7f9e242719667e446a090894e11eef1", "feat/smallworld-kernel-migration-v1-20260821", "NEXUS_SMALLWORLD_KERNEL_CANDIDATE"),
    "synergynet": ("Shtenco/synergynet", "a8fde01c19420dbe63ca30e1da3b009c0c10064d", "feat/persistent-store-codec-v3-20260821", "SYNERGYNET_TRANSPORT_CANDIDATE"),
}


@dataclass(frozen=True)
class ResearchNodeReadinessResult:
    profile_status: str
    profile_digest: str
    source_lock_digest: str
    source_lock_status: str
    build_evidence_status: str
    deployability_status: str
    blockers: tuple[str, ...]
    financial_authority: str = "NONE"
    payment_authority: str = "NONE"
    accounting_authority: str = "NONE"
    execution_authority: str = "NONE"


def lock_digest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("lock_digest", None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


def verify_research_source_lock(payload: dict[str, Any]) -> dict[str, Any]:
    expected_fields = {
        "schema", "lock_id", "profile_digest", "services", "verification_status",
        "execution_authority", "lock_digest"
    }
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise NodeBuildLockConsumerError("unexpected node-build-lock shape")
    if payload["schema"] != "synergy.node-build-lock/v1":
        raise NodeBuildLockConsumerError("unexpected node-build-lock schema")
    if payload["lock_id"] != "RESEARCH_COMPUTE_NODE_SOURCE_CANDIDATE_20260821":
        raise NodeBuildLockConsumerError("unexpected source lock id")
    if payload["profile_digest"] != _PROFILE_DIGEST:
        raise NodeBuildLockConsumerError("source lock bound to wrong profile")
    services = payload["services"]
    if not isinstance(services, list) or services != sorted(services, key=lambda item: item.get("service_id", "")):
        raise NodeBuildLockConsumerError("source-lock services must be sorted")
    if len(services) != len(_EXPECTED_SOURCE):
        raise NodeBuildLockConsumerError("source-lock service set drifted")
    seen: set[str] = set()
    for service in services:
        expected_shape = {
            "service_id", "repository", "source_commit", "source_ref", "source_role",
            "build_artifact_digest", "build_status"
        }
        if not isinstance(service, dict) or set(service) != expected_shape:
            raise NodeBuildLockConsumerError("unexpected source-lock service shape")
        sid = service["service_id"]
        if sid in seen or sid not in _EXPECTED_SOURCE:
            raise NodeBuildLockConsumerError("unexpected or duplicate source-lock service")
        seen.add(sid)
        repository, commit, source_ref, source_role = _EXPECTED_SOURCE[sid]
        if service["repository"] != repository or service["source_commit"] != commit:
            raise NodeBuildLockConsumerError("source identity drifted")
        if service["source_ref"] != source_ref or service["source_role"] != source_role:
            raise NodeBuildLockConsumerError("source metadata drifted")
        if not _HEX40.fullmatch(service["source_commit"]):
            raise NodeBuildLockConsumerError("source commit must be lowercase git sha")
        if service["build_artifact_digest"] is not None:
            raise NodeBuildLockConsumerError("source-only v1 cannot claim a build artifact")
        if service["build_status"] != "SOURCE_CANDIDATE_NOT_BUILD_VERIFIED":
            raise NodeBuildLockConsumerError("source-only v1 build status overclaims evidence")
    if seen != set(_EXPECTED_SOURCE):
        raise NodeBuildLockConsumerError("source-lock service set incomplete")
    if payload["verification_status"] != "SOURCE_IDENTITY_FROZEN_BUILD_NOT_VERIFIED":
        raise NodeBuildLockConsumerError("source-lock verification status overclaims evidence")
    if payload["execution_authority"] != "NONE":
        raise NodeBuildLockConsumerError("source lock cannot execute services")
    supplied = payload["lock_digest"]
    if not isinstance(supplied, str) or not _HEX64.fullmatch(supplied):
        raise NodeBuildLockConsumerError("source-lock digest must be lowercase sha256")
    recomputed = lock_digest(payload)
    if supplied != recomputed or recomputed != _LOCK_DIGEST:
        raise NodeBuildLockConsumerError("source-lock digest mismatch")
    return payload


def evaluate_research_node_readiness(
    *,
    profile: dict[str, Any],
    source_lock: dict[str, Any],
    signed_manifest: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
    now=None,
) -> ResearchNodeReadinessResult:
    profile_result: ProfileConformanceResult = evaluate_signed_manifest_for_research_profile(
        profile=profile,
        signed_manifest=signed_manifest,
        key_resolver=key_resolver,
        now=now,
    )
    verify_research_source_lock(source_lock)
    blockers = list(profile_result.blockers)
    if source_lock["profile_digest"] != profile_result.profile_digest:
        blockers.append("SOURCE_LOCK_PROFILE_MISMATCH")

    manifest_services = {service["service_id"]: service for service in signed_manifest["body"]["services"]}
    for service in source_lock["services"]:
        manifest_service = manifest_services.get(service["service_id"])
        if manifest_service is None:
            blockers.append(f"SOURCE_LOCK_MANIFEST_SERVICE_MISSING:{service['service_id']}")
            continue
        if manifest_service["repository"] != service["repository"]:
            blockers.append(f"SOURCE_LOCK_REPOSITORY_MISMATCH:{service['service_id']}")
        # No build digest exists in v1. A manifest artifact digest therefore cannot be
        # proven to originate from this source lock.
        if service["build_artifact_digest"] is None:
            blockers.append(f"BUILD_ARTIFACT_EVIDENCE_MISSING:{service['service_id']}")

    blockers = sorted(set(blockers))
    source_status = "SOURCE_LOCK_CONFORMANT" if source_lock["lock_digest"] == _LOCK_DIGEST else "SOURCE_LOCK_INVALID"
    build_status = "BUILD_EVIDENCE_MISSING"
    deployability = "NOT_DEPLOYABLE"
    return ResearchNodeReadinessResult(
        profile_status=profile_result.status,
        profile_digest=profile_result.profile_digest,
        source_lock_digest=source_lock["lock_digest"],
        source_lock_status=source_status,
        build_evidence_status=build_status,
        deployability_status=deployability,
        blockers=tuple(blockers),
    )


def require_deployable(result: ResearchNodeReadinessResult) -> None:
    if result.deployability_status != "DEPLOYABLE" or result.blockers:
        raise NodeBuildLockConsumerError("research node is not deployable from source-lock evidence alone")
