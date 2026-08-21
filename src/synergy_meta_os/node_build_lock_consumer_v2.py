from __future__ import annotations

import hashlib
import re
from typing import Any

from .capability_registry_consumer_v1 import canonical_json


class BuildLockConsumerV2Error(ValueError):
    pass


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCIENCE_PROFILE_DIGEST = "0c9b82e591c5aa30d1f9b499edee02c0b56643af825bbb7eecb93f8651659107"
REGISTRY_DIGEST = "3727810480e5660129fc63a2d7999b988ed9ae387365d4501bb50b7ae7257913"
SCIENCE_LOCK_DIGEST = "24e4a3c6ed23c2e156b07821fb3b1e0e232651c256bc3b750d2ed25bee477757"
EXPECTED = {
    "content-cache": ("CONTENT_CACHE", "Shtenco/synergynet", "874a83b6510420ec43ce99fc4b7936e106ad2339"),
    "nexus": ("NEXUS", "Shtenco/agi_nexus", "ef1a6e3675e53fda4bf91566aec61f1b62fa9336"),
    "science-agent": ("SCIENCE_AGENT", "Shtenco/nexus_science_agent", "0607690c3036d2fdce2ac3e044094a8e4da0311b"),
    "synergynet": ("SYNERGYNET", "Shtenco/synergynet", "874a83b6510420ec43ce99fc4b7936e106ad2339"),
}


def lock_digest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("lock_digest", None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


def verify_science_build_lock_v2(payload: dict[str, Any]) -> dict[str, Any]:
    expected_fields = {"schema", "lock_id", "profile_digest", "capability_registry_digest", "services", "verification_status", "execution_authority", "lock_digest"}
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise BuildLockConsumerV2Error("unexpected build-lock v2 shape")
    if payload["schema"] != "synergy.node-build-lock/v2" or payload["lock_id"] != "SCIENCE_RESEARCH_NODE_SOURCE_CANDIDATE_20260821":
        raise BuildLockConsumerV2Error("unexpected science build-lock identity")
    if payload["profile_digest"] != SCIENCE_PROFILE_DIGEST or payload["capability_registry_digest"] != REGISTRY_DIGEST:
        raise BuildLockConsumerV2Error("build lock bound to wrong profile or capability registry")
    if payload["execution_authority"] != "NONE":
        raise BuildLockConsumerV2Error("build lock cannot execute services")
    services = payload["services"]
    if not isinstance(services, list) or services != sorted(services, key=lambda x:x.get("service_id", "")) or len(services) != len(EXPECTED):
        raise BuildLockConsumerV2Error("science service set invalid")
    seen: set[str] = set()
    for service in services:
        fields = {"service_id", "kind", "repository", "source_commit", "source_ref", "source_role", "build_artifact_digest", "build_evidence_digest", "build_status"}
        if not isinstance(service, dict) or set(service) != fields:
            raise BuildLockConsumerV2Error("unexpected service shape")
        sid = service["service_id"]
        if sid not in EXPECTED or sid in seen:
            raise BuildLockConsumerV2Error("unexpected or duplicate service")
        seen.add(sid)
        kind, repo, commit = EXPECTED[sid]
        if (service["kind"], service["repository"], service["source_commit"]) != (kind, repo, commit):
            raise BuildLockConsumerV2Error(f"source identity drifted for {sid}")
        if not HEX40.fullmatch(service["source_commit"]):
            raise BuildLockConsumerV2Error("invalid git commit")
        if service["build_status"] != "SOURCE_CANDIDATE_NOT_BUILD_VERIFIED":
            raise BuildLockConsumerV2Error("canonical science lock cannot overclaim build status")
        if service["build_artifact_digest"] is not None or service["build_evidence_digest"] is not None:
            raise BuildLockConsumerV2Error("canonical science source lock cannot claim build/evidence digests")
    if seen != set(EXPECTED):
        raise BuildLockConsumerV2Error("science service set incomplete")
    if payload["verification_status"] != "SOURCE_IDENTITY_FROZEN_BUILD_NOT_VERIFIED":
        raise BuildLockConsumerV2Error("science build verification status overclaims evidence")
    if not isinstance(payload["lock_digest"], str) or not HEX64.fullmatch(payload["lock_digest"]):
        raise BuildLockConsumerV2Error("invalid build-lock digest")
    recomputed = lock_digest(payload)
    if recomputed != payload["lock_digest"] or recomputed != SCIENCE_LOCK_DIGEST:
        raise BuildLockConsumerV2Error("science build-lock digest mismatch")
    return payload
