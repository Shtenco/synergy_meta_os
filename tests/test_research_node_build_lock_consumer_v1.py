import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from synergy_meta_os.manifest import sign_manifest
from synergy_meta_os.node_build_lock_consumer_v1 import (
    NodeBuildLockConsumerError,
    evaluate_research_node_readiness,
    lock_digest,
    require_deployable,
    verify_research_source_lock,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 21, 13, 0, 0, tzinfo=timezone.utc)


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def research_body():
    return {
        "schema": "synergy.node-manifest/v1",
        "node_id": "research-node-001",
        "generation": 1,
        "issued_at": "2026-08-21T12:00:00Z",
        "expires_at": "2026-08-22T12:00:00Z",
        "capabilities": ["CONTENT_CACHE", "NEXUS_COMPUTE", "P2P_RELAY"],
        "services": [
            {"service_id":"content-cache","kind":"CONTENT_CACHE","repository":"Shtenco/synergynet","artifact_digest":"1"*64,"required_capabilities":["CONTENT_CACHE"],"desired_state":"ENABLED"},
            {"service_id":"nexus","kind":"NEXUS","repository":"Shtenco/agi_nexus","artifact_digest":"2"*64,"required_capabilities":["NEXUS_COMPUTE"],"desired_state":"ENABLED"},
            {"service_id":"synergynet","kind":"SYNERGYNET","repository":"Shtenco/synergynet","artifact_digest":"3"*64,"required_capabilities":["P2P_RELAY"],"desired_state":"ENABLED"},
        ],
    }


def signed(body):
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    return sign_manifest(body, private, key_id="test-key"), lambda key_id: public


def test_exact_source_lock_verifies_but_is_not_build_evidence():
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    verify_research_source_lock(source_lock)
    assert source_lock["lock_digest"] == "14c763218602585d49e12060e1e6cf21d33815fda0cb18711a6522a26157ace2"
    assert all(item["build_artifact_digest"] is None for item in source_lock["services"])


def test_profile_plus_signed_manifest_plus_source_lock_is_still_not_deployable():
    profile = load_json("fixtures/node_profiles/research_compute_node_v1.json")
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    envelope, resolver = signed(research_body())
    result = evaluate_research_node_readiness(
        profile=profile,
        source_lock=source_lock,
        signed_manifest=envelope,
        key_resolver=resolver,
        now=NOW,
    )
    assert result.profile_status == "PROFILE_CONFORMANT"
    assert result.source_lock_status == "SOURCE_LOCK_CONFORMANT"
    assert result.build_evidence_status == "BUILD_EVIDENCE_MISSING"
    assert result.deployability_status == "NOT_DEPLOYABLE"
    assert result.blockers == (
        "BUILD_ARTIFACT_EVIDENCE_MISSING:content-cache",
        "BUILD_ARTIFACT_EVIDENCE_MISSING:nexus",
        "BUILD_ARTIFACT_EVIDENCE_MISSING:synergynet",
    )
    assert result.execution_authority == "NONE"
    with pytest.raises(NodeBuildLockConsumerError, match="not deployable"):
        require_deployable(result)


def test_fresh_lock_hash_cannot_invent_deployable_artifact():
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    source_lock["services"][1]["build_artifact_digest"] = "f" * 64
    source_lock["services"][1]["build_status"] = "BUILD_VERIFIED"
    source_lock["lock_digest"] = lock_digest(source_lock)
    with pytest.raises(NodeBuildLockConsumerError, match="cannot claim a build artifact"):
        verify_research_source_lock(source_lock)


def test_other_source_commit_is_rejected_even_if_outer_digest_is_recomputed():
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    source_lock["services"][0]["source_commit"] = "0" * 40
    source_lock["lock_digest"] = lock_digest(source_lock)
    with pytest.raises(NodeBuildLockConsumerError, match="source identity drifted"):
        verify_research_source_lock(source_lock)


def test_source_lock_does_not_grant_any_authority():
    profile = load_json("fixtures/node_profiles/research_compute_node_v1.json")
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    envelope, resolver = signed(research_body())
    result = evaluate_research_node_readiness(
        profile=profile, source_lock=source_lock, signed_manifest=envelope, key_resolver=resolver, now=NOW
    )
    assert result.financial_authority == "NONE"
    assert result.payment_authority == "NONE"
    assert result.accounting_authority == "NONE"
    assert result.execution_authority == "NONE"
