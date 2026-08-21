from copy import deepcopy
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from synergy_meta_os import ManifestError, reconcile_services, sign_manifest, verify_manifest


def _body():
    return {
        "schema": "synergy.node-manifest/v1",
        "node_id": "node-lab-001",
        "generation": 1,
        "issued_at": "2026-08-21T05:00:00Z",
        "expires_at": "2026-08-22T05:00:00Z",
        "capabilities": ["CONTENT_CACHE", "NEXUS_COMPUTE", "P2P_RELAY"],
        "services": [
            {
                "service_id": "mesh",
                "kind": "SYNERGYNET",
                "repository": "Shtenco/synergynet",
                "artifact_digest": "11" * 32,
                "required_capabilities": ["P2P_RELAY"],
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
                "service_id": "payments",
                "kind": "METAPAY",
                "repository": "Shtenco/synergy_pay_system",
                "artifact_digest": "33" * 32,
                "required_capabilities": ["METAPAY_GATEWAY"],
                "desired_state": "ENABLED",
            },
        ],
    }


def test_ed25519_manifest_round_trip_and_capability_reconciliation():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    envelope = sign_manifest(_body(), private, key_id="lab-key-1")
    verified = verify_manifest(
        envelope,
        lambda key_id: public if key_id == "lab-key-1" else (_ for _ in ()).throw(KeyError(key_id)),
        now=datetime(2026, 8, 21, 6, 0, tzinfo=timezone.utc),
    )
    decisions = {item.service_id: item for item in reconcile_services(verified)}
    assert decisions["mesh"].state == "RUNNABLE"
    assert decisions["nexus"].state == "RUNNABLE"
    assert decisions["payments"].state == "BLOCKED_CAPABILITY"
    assert decisions["payments"].blockers == ("METAPAY_GATEWAY",)


def test_manifest_tamper_fails_even_when_body_digest_is_recomputed_without_signature():
    import hashlib
    from synergy_meta_os import canonical_json

    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    envelope = sign_manifest(_body(), private, key_id="k")
    broken = deepcopy(envelope)
    broken["body"]["capabilities"].append("METAPAY_GATEWAY")
    broken["body"]["capabilities"].sort()
    broken["body_digest"] = hashlib.sha256(canonical_json(broken["body"])).hexdigest()
    with pytest.raises(ManifestError):
        verify_manifest(broken, lambda _: public, now=datetime(2026, 8, 21, 6, 0, tzinfo=timezone.utc))


def test_expired_manifest_is_rejected():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    envelope = sign_manifest(_body(), private, key_id="k")
    with pytest.raises(ManifestError):
        verify_manifest(envelope, lambda _: public, now=datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc))


def test_service_cannot_omit_kind_mandatory_capability():
    private = Ed25519PrivateKey.generate()
    body = _body()
    body["services"][0]["required_capabilities"] = []
    with pytest.raises(ManifestError):
        sign_manifest(body, private, key_id="k")


def test_float_and_unsafe_integer_are_forbidden_in_signed_bytes():
    private = Ed25519PrivateKey.generate()
    body = _body()
    body["generation"] = 2**53
    with pytest.raises(ManifestError):
        sign_manifest(body, private, key_id="k")
