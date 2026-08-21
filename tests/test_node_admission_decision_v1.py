import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from synergy_meta_os.manifest import sign_manifest
from synergy_meta_os.node_admission_decision_v1 import (
    NodeAdmissionDecisionError,
    build_node_admission_decision_v1,
    decision_digest,
    verify_node_admission_decision_v1,
)

ROOT = Path(__file__).resolve().parents[1]
EVALUATED_AT = datetime(2026, 8, 21, 13, 30, 0, tzinfo=timezone.utc)


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


def signed_manifest():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    envelope = sign_manifest(research_body(), private, key_id="test-key")
    return envelope, lambda key_id: public


def test_canonical_blocked_admission_matches_fixed_fixture():
    profile = load_json("fixtures/node_profiles/research_compute_node_v1.json")
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    envelope, resolver = signed_manifest()
    decision = build_node_admission_decision_v1(
        profile=profile,
        source_lock=source_lock,
        signed_manifest=envelope,
        key_resolver=resolver,
        evaluated_at=EVALUATED_AT,
    )
    expected = load_json("fixtures/node_admission/research_compute_node_blocked_build_v1.json")
    assert decision == expected
    assert decision["decision_digest"] == "cac0a7dca9ac1c304ca9d37577d32c95024de02edf4c70f283d5474ddfcbb9a1"
    verify_node_admission_decision_v1(
        decision,
        profile=profile,
        source_lock=source_lock,
        signed_manifest=envelope,
        key_resolver=resolver,
    )


def test_fresh_hash_cannot_change_blocked_decision_into_admitted():
    profile = load_json("fixtures/node_profiles/research_compute_node_v1.json")
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    envelope, resolver = signed_manifest()
    decision = build_node_admission_decision_v1(
        profile=profile, source_lock=source_lock, signed_manifest=envelope,
        key_resolver=resolver, evaluated_at=EVALUATED_AT
    )
    decision["admission_status"] = "ADMITTED"
    decision["blockers"] = []
    decision["decision_digest"] = decision_digest(decision)
    with pytest.raises(NodeAdmissionDecisionError, match="does not match raw evidence"):
        verify_node_admission_decision_v1(
            decision,
            profile=profile,
            source_lock=source_lock,
            signed_manifest=envelope,
            key_resolver=resolver,
        )


def test_fresh_hash_cannot_grant_execution_authority():
    profile = load_json("fixtures/node_profiles/research_compute_node_v1.json")
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    envelope, resolver = signed_manifest()
    decision = build_node_admission_decision_v1(
        profile=profile, source_lock=source_lock, signed_manifest=envelope,
        key_resolver=resolver, evaluated_at=EVALUATED_AT
    )
    decision["execution_authority"] = "PROCESS_START"
    decision["decision_digest"] = decision_digest(decision)
    with pytest.raises(NodeAdmissionDecisionError, match="cannot grant execution_authority"):
        verify_node_admission_decision_v1(
            decision,
            profile=profile,
            source_lock=source_lock,
            signed_manifest=envelope,
            key_resolver=resolver,
        )


def test_historical_verification_uses_original_evaluation_time():
    profile = load_json("fixtures/node_profiles/research_compute_node_v1.json")
    source_lock = load_json("fixtures/node_build_locks/research_compute_node_source_candidate_v1.json")
    envelope, resolver = signed_manifest()
    decision = build_node_admission_decision_v1(
        profile=profile, source_lock=source_lock, signed_manifest=envelope,
        key_resolver=resolver, evaluated_at=EVALUATED_AT
    )
    # Verification does not reinterpret the historical decision at wall-clock time.
    verify_node_admission_decision_v1(
        decision,
        profile=profile,
        source_lock=source_lock,
        signed_manifest=envelope,
        key_resolver=resolver,
    )
