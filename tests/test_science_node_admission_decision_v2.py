from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from synergy_meta_os.manifest_v2 import sign_manifest_v2
from synergy_meta_os.node_admission_decision_v2 import (
    NodeAdmissionDecisionV2Error,
    build_science_node_admission_decision_v2,
    decision_digest,
    verify_science_node_admission_decision_v2,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "fixtures/capabilities/synergy_capability_registry_v1.json"
PROFILE = ROOT / "fixtures/node_profiles/science_research_node_v1.json"
BUILD_LOCK = ROOT / "fixtures/node_build_locks/science_research_node_source_candidate_v2.json"
EXPECTED = ROOT / "fixtures/node_admission/science_research_node_blocked_build_v2.json"
EVALUATED_AT = datetime(2026,8,21,17,0,tzinfo=timezone.utc)
REGISTRY_DIGEST = "3727810480e5660129fc63a2d7999b988ed9ae387365d4501bb50b7ae7257913"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def body():
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


def signed():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    envelope = sign_manifest_v2(body(), load(REGISTRY), private, key_id="node-key")
    return envelope, lambda key_id: public


def build():
    envelope, resolver = signed()
    decision = build_science_node_admission_decision_v2(
        profile=load(PROFILE), signed_manifest=envelope, capability_registry=load(REGISTRY),
        build_lock=load(BUILD_LOCK), key_resolver=resolver, evaluated_at=EVALUATED_AT
    )
    return decision, envelope, resolver


def test_canonical_science_blocked_decision_matches_fixed_fixture():
    decision, envelope, resolver = build()
    assert decision == load(EXPECTED)
    assert decision["decision_digest"] == "d33c013bd28feee1faea62a3521da40fa6a532285ffce81a59819424cf0a7156"
    verify_science_node_admission_decision_v2(
        decision, profile=load(PROFILE), signed_manifest=envelope,
        capability_registry=load(REGISTRY), build_lock=load(BUILD_LOCK), key_resolver=resolver
    )


def test_fresh_hash_cannot_change_blocked_science_decision_into_admitted():
    decision, envelope, resolver = build()
    decision["admission_status"] = "ADMITTED"
    decision["blockers"] = []
    decision["decision_digest"] = decision_digest(decision)
    with pytest.raises(NodeAdmissionDecisionV2Error, match="does not match raw evidence"):
        verify_science_node_admission_decision_v2(
            decision, profile=load(PROFILE), signed_manifest=envelope,
            capability_registry=load(REGISTRY), build_lock=load(BUILD_LOCK), key_resolver=resolver
        )


def test_fresh_hash_cannot_grant_deployment_or_scientific_truth_authority():
    decision, envelope, resolver = build()
    decision["deployment_authority"] = "START_SERVICES"
    decision["scientific_truth_authority"] = "TRUTH"
    decision["decision_digest"] = decision_digest(decision)
    with pytest.raises(NodeAdmissionDecisionV2Error):
        verify_science_node_admission_decision_v2(
            decision, profile=load(PROFILE), signed_manifest=envelope,
            capability_registry=load(REGISTRY), build_lock=load(BUILD_LOCK), key_resolver=resolver
        )


def test_historical_verification_uses_recorded_evaluation_time():
    decision, envelope, resolver = build()
    verify_science_node_admission_decision_v2(
        decision, profile=load(PROFILE), signed_manifest=envelope,
        capability_registry=load(REGISTRY), build_lock=load(BUILD_LOCK), key_resolver=resolver
    )
