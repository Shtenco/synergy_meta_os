import json
from pathlib import Path

import pytest

from synergy_meta_os.durable_state_v3 import DurableSupervisorStore, make_supervisor_state
from synergy_meta_os.manifest import ManifestError
from synergy_meta_os.runtime_v2 import CurrentServiceState


D1 = "1" * 64
D2 = "2" * 64
A1 = "a" * 64
A2 = "b" * 64


def _state(generation, manifest, services, prev=None):
    return make_supervisor_state(
        node_id="node-1",
        generation=generation,
        manifest_body_digest=manifest,
        current_states=tuple(services),
        previous_state_digest=prev,
    )


def test_state_survives_restart_and_preserves_running_artifact(tmp_path: Path):
    store = DurableSupervisorStore(tmp_path / "state")
    first = _state(1, D1, [CurrentServiceState("mesh", "RUNNING", A1)])
    digest = store.commit(first)
    restarted = DurableSupervisorStore(tmp_path / "state")
    loaded = restarted.load_current()
    assert loaded["state_digest"] == digest
    assert loaded["services"] == [{"service_id":"mesh","state":"RUNNING","artifact_digest":A1}]


def test_runtime_transition_same_manifest_forms_hash_chain(tmp_path: Path):
    store = DurableSupervisorStore(tmp_path / "state")
    stopped = _state(1, D1, [CurrentServiceState("mesh", "STOPPED")])
    d1 = store.commit(stopped)
    running = _state(1, D1, [CurrentServiceState("mesh", "RUNNING", A1)], d1)
    d2 = store.commit(running)
    assert d1 != d2
    assert store.load_current()["previous_state_digest"] == d1


def test_manifest_generation_rollback_and_same_generation_drift_blocked(tmp_path: Path):
    store = DurableSupervisorStore(tmp_path / "state")
    one = _state(2, D2, [], None)
    d1 = store.commit(one)
    with pytest.raises(ManifestError):
        store.commit(_state(1, D1, [], d1))
    with pytest.raises(ManifestError):
        store.commit(_state(2, D1, [], d1))


def test_stale_writer_cannot_fork_state_chain(tmp_path: Path):
    store = DurableSupervisorStore(tmp_path / "state")
    genesis = _state(1, D1, [], None)
    d1 = store.commit(genesis)
    d2 = store.commit(_state(1, D1, [CurrentServiceState("a", "RUNNING", A1)], d1))
    with pytest.raises(ManifestError):
        store.commit(_state(1, D1, [CurrentServiceState("b", "RUNNING", A2)], d1))
    assert store.load_current()["state_digest"] == d2


def test_history_tamper_is_detected(tmp_path: Path):
    store = DurableSupervisorStore(tmp_path / "state")
    payload = _state(1, D1, [], None)
    digest = store.commit(payload)
    path = store.history / f"{digest}.json"
    tampered = json.loads(path.read_text())
    tampered["generation"] = 2
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ManifestError):
        store.load_current()
