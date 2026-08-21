from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from synergy_meta_os.manifest_v2 import sign_manifest_v2
from synergy_meta_os.science_node_profile_consumer_v1 import evaluate_signed_manifest_v2_for_science_profile


REGISTRY = Path("fixtures/capabilities/synergy_capability_registry_v1.json")
PROFILE = Path("fixtures/node_profiles/science_research_node_v1.json")
REGISTRY_DIGEST = "3727810480e5660129fc63a2d7999b988ed9ae387365d4501bb50b7ae7257913"


def load(path):
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


def evaluate(body):
    envelope, resolver = signed(body)
    return evaluate_signed_manifest_v2_for_science_profile(
        profile=load(PROFILE), signed_manifest=envelope, capability_registry=load(REGISTRY), key_resolver=resolver,
        now=datetime(2026,8,21,17,0,tzinfo=timezone.utc)
    )


def test_exact_science_manifest_is_profile_conformant():
    result = evaluate(base_body())
    assert result.status == "PROFILE_CONFORMANT"
    assert result.blockers == ()
    assert result.execution_authority == "NONE"


def test_correctly_resigned_midas_escalation_is_still_nonconformant():
    body = base_body()
    body["capabilities"].append("MIDAS_ANALYSIS")
    body["capabilities"].sort()
    body["services"].append({"service_id":"midas","kind":"MIDAS","repository":"Shtenco/midas_ai","artifact_digest":"55"*32,"required_capabilities":["MIDAS_ANALYSIS"],"desired_state":"ENABLED"})
    body["services"] = sorted(body["services"], key=lambda x:x["service_id"])
    result = evaluate(body)
    assert result.status == "SIGNED_BUT_PROFILE_NONCONFORMANT"
    assert "CAPABILITY_SET_MISMATCH" in result.blockers
    assert "SERVICE_SET_MISMATCH" in result.blockers


def test_correctly_resigned_metapay_escalation_is_nonconformant():
    body = base_body()
    body["capabilities"].append("METAPAY_GATEWAY")
    body["capabilities"].sort()
    body["services"].append({"service_id":"metapay","kind":"METAPAY","repository":"Shtenco/synergy_pay_system","artifact_digest":"66"*32,"required_capabilities":["METAPAY_GATEWAY"],"desired_state":"ENABLED"})
    body["services"] = sorted(body["services"], key=lambda x:x["service_id"])
    result = evaluate(body)
    assert result.status == "SIGNED_BUT_PROFILE_NONCONFORMANT"
    assert "FORBIDDEN_CAPABILITY_PRESENT" in result.blockers
    assert "FORBIDDEN_SERVICE_KIND_PRESENT" in result.blockers
