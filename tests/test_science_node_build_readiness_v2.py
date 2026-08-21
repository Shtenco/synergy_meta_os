from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from synergy_meta_os.manifest_v2 import sign_manifest_v2
from synergy_meta_os.node_build_lock_consumer_v2 import NodeBuildLockConsumerV2Error, lock_digest
from synergy_meta_os.science_node_build_readiness_v2 import evaluate_pinned_science_source_readiness_v2

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "fixtures/capabilities/synergy_capability_registry_v1.json"
PROFILE = ROOT / "fixtures/node_profiles/science_research_node_v1.json"
BUILD_LOCK = ROOT / "fixtures/node_build_locks/science_research_node_source_candidate_v2.json"
REGISTRY_DIGEST = "3727810480e5660129fc63a2d7999b988ed9ae387365d4501bb50b7ae7257913"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def base_body():
    return {
        "schema":"synergy.node-manifest/v2",
        "node_id":"science-node-001",
        "generation":1,
        "issued_at":"2026-08-21T16:00:00Z",
        "expires_at":"2026-08-22T16:00:00Z",
        "capability_registry_digest":REGISTRY_DIGEST,
        "capabilities":["CONTENT_CACHE","NEXUS_COMPUTE","P2P_RELAY","SCIENCE_RESEARCH"],
        "services":[
            {"service_id":"content-cache","kind":"CONTENT_CACHE","repository":"Shtenco/synergynet","artifact_digest":"11"*32,"required_capabilities":["CONTENT_CACHE"],"desired_state":"ENABLED"},
            {"service_id":"nexus","kind":"NEXUS","repository":"Shtenco/agi_nexus","artifact_digest":"22"*32,"required_capabilities":["NEXUS_COMPUTE"],"desired_state":"ENABLED"},
            {"service_id":"science-agent","kind":"SCIENCE_AGENT","repository":"Shtenco/nexus_science_agent","artifact_digest":"33"*32,"required_capabilities":["SCIENCE_RESEARCH"],"desired_state":"ENABLED"},
            {"service_id":"synergynet","kind":"SYNERGYNET","repository":"Shtenco/synergynet","artifact_digest":"44"*32,"required_capabilities":["P2P_RELAY"],"desired_state":"ENABLED"}
        ]
    }


def signed(body):
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    envelope = sign_manifest_v2(body, load(REGISTRY), private, key_id="node-key")
    return envelope, lambda key_id: public


def evaluate(body, build_lock=None):
    envelope, resolver = signed(body)
    return evaluate_pinned_science_source_readiness_v2(
        profile=load(PROFILE),
        signed_manifest=envelope,
        capability_registry=load(REGISTRY),
        build_lock=load(BUILD_LOCK) if build_lock is None else build_lock,
        key_resolver=resolver,
        now=datetime(2026,8,21,17,0,tzinfo=timezone.utc),
    )


def test_profile_conformant_source_locked_science_node_is_still_not_deployable():
    result = evaluate(base_body())
    assert result.status == "BLOCKED_BUILD_EVIDENCE"
    assert result.execution_authority == "NONE"
    assert result.deployment_authority == "NONE"
    assert set(result.blockers) == {
        "BUILD_NOT_VERIFIED:content-cache",
        "BUILD_NOT_VERIFIED:nexus",
        "BUILD_NOT_VERIFIED:science-agent",
        "BUILD_NOT_VERIFIED:synergynet",
    }


def test_correctly_resigned_metapay_escalation_fails_profile_before_build_readiness():
    body = base_body()
    body["capabilities"].append("METAPAY_GATEWAY")
    body["capabilities"].sort()
    body["services"].append({"service_id":"metapay","kind":"METAPAY","repository":"Shtenco/synergy_pay_system","artifact_digest":"55"*32,"required_capabilities":["METAPAY_GATEWAY"],"desired_state":"ENABLED"})
    body["services"] = sorted(body["services"], key=lambda x:x["service_id"])
    result = evaluate(body)
    assert result.status == "BLOCKED_PROFILE"
    assert "FORBIDDEN_CAPABILITY_PRESENT" in result.blockers


def test_fresh_hash_fake_build_verified_lock_is_rejected_by_pinned_generation():
    forged = load(BUILD_LOCK)
    for item in forged["services"]:
        item["build_status"] = "BUILD_VERIFIED"
        item["build_artifact_digest"] = "aa" * 32
        item["build_evidence_digest"] = "bb" * 32
    forged["verification_status"] = "BUILD_VERIFIED"
    forged["lock_digest"] = lock_digest(forged)
    with pytest.raises(NodeBuildLockConsumerV2Error):
        evaluate(base_body(), forged)


def test_source_commit_drift_is_rejected_even_with_fresh_lock_hash():
    forged = copy.deepcopy(load(BUILD_LOCK))
    for item in forged["services"]:
        if item["service_id"] == "nexus":
            item["source_commit"] = "0" * 40
    forged["lock_digest"] = lock_digest(forged)
    with pytest.raises(NodeBuildLockConsumerV2Error):
        evaluate(base_body(), forged)
