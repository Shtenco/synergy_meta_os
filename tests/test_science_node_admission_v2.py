from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from synergy_meta_os.capability_registry_consumer_v1 import canonical_json
from synergy_meta_os.manifest_v2 import sign_manifest_v2
from synergy_meta_os.node_admission_decision_v2 import NodeAdmissionV2Error, evaluate_science_node_admission_v2, verify_science_node_admission_decision_v2


REGISTRY = Path("fixtures/capabilities/synergy_capability_registry_v1.json")
PROFILE = Path("fixtures/node_profiles/science_research_node_v1.json")
LOCK = Path("fixtures/node_build_locks/science_research_node_source_candidate_v2.json")
REGISTRY_DIGEST = "3727810480e5660129fc63a2d7999b988ed9ae387365d4501bb50b7ae7257913"
NOW = datetime(2026,8,21,17,30,tzinfo=timezone.utc)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def body():
    return {
        "schema":"synergy.node-manifest/v2","node_id":"science-node-001","generation":1,
        "issued_at":"2026-08-21T16:00:00Z","expires_at":"2026-08-22T16:00:00Z",
        "capability_registry_digest":REGISTRY_DIGEST,
        "capabilities":["CONTENT_CACHE","NEXUS_COMPUTE","P2P_RELAY","SCIENCE_RESEARCH"],
        "services":[
            {"service_id":"content-cache","kind":"CONTENT_CACHE","repository":"Shtenco/synergynet","artifact_digest":"11"*32,"required_capabilities":["CONTENT_CACHE"],"desired_state":"ENABLED"},
            {"service_id":"nexus","kind":"NEXUS","repository":"Shtenco/agi_nexus","artifact_digest":"22"*32,"required_capabilities":["NEXUS_COMPUTE"],"desired_state":"ENABLED"},
            {"service_id":"science-agent","kind":"SCIENCE_AGENT","repository":"Shtenco/nexus_science_agent","artifact_digest":"33"*32,"required_capabilities":["SCIENCE_RESEARCH"],"desired_state":"ENABLED"},
            {"service_id":"synergynet","kind":"SYNERGYNET","repository":"Shtenco/synergynet","artifact_digest":"44"*32,"required_capabilities":["P2P_RELAY"],"desired_state":"ENABLED"}
        ]
    }


def signed_manifest(manifest_body=None):
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    envelope = sign_manifest_v2(manifest_body or body(), load(REGISTRY), private, key_id="node-key")
    return envelope, lambda key_id: public


def evaluate(manifest_body=None):
    envelope, resolver = signed_manifest(manifest_body)
    decision = evaluate_science_node_admission_v2(profile=load(PROFILE), signed_manifest=envelope, capability_registry=load(REGISTRY), build_lock=load(LOCK), key_resolver=resolver, now=NOW)
    return decision, envelope, resolver


def test_current_science_node_is_blocked_only_on_build_evidence():
    decision, envelope, resolver = evaluate()
    assert decision["status"] == "BLOCKED_BUILD_EVIDENCE"
    assert decision["blockers"] == ["BUILD_EVIDENCE_MISSING"]
    assert decision["deployment_authority"] == "NONE"
    verify_science_node_admission_decision_v2(decision, profile=load(PROFILE), signed_manifest=envelope, capability_registry=load(REGISTRY), build_lock=load(LOCK), key_resolver=resolver, now=NOW)


def test_fresh_hash_cannot_promote_blocked_decision_to_reviewable():
    decision, envelope, resolver = evaluate()
    tampered = copy.deepcopy(decision)
    tampered["status"] = "ADMISSION_REVIEWABLE"
    tampered["blockers"] = []
    body_part = dict(tampered)
    body_part.pop("decision_digest")
    tampered["decision_digest"] = hashlib.sha256(canonical_json(body_part)).hexdigest()
    with pytest.raises(NodeAdmissionV2Error):
        verify_science_node_admission_decision_v2(tampered, profile=load(PROFILE), signed_manifest=envelope, capability_registry=load(REGISTRY), build_lock=load(LOCK), key_resolver=resolver, now=NOW)


def test_signed_midas_escalation_blocks_profile_before_build_gate():
    manifest_body = body()
    manifest_body["capabilities"].append("MIDAS_ANALYSIS")
    manifest_body["capabilities"].sort()
    manifest_body["services"].append({"service_id":"midas","kind":"MIDAS","repository":"Shtenco/midas_ai","artifact_digest":"55"*32,"required_capabilities":["MIDAS_ANALYSIS"],"desired_state":"ENABLED"})
    manifest_body["services"] = sorted(manifest_body["services"], key=lambda x:x["service_id"])
    decision, _, _ = evaluate(manifest_body)
    assert decision["status"] == "BLOCKED_PROFILE"
    assert "PROFILE_NONCONFORMANT" in decision["blockers"]
