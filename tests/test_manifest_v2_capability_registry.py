from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from synergy_meta_os.manifest_v2 import ManifestV2Error, sign_manifest_v2, verify_manifest_v2


REGISTRY = Path("fixtures/capabilities/synergy_capability_registry_v1.json")
REGISTRY_DIGEST = "3727810480e5660129fc63a2d7999b988ed9ae387365d4501bb50b7ae7257913"


def registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def science_body():
    return {
        "schema":"synergy.node-manifest/v2",
        "node_id":"science-node-001",
        "generation":1,
        "issued_at":"2026-08-21T16:00:00Z",
        "expires_at":"2026-08-22T16:00:00Z",
        "capability_registry_digest":REGISTRY_DIGEST,
        "capabilities":["SCIENCE_RESEARCH"],
        "services":[{
            "service_id":"science-agent",
            "kind":"SCIENCE_AGENT",
            "repository":"Shtenco/nexus_science_agent",
            "artifact_digest":"11" * 32,
            "required_capabilities":["SCIENCE_RESEARCH"],
            "desired_state":"ENABLED"
        }]
    }


def keys():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    return private, lambda key_id: public


def test_v2_accepts_registry_defined_science_service():
    private, resolver = keys()
    envelope = sign_manifest_v2(science_body(), registry(), private, key_id="node-key-1")
    body = verify_manifest_v2(envelope, registry(), resolver, now=datetime(2026,8,21,17,0,tzinfo=timezone.utc))
    assert body["capabilities"] == ["SCIENCE_RESEARCH"]
    assert envelope["execution_authority"] == "NONE"


def test_wrong_repository_for_registry_kind_fails():
    body = science_body()
    body["services"][0]["repository"] = "Shtenco/agi_nexus"
    private, _ = keys()
    with pytest.raises(ManifestV2Error):
        sign_manifest_v2(body, registry(), private, key_id="node-key-1")


def test_unknown_capability_fails():
    body = science_body()
    body["capabilities"] = ["ROOT_SHELL"]
    private, _ = keys()
    with pytest.raises(ManifestV2Error):
        sign_manifest_v2(body, registry(), private, key_id="node-key-1")


def test_registry_digest_is_pinned():
    body = science_body()
    body["capability_registry_digest"] = "22" * 32
    private, _ = keys()
    with pytest.raises(ManifestV2Error):
        sign_manifest_v2(body, registry(), private, key_id="node-key-1")


def test_fresh_signature_cannot_grant_execution_authority():
    private, resolver = keys()
    envelope = sign_manifest_v2(science_body(), registry(), private, key_id="node-key-1")
    tampered = copy.deepcopy(envelope)
    tampered["execution_authority"] = "PROCESS"
    with pytest.raises(ManifestV2Error):
        verify_manifest_v2(tampered, registry(), resolver)
