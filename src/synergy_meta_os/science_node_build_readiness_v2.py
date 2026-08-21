from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .node_build_lock_consumer_v2 import verify_science_source_lock_v2
from .science_node_profile_consumer_v1 import (
    evaluate_signed_manifest_v2_for_science_profile,
    verify_science_profile,
)


@dataclass(frozen=True)
class ScienceNodeBuildReadinessV2:
    profile_digest: str
    capability_registry_digest: str
    manifest_body_digest: str
    build_lock_digest: str
    status: str
    blockers: tuple[str, ...]
    execution_authority: str = "NONE"
    deployment_authority: str = "NONE"


def evaluate_pinned_science_source_readiness_v2(
    *,
    profile: dict[str, Any],
    signed_manifest: dict[str, Any],
    capability_registry: dict[str, Any],
    build_lock: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
    now=None,
) -> ScienceNodeBuildReadinessV2:
    verify_science_profile(profile)
    profile_result = evaluate_signed_manifest_v2_for_science_profile(
        profile=profile,
        signed_manifest=signed_manifest,
        capability_registry=capability_registry,
        key_resolver=key_resolver,
        now=now,
    )
    locked = verify_science_source_lock_v2(build_lock)

    blockers: list[str] = []
    if profile_result.status != "PROFILE_CONFORMANT":
        blockers.extend(profile_result.blockers)
    if locked["profile_digest"] != profile_result.profile_digest:
        blockers.append("BUILD_LOCK_PROFILE_MISMATCH")
    if locked["capability_registry_digest"] != profile_result.capability_registry_digest:
        blockers.append("BUILD_LOCK_REGISTRY_MISMATCH")

    manifest_services = {item["service_id"]: item for item in signed_manifest["body"]["services"]}
    lock_services = {item["service_id"]: item for item in locked["services"]}
    if set(manifest_services) != set(lock_services):
        blockers.append("BUILD_LOCK_SERVICE_SET_MISMATCH")

    for sid, service_lock in lock_services.items():
        manifest_service = manifest_services.get(sid)
        if manifest_service is None:
            blockers.append(f"MISSING_MANIFEST_SERVICE:{sid}")
            continue
        if manifest_service["kind"] != service_lock["kind"]:
            blockers.append(f"SERVICE_KIND_MISMATCH:{sid}")
        if manifest_service["repository"] != service_lock["repository"]:
            blockers.append(f"SERVICE_REPOSITORY_MISMATCH:{sid}")
        blockers.append(f"BUILD_NOT_VERIFIED:{sid}")

    blockers = sorted(set(blockers))
    if profile_result.status != "PROFILE_CONFORMANT":
        status = "BLOCKED_PROFILE"
    else:
        status = "BLOCKED_BUILD_EVIDENCE"

    return ScienceNodeBuildReadinessV2(
        profile_digest=profile_result.profile_digest,
        capability_registry_digest=profile_result.capability_registry_digest,
        manifest_body_digest=profile_result.manifest_body_digest,
        build_lock_digest=locked["lock_digest"],
        status=status,
        blockers=tuple(blockers),
    )
