from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .science_node_profile_consumer_v1 import (
    SCIENCE_PROFILE_DIGEST,
    ScienceProfileConsumerError,
    evaluate_signed_manifest_v2_for_science_profile,
    verify_science_profile,
)


class NodeBuildLockConsumerV2Error(ValueError):
    pass


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCIENCE_REGISTRY_DIGEST = "3727810480e5660129fc63a2d7999b988ed9ae387365d4501bb50b7ae7257913"
SCIENCE_SOURCE_LOCK_DIGEST = "24e4a3c6ed23c2e156b07821fb3b1e0e232651c256bc3b750d2ed25bee477757"
SCIENCE_SOURCE_LOCK_ID = "SCIENCE_RESEARCH_NODE_SOURCE_CANDIDATE_20260821"
SCIENCE_SOURCES = {
    "content-cache": ("CONTENT_CACHE", "Shtenco/synergynet", "874a83b6510420ec43ce99fc4b7936e106ad2339", "feat/static-peer-relay-service-v1-20260821", "SYNERGYNET_PERSISTENT_CONTENT_SERVICE_CANDIDATE"),
    "nexus": ("NEXUS", "Shtenco/agi_nexus", "ef1a6e3675e53fda4bf91566aec61f1b62fa9336", "feat/smallworld-service-protocol-v1-20260821", "NEXUS_SMALLWORLD_SERVICE_CANDIDATE"),
    "science-agent": ("SCIENCE_AGENT", "Shtenco/nexus_science_agent", "0607690c3036d2fdce2ac3e044094a8e4da0311b", "feat/science-service-protocol-v4-20260821", "SCIENCE_AGENT_LOCAL_RESEARCH_SERVICE_CANDIDATE"),
    "synergynet": ("SYNERGYNET", "Shtenco/synergynet", "874a83b6510420ec43ce99fc4b7936e106ad2339", "feat/static-peer-relay-service-v1-20260821", "SYNERGYNET_STATIC_PEER_RELAY_SERVICE_CANDIDATE"),
}


