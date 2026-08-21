import pytest

from synergy_meta_os.manifest import ManifestError
from synergy_meta_os.runtime_v2 import ArtifactStore, CurrentServiceState, GenerationGuard, plan_lifecycle


def body_for(digest: str, desired_state: str = "ENABLED") -> dict:
    return {
        "schema": "synergy.node-manifest/v1",
        "node_id": "node-001",
        "generation": 2,
        "issued_at": "2026-08-21T06:00:00Z",
        "expires_at": "2026-08-22T06:00:00Z",
        "capabilities": ["P2P_RELAY"],
        "services": [{
            "service_id": "synergynet-main",
            "kind": "SYNERGYNET",
            "repository": "Shtenco/synergynet",
            "artifact_digest": digest,
            "required_capabilities": ["P2P_RELAY"],
            "desired_state": desired_state,
        }],
    }


def test_artifact_store_round_trip():
    store = ArtifactStore()
    digest = store.put(b"artifact-v1")
    assert store.get_verified(digest) == b"artifact-v1"


def test_generation_guard_blocks_rollback_and_same_generation_change():
    guard = GenerationGuard()
    guard.accept(node_id="node-1", generation=2, body_digest="1" * 64)
    guard.accept(node_id="node-1", generation=2, body_digest="1" * 64)
    with pytest.raises(ManifestError):
        guard.accept(node_id="node-1", generation=1, body_digest="2" * 64)
    with pytest.raises(ManifestError):
        guard.accept(node_id="node-1", generation=2, body_digest="3" * 64)


def test_present_artifact_is_startable_but_has_no_execution_authority():
    store = ArtifactStore()
    digest = store.put(b"synergynet-artifact")
    action = plan_lifecycle(body_for(digest), artifact_store=store)[0]
    assert action.action == "STARTABLE"
    assert action.execution_authority == "NONE"


def test_missing_artifact_is_blocked():
    action = plan_lifecycle(body_for("a" * 64), artifact_store=ArtifactStore())[0]
    assert action.action == "BLOCKED_ARTIFACT"


def test_changed_artifact_is_upgrade_pending_not_automatic():
    store = ArtifactStore()
    desired = store.put(b"artifact-v2")
    current = CurrentServiceState("synergynet-main", "RUNNING", "b" * 64)
    action = plan_lifecycle(body_for(desired), artifact_store=store, current_states=(current,))[0]
    assert action.action == "UPGRADE_PENDING"
    assert action.execution_authority == "NONE"


def test_disabled_running_service_is_stoppable():
    store = ArtifactStore()
    digest = store.put(b"artifact-v1")
    current = CurrentServiceState("synergynet-main", "RUNNING", digest)
    action = plan_lifecycle(body_for(digest, desired_state="DISABLED"), artifact_store=store, current_states=(current,))[0]
    assert action.action == "STOPPABLE"
