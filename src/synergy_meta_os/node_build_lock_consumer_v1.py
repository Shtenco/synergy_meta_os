from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


class BuildLockConsumerError(ValueError):
    pass


_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_DIGEST = "406740705e853fa51ad4eacf7a01925fbe4b5cec491be35ea12ba777d217d714"
_LOCK_DIGEST = "14c763218602585d49e12060e1e6cf21d33815fda0cb18711a6522a26157ace2"
_EXPECTED = {
    "content-cache": (
        "Shtenco/synergynet",
        "a8fde01c19420dbe63ca30e1da3b009c0c10064d",
        "feat/persistent-store-codec-v3-20260821",
        "SYNERGYNET_PERSISTENT_CACHE_CANDIDATE",
    ),
    "nexus": (
        "Shtenco/agi_nexus",
        "cbc06e83f7f9e242719667e446a090894e11eef1",
        "feat/smallworld-kernel-migration-v1-20260821",
        "NEXUS_SMALLWORLD_KERNEL_CANDIDATE",
    ),
    "synergynet": (
        "Shtenco/synergynet",
        "a8fde01c19420dbe63ca30e1da3b009c0c10064d",
        "feat/persistent-store-codec-v3-20260821",
        "SYNERGYNET_TRANSPORT_CANDIDATE",
    ),
}


def _check_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 2**53 - 1:
            raise BuildLockConsumerError("unsafe integer")
        return
    if isinstance(value, float):
        raise BuildLockConsumerError("floating point values are forbidden")
    if isinstance(value, list):
        for item in value:
            _check_json(item)
        return
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise BuildLockConsumerError("object keys must be strings")
        for item in value.values():
            _check_json(item)
        return
    raise BuildLockConsumerError("unsupported value in build lock")


def canonical_json(value: Any) -> bytes:
    _check_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("lock_digest", None)
    return hashlib.sha256(canonical_json(body)).hexdigest()


@dataclass(frozen=True)
class BuildLockDecisionV1:
    status: str
    source_identity_verified: bool
    build_artifacts_verified: bool
    deployable: bool
    blockers: tuple[str, ...]


def verify_research_node_source_lock_v1(payload: dict[str, Any]) -> BuildLockDecisionV1:
    required = {
        "schema", "lock_id", "profile_digest", "services", "verification_status",
        "execution_authority", "lock_digest",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise BuildLockConsumerError("unexpected node build-lock shape")
    if payload["schema"] != "synergy.node-build-lock/v1":
        raise BuildLockConsumerError("unexpected build-lock schema")
    if payload["lock_id"] != "RESEARCH_COMPUTE_NODE_SOURCE_CANDIDATE_20260821":
        raise BuildLockConsumerError("unexpected build-lock id")
    if payload["profile_digest"] != _PROFILE_DIGEST:
        raise BuildLockConsumerError("build lock bound to the wrong node profile")
    if payload["execution_authority"] != "NONE":
        raise BuildLockConsumerError("source lock cannot grant execution authority")
    if payload["verification_status"] != "SOURCE_IDENTITY_FROZEN_BUILD_NOT_VERIFIED":
        raise BuildLockConsumerError("source lock overclaims verification status")
    services = payload["services"]
    if not isinstance(services, list) or services != sorted(services, key=lambda item: item.get("service_id", "")):
        raise BuildLockConsumerError("services must be sorted by service_id")
    if len(services) != len(_EXPECTED):
        raise BuildLockConsumerError("service set drifted")
    seen: set[str] = set()
    for service in services:
        fields = {
            "service_id", "repository", "source_commit", "source_ref", "source_role",
            "build_artifact_digest", "build_status",
        }
        if not isinstance(service, dict) or set(service) != fields:
            raise BuildLockConsumerError("unexpected service shape")
        sid = service["service_id"]
        if sid in seen or sid not in _EXPECTED:
            raise BuildLockConsumerError("unexpected or duplicate service")
        seen.add(sid)
        repository, commit, ref, role = _EXPECTED[sid]
        if (
            service["repository"] != repository
            or service["source_commit"] != commit
            or service["source_ref"] != ref
            or service["source_role"] != role
        ):
            raise BuildLockConsumerError(f"source identity drifted for {sid}")
        if not _HEX40.fullmatch(service["source_commit"]):
            raise BuildLockConsumerError("source commit must be lowercase git sha")
        if service["build_artifact_digest"] is not None:
            raise BuildLockConsumerError("source-only lock cannot contain build artifact digest")
        if service["build_status"] != "SOURCE_CANDIDATE_NOT_BUILD_VERIFIED":
            raise BuildLockConsumerError("unexpected service build status")
    if seen != set(_EXPECTED):
        raise BuildLockConsumerError("service set incomplete")
    supplied = payload["lock_digest"]
    if not isinstance(supplied, str) or not _HEX64.fullmatch(supplied):
        raise BuildLockConsumerError("invalid lock digest")
    recomputed = _digest(payload)
    if supplied != recomputed or recomputed != _LOCK_DIGEST:
        raise BuildLockConsumerError("build-lock digest mismatch")
    return BuildLockDecisionV1(
        status="SOURCE_LOCK_CONFORMANT_BUILD_NOT_VERIFIED",
        source_identity_verified=True,
        build_artifacts_verified=False,
        deployable=False,
        blockers=("BUILD_ARTIFACTS_NOT_VERIFIED",),
    )


def verify_manifest_artifact_binding_v1(
    manifest_body: dict[str, Any],
    build_lock: dict[str, Any],
) -> BuildLockDecisionV1:
    """Rejects source-only locks as deployable bindings.

    A manifest may be validly signed and profile-conformant, but v1 source locks do not
    contain executable artifact digests. Therefore this function deliberately never
    upgrades a source-only build lock into a deployable service binding.
    """
    decision = verify_research_node_source_lock_v1(build_lock)
    services = manifest_body.get("services") if isinstance(manifest_body, dict) else None
    if not isinstance(services, list):
        raise BuildLockConsumerError("manifest services must be present")
    expected_ids = set(_EXPECTED)
    actual_ids = {item.get("service_id") for item in services if isinstance(item, dict)}
    if actual_ids != expected_ids:
        raise BuildLockConsumerError("manifest service ids do not match source lock")
    # Source-only lock deliberately contains no build artifact identities, so there is
    # nothing authoritative to compare manifest artifact_digest against yet.
    return decision
