import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from synergy_meta_os.manifest import sign_manifest, verify_manifest
from synergy_meta_os.node_profile_consumer_v1 import (
    NodeProfileConsumerError,
    RESEARCH_PROFILE_DIGEST,
    evaluate_signed_manifest_for_research_profile,
    profile_digest,
    require_profile_conformance,
    verify_research_profile,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 21, 13, 0, 0, tzinfo=timezone.utc)


def load_profile():
    return json.loads((ROOT / "fixtures/node_profiles/research_compute_node_v1.json").read_text(encoding="utf-8"))


def research_body():
    return {
        "schema": "synergy.node-manifest/v1",
        "node_id": "research-node-001",
        "generation": 1,
        "issued_at": "2026-08-21T12:00:00Z",
        "expires_at": "2026-08-22T12:00:00Z",
        "capabilities": ["CONTENT_CACHE", "NEXUS_COMPUTE", "P2P_RELAY"],
        "services": [
            {
                "service_id": "content-cache",
                "kind": "CONTENT_CACHE",
                "repository": "Shtenco/synergynet",
                "artifact_digest": "1" * 64,
                "required_capabilities": ["CONTENT_CACHE"],
                "desired_state": "ENABLED",
            },
            {
                "service_id": "nexus",
                "kind": "NEXUS",
                "repository": "Shtenco/agi_nexus",
                "artifact_digest": "2" * 64,
                "required_capabilities": ["NEXUS_COMPUTE"],
                "desired_state": "ENABLED",
            },
            {
                "service_id": "synergynet",
                "kind": "SYNERGYNET",
                "repository": "Shtenco/synergynet",
                "artifact_digest": "3" * 64,
                "required_capabilities": ["P2P_RELAY"],
                "desired_state": "ENABLED",
            },
        ],
    }


def signed(body):
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    envelope = sign_manifest(body, private, key_id="test-key")
    return envelope, lambda key_id: public


def test_exact_profile_fixture_is_accepted():
    profile = load_profile()
    verify_research_profile(profile)
    assert profile_digest(profile) == RESEARCH_PROFILE_DIGEST


def test_signed_research_manifest_is_profile_conformant_and_non_authoritative():
    profile = load_profile()
    envelope, resolver = signed(research_body())
    verify_manifest(envelope, resolver, now=NOW)
    result = evaluate_signed_manifest_for_research_profile(
        profile=profile, signed_manifest=envelope, key_resolver=resolver, now=NOW
    )
    assert result.status == "PROFILE_CONFORMANT"
    assert result.blockers == ()
    assert result.financial_authority == "NONE"
    assert result.payment_authority == "NONE"
    assert result.accounting_authority == "NONE"
    assert result.execution_authority == "NONE"
    require_profile_conformance(result)


def test_correctly_resigned_metapay_escalation_is_still_profile_nonconformant():
    profile = load_profile()
    body = research_body()
    body["capabilities"] = ["CONTENT_CACHE", "METAPAY_GATEWAY", "NEXUS_COMPUTE", "P2P_RELAY"]
    body["services"].append({
        "service_id": "metapay",
        "kind": "METAPAY",
        "repository": "Shtenco/synergy_pay_system",
        "artifact_digest": "4" * 64,
        "required_capabilities": ["METAPAY_GATEWAY"],
        "desired_state": "ENABLED",
    })
    envelope, resolver = signed(body)
    # Cryptographic identity is valid.
    verify_manifest(envelope, resolver, now=NOW)
    # Architecture authorization is not.
    result = evaluate_signed_manifest_for_research_profile(
        profile=profile, signed_manifest=envelope, key_resolver=resolver, now=NOW
    )
    assert result.status == "SIGNED_BUT_PROFILE_NONCONFORMANT"
    assert "FORBIDDEN_CAPABILITY_PRESENT" in result.blockers
    assert "FORBIDDEN_SERVICE_KIND_PRESENT" in result.blockers
    with pytest.raises(ValueError, match="does not conform"):
        require_profile_conformance(result)


def test_fresh_profile_digest_cannot_add_financial_authority():
    profile = load_profile()
    profile["payment_authority"] = "METAPAY"
    profile["profile_digest"] = profile_digest(profile)
    with pytest.raises(NodeProfileConsumerError, match="payment_authority"):
        verify_research_profile(profile)


def test_profile_requires_exact_service_repositories():
    profile = load_profile()
    profile["required_services"][1]["repository"] = "Shtenco/agi_olga"
    profile["profile_digest"] = profile_digest(profile)
    with pytest.raises(NodeProfileConsumerError, match="identity drifted"):
        verify_research_profile(profile)


def test_signed_manifest_cannot_disable_required_nexus_service():
    profile = load_profile()
    body = research_body()
    body["services"][1]["desired_state"] = "DISABLED"
    envelope, resolver = signed(body)
    result = evaluate_signed_manifest_for_research_profile(
        profile=profile, signed_manifest=envelope, key_resolver=resolver, now=NOW
    )
    assert result.status == "SIGNED_BUT_PROFILE_NONCONFORMANT"
    assert "SERVICE_NOT_ENABLED:nexus" in result.blockers