def canonical_json(value: Any) -> bytes:
    def check(v: Any) -> None:
        if v is None or isinstance(v, (str, bool)):
            return
        if isinstance(v, int) and not isinstance(v, bool):
            if abs(v) > 2**53 - 1:
                raise NodeBuildLockConsumerV2Error("unsafe integer")
            return
        if isinstance(v, float):
            raise NodeBuildLockConsumerV2Error("floats forbidden")
        if isinstance(v, list):
            for item in v:
                check(item)
            return
        if isinstance(v, dict):
            if any(not isinstance(k, str) for k in v):
                raise NodeBuildLockConsumerV2Error("object keys must be strings")
            for item in v.values():
                check(item)
            return
        raise NodeBuildLockConsumerV2Error("unsupported build-lock value")
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def lock_digest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("lock_digest", None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


def verify_node_build_lock_v2(payload: dict[str, Any]) -> dict[str, Any]:
    expected = {"schema", "lock_id", "profile_digest", "capability_registry_digest", "services", "verification_status", "execution_authority", "lock_digest"}
    if not isinstance(payload, dict) or set(payload) != expected:
        raise NodeBuildLockConsumerV2Error("unexpected build-lock v2 shape")
    if payload["schema"] != "synergy.node-build-lock/v2":
        raise NodeBuildLockConsumerV2Error("unexpected build-lock schema")
    for field in ("profile_digest", "capability_registry_digest", "lock_digest"):
        if not isinstance(payload[field], str) or not HEX64.fullmatch(payload[field]):
            raise NodeBuildLockConsumerV2Error(f"{field} must be lowercase sha256")
    if not isinstance(payload["lock_id"], str) or not payload["lock_id"]:
        raise NodeBuildLockConsumerV2Error("lock_id required")
    services = payload["services"]
    if not isinstance(services, list) or not services or services != sorted(services, key=lambda x: x.get("service_id", "")):
        raise NodeBuildLockConsumerV2Error("services must be sorted by service_id")
    seen: set[str] = set()
    statuses: list[str] = []
    for service in services:
        fields = {"service_id", "kind", "repository", "source_commit", "source_ref", "source_role", "build_artifact_digest", "build_evidence_digest", "build_status"}
        if not isinstance(service, dict) or set(service) != fields:
            raise NodeBuildLockConsumerV2Error("unexpected service shape")
        sid = service["service_id"]
        if not isinstance(sid, str) or not sid or sid in seen:
            raise NodeBuildLockConsumerV2Error("service_id must be unique")
        seen.add(sid)
        if not isinstance(service["kind"], str) or service["kind"] != service["kind"].upper():
            raise NodeBuildLockConsumerV2Error("invalid service kind")
        if not isinstance(service["repository"], str) or not service["repository"].startswith("Shtenco/"):
            raise NodeBuildLockConsumerV2Error("invalid service repository")
        if not isinstance(service["source_commit"], str) or not HEX40.fullmatch(service["source_commit"]):
            raise NodeBuildLockConsumerV2Error("invalid source commit")
        if not isinstance(service["source_ref"], str) or not service["source_ref"]:
            raise NodeBuildLockConsumerV2Error("source_ref required")
        if not isinstance(service["source_role"], str) or not service["source_role"] or service["source_role"] != service["source_role"].upper():
            raise NodeBuildLockConsumerV2Error("invalid source_role")
        status = service["build_status"]
        artifact = service["build_artifact_digest"]
        evidence = service["build_evidence_digest"]
        statuses.append(status)
        if status == "SOURCE_CANDIDATE_NOT_BUILD_VERIFIED":
            if artifact is not None or evidence is not None:
                raise NodeBuildLockConsumerV2Error("source-only candidate cannot claim build evidence")
        elif status == "BUILD_ARTIFACT_FROZEN_TESTS_PENDING":
            if not isinstance(artifact, str) or not HEX64.fullmatch(artifact) or evidence is not None:
                raise NodeBuildLockConsumerV2Error("artifact-frozen status inconsistent")
        elif status == "BUILD_VERIFIED":
            if not isinstance(artifact, str) or not HEX64.fullmatch(artifact) or not isinstance(evidence, str) or not HEX64.fullmatch(evidence):
                raise NodeBuildLockConsumerV2Error("build-verified status requires artifact and evidence digests")
        else:
            raise NodeBuildLockConsumerV2Error("unknown build status")
    if all(s == "SOURCE_CANDIDATE_NOT_BUILD_VERIFIED" for s in statuses):
        expected_status = "SOURCE_IDENTITY_FROZEN_BUILD_NOT_VERIFIED"
    elif all(s == "BUILD_VERIFIED" for s in statuses):
        expected_status = "BUILD_VERIFIED"
    else:
        expected_status = "BUILD_EVIDENCE_INCOMPLETE"
    if payload["verification_status"] != expected_status:
        raise NodeBuildLockConsumerV2Error("overall build status inconsistent")
    if payload["execution_authority"] != "NONE":
        raise NodeBuildLockConsumerV2Error("build lock grants no execution authority")
    if payload["lock_digest"] != lock_digest(payload):
        raise NodeBuildLockConsumerV2Error("build-lock digest mismatch")
    return payload


def verify_science_source_lock_v2(payload: dict[str, Any]) -> dict[str, Any]:
    verify_node_build_lock_v2(payload)
    if payload["lock_id"] != SCIENCE_SOURCE_LOCK_ID:
        raise NodeBuildLockConsumerV2Error("unexpected science build-lock id")
    if payload["profile_digest"] != SCIENCE_PROFILE_DIGEST or payload["capability_registry_digest"] != SCIENCE_REGISTRY_DIGEST:
        raise NodeBuildLockConsumerV2Error("science build lock bound to wrong profile/registry")
    if payload["lock_digest"] != SCIENCE_SOURCE_LOCK_DIGEST:
        raise NodeBuildLockConsumerV2Error("science source lock digest drifted")
    if len(payload["services"]) != len(SCIENCE_SOURCES):
        raise NodeBuildLockConsumerV2Error("science service set drifted")
    for service in payload["services"]:
        sid = service["service_id"]
        if sid not in SCIENCE_SOURCES:
            raise NodeBuildLockConsumerV2Error("unexpected science service")
        expected = SCIENCE_SOURCES[sid]
        got = (service["kind"], service["repository"], service["source_commit"], service["source_ref"], service["source_role"])
        if got != expected:
            raise NodeBuildLockConsumerV2Error(f"science source identity drifted for {sid}")
        if service["build_status"] != "SOURCE_CANDIDATE_NOT_BUILD_VERIFIED":
            raise NodeBuildLockConsumerV2Error("canonical science source lock cannot overclaim build verification")
    return payload


@dataclass(frozen=True)
class ScienceBuildReadinessV2:
    profile_digest: str
    capability_registry_digest: str
    manifest_body_digest: str
    build_lock_digest: str
    status: str
    blockers: tuple[str, ...]
    execution_authority: str = "NONE"


def evaluate_science_build_readiness_v2(
    *,
    profile: dict[str, Any],
    signed_manifest: dict[str, Any],
    capability_registry: dict[str, Any],
    build_lock: dict[str, Any],
    key_resolver: Callable[[str], Ed25519PublicKey],
    now=None,
) -> ScienceBuildReadinessV2:
    verify_science_profile(profile)
    profile_result = evaluate_signed_manifest_v2_for_science_profile(
        profile=profile,
        signed_manifest=signed_manifest,
        capability_registry=capability_registry,
        key_resolver=key_resolver,
        now=now,
    )
    verify_node_build_lock_v2(build_lock)
    blockers: list[str] = []
    if profile_result.status != "PROFILE_CONFORMANT":
        blockers.extend(profile_result.blockers)
    if build_lock["profile_digest"] != profile["profile_digest"]:
        blockers.append("BUILD_LOCK_PROFILE_MISMATCH")
    if build_lock["capability_registry_digest"] != profile_result.capability_registry_digest:
        blockers.append("BUILD_LOCK_REGISTRY_MISMATCH")
    manifest_services = {item["service_id"]: item for item in signed_manifest["body"]["services"]}
    lock_services = {item["service_id"]: item for item in build_lock["services"]}
    if set(manifest_services) != set(lock_services):
        blockers.append("BUILD_LOCK_SERVICE_SET_MISMATCH")
    for sid, locked in lock_services.items():
        manifest_service = manifest_services.get(sid)
        if manifest_service is None:
            blockers.append(f"MISSING_MANIFEST_SERVICE:{sid}")
            continue
        if manifest_service["kind"] != locked["kind"] or manifest_service["repository"] != locked["repository"]:
            blockers.append(f"SERVICE_IDENTITY_MISMATCH:{sid}")
        if locked["build_status"] != "BUILD_VERIFIED":
            blockers.append(f"BUILD_NOT_VERIFIED:{sid}")
        else:
            if manifest_service["artifact_digest"] != locked["build_artifact_digest"]:
                blockers.append(f"ARTIFACT_DIGEST_MISMATCH:{sid}")
            if locked["build_evidence_digest"] is None:
                blockers.append(f"BUILD_EVIDENCE_MISSING:{sid}")
    blockers = sorted(set(blockers))
    if any(item.startswith("BUILD_NOT_VERIFIED:") or item.startswith("BUILD_EVIDENCE_MISSING:") for item in blockers):
        status = "BLOCKED_BUILD_EVIDENCE"
    elif blockers:
        status = "BLOCKED_CONGRUENCE"
    else:
        status = "BUILD_EVIDENCE_COMPLETE_NOT_EXECUTABLE"
    return ScienceBuildReadinessV2(
        profile_digest=profile["profile_digest"],
        capability_registry_digest=profile_result.capability_registry_digest,
        manifest_body_digest=signed_manifest["body_digest"],
        build_lock_digest=build_lock["lock_digest"],
        status=status,
        blockers=tuple(blockers),
    )
