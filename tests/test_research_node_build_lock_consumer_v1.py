from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from synergy_meta_os.manifest import sign_manifest, verify_manifest
from synergy_meta_os.node_build_lock_consumer_v1 import (
    BuildLockConsumerError,
    verify_manifest_artifact_binding_v1,
    verify_research_node_source_lock_v1,
)


ROOT = Path(__file__).resolve().parents[1]


def _lock() -> dict:
    return json.loads((ROOT / "fixtures/node_build_locks/research_compute_node_source_candidate_v1.json").read_text())


def _manifest_body() -> dict:
    return {
        "schema": "synergy.node-manifest/v1",
        "node_id": "research-node-001",
        "generation": 1,
        "issued_at": "2026-08-22T10:00:00Z",
        "expires_at": "2026-08-23T10:00:00Z",
        "capabilities": ["CONTENT_CACHE", "NEXUS_COMPUTE", "P2P_RELAY"],
        "services": [
            {
                "service_id": "content-cache",
                "kind": "CONTENT_CACHE",
                "repository": "Shtenco/synergynet",
                "artifact_digest": "11" * 32,
                "required_capabilities": ["CONTENT_CACHE"],
                "desired_state": "ENABLED",
            },
            {
                "service_id": "nexus",
                "kind": "NEXUS",
                "repository": "Shtenco/agi_nexus",
                "artifact_digest": "22" * 32,
                "required_capabilities": ["NEXUS_COMPUTE"],
                "desired_state": "ENABLED",
            },
            {
                "service_id": "synergynet",
                "kind": "SYNERGYNET",
                "repository": "Shtenco/synergynet",
                "artifact_digest": "33" * 32,
                "required_capabilities": ["P2P_RELAY"],
                "desired_state": "ENABLED",
            },
        ],
    }


def test_source_lock_is_conformant_but_never_deployable() -> None:
    decision = verify_research_node_source_lock_v1(_lock())
    assert decision.source_identity_verified is True
    assert decision.build_artifacts_verified is False
    assert decision.deployable is False
    assert decision.status == "SOURCE_LOCK_CONFORMANT_BUILD_NOT_VERIFIED"


def test_valid_signed_manifest_does_not_upgrade_source_lock_to_deployable() -> None:
    private_key = Ed25519PrivateKey.generate()
    envelope = sign_manifest(_manifest_body(), private_key, key_id="test-key")
    body = verify_manifest(
        envelope,
        lambda key_id: private_key.public_key(),
        now=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
    )
    decision = verify_manifest_artifact_binding_v1(body, _lock())
    assert decision.deployable is False
    assert decision.blockers == ("BUILD_ARTIFACTS_NOT_VERIFIED",)


def test_fresh_hash_cannot_claim_build_artifact_in_source_only_generation() -> None:
    tampered = copy.deepcopy(_lock())
    tampered["services"][0]["build_artifact_digest"] = "aa" * 32
    tampered["services"][0]["build_status"] = "BUILD_VERIFIED"
    # Even a caller that recomputes an outer digest cannot change the semantic generation.
    from synergy_meta_os.node_build_lock_consumer_v1 import _digest

    tampered["lock_digest"] = _digest(tampered)
    with pytest.raises(BuildLockConsumerError):
        verify_research_node_source_lock_v1(tampered)


def test_manifest_service_set_must_match_source_lock() -> None:
    body = _manifest_body()
    body["services"] = body["services"][:-1]
    with pytest.raises(BuildLockConsumerError):
        verify_manifest_artifact_binding_v1(body, _lock())
