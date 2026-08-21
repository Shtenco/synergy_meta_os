from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .manifest import ManifestError
from .runtime_v2 import CurrentServiceState


SAFE_INT_MAX = 2**53 - 1


def _canonical(value: Any) -> bytes:
    def check(v: Any) -> None:
        if v is None or isinstance(v, (str, bool)):
            return
        if isinstance(v, int) and not isinstance(v, bool):
            if abs(v) > SAFE_INT_MAX:
                raise ManifestError("unsafe integer in durable state")
            return
        if isinstance(v, float):
            raise ManifestError("floats are forbidden in durable supervisor state")
        if isinstance(v, list):
            for item in v:
                check(item)
            return
        if isinstance(v, dict):
            if any(not isinstance(k, str) for k in v):
                raise ManifestError("state keys must be strings")
            for item in v.values():
                check(item)
            return
        raise ManifestError("unsupported durable-state value")
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise ManifestError(f"{label} must be lowercase sha256")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise ManifestError(f"{label} must be lowercase sha256")


def make_supervisor_state(
    *,
    node_id: str,
    generation: int,
    manifest_body_digest: str,
    current_states: tuple[CurrentServiceState, ...],
    previous_state_digest: str | None,
) -> dict[str, Any]:
    if not isinstance(node_id, str) or not node_id:
        raise ManifestError("node_id required")
    if isinstance(generation, bool) or not isinstance(generation, int) or not (1 <= generation <= SAFE_INT_MAX):
        raise ManifestError("generation must be a positive safe integer")
    _validate_digest(manifest_body_digest, "manifest_body_digest")
    if previous_state_digest is not None:
        _validate_digest(previous_state_digest, "previous_state_digest")

    services = []
    seen: set[str] = set()
    for state in sorted(current_states, key=lambda item: item.service_id):
        state.validate()
        if state.service_id in seen:
            raise ManifestError("duplicate service state")
        seen.add(state.service_id)
        services.append({
            "service_id": state.service_id,
            "state": state.state,
            "artifact_digest": state.artifact_digest,
        })
    body = {
        "schema": "synergy.supervisor-state/v3",
        "node_id": node_id,
        "generation": generation,
        "manifest_body_digest": manifest_body_digest,
        "previous_state_digest": previous_state_digest,
        "services": services,
        "execution_authority": "NONE",
    }
    return body | {"state_digest": _sha(body)}


def verify_supervisor_state(payload: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema", "node_id", "generation", "manifest_body_digest",
        "previous_state_digest", "services", "execution_authority", "state_digest",
    }
    if set(payload) != expected or payload["schema"] != "synergy.supervisor-state/v3":
        raise ManifestError("unexpected durable-state shape/schema")
    supplied = payload["state_digest"]
    _validate_digest(supplied, "state_digest")
    body = dict(payload)
    body.pop("state_digest")
    rebuilt = make_supervisor_state(
        node_id=body["node_id"],
        generation=body["generation"],
        manifest_body_digest=body["manifest_body_digest"],
        current_states=tuple(CurrentServiceState(item["service_id"], item["state"], item["artifact_digest"]) for item in body["services"]),
        previous_state_digest=body["previous_state_digest"],
    )
    if rebuilt != payload:
        raise ManifestError("durable supervisor state digest/content mismatch")
    if payload["execution_authority"] != "NONE":
        raise ManifestError("durable state cannot execute services")
    return payload


class DurableSupervisorStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.history = self.root / "history"
        self.root.mkdir(parents=True, exist_ok=True)
        self.history.mkdir(parents=True, exist_ok=True)

    def _history_path(self, digest: str) -> Path:
        _validate_digest(digest, "state_digest")
        return self.history / f"{digest}.json"

    def _atomic_write(self, path: Path, data: bytes) -> None:
        fd, tmp = tempfile.mkstemp(prefix=".state-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass

    def load_current(self) -> dict[str, Any] | None:
        pointer = self.root / "current.json"
        if not pointer.exists():
            return None
        try:
            pointer_payload = json.loads(pointer.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ManifestError("invalid durable-state pointer") from exc
        if set(pointer_payload) != {"state_digest"}:
            raise ManifestError("unexpected durable-state pointer shape")
        digest = pointer_payload["state_digest"]
        _validate_digest(digest, "state_digest")
        history_path = self._history_path(digest)
        try:
            payload = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ManifestError("durable-state history missing/corrupt") from exc
        verified = verify_supervisor_state(payload)
        if verified["state_digest"] != digest:
            raise ManifestError("durable-state pointer mismatch")
        return verified

    def commit(self, payload: dict[str, Any]) -> str:
        payload = verify_supervisor_state(payload)
        current = self.load_current()
        if current is not None:
            if payload["node_id"] != current["node_id"]:
                raise ManifestError("durable store cannot switch node identity")
            if payload["generation"] < current["generation"]:
                raise ManifestError("durable generation rollback blocked")
            if payload["generation"] == current["generation"] and payload["manifest_body_digest"] != current["manifest_body_digest"]:
                raise ManifestError("same generation cannot change manifest bytes")
            if payload["previous_state_digest"] != current["state_digest"]:
                raise ManifestError("durable state chain fork/stale writer blocked")
        elif payload["previous_state_digest"] is not None:
            raise ManifestError("genesis durable state must have null previous digest")

        digest = payload["state_digest"]
        history_path = self._history_path(digest)
        data = _canonical(payload)
        if history_path.exists():
            existing = history_path.read_bytes()
            if existing != data:
                raise ManifestError("state digest collision/inconsistent history")
        else:
            self._atomic_write(history_path, data)
        self._atomic_write(self.root / "current.json", _canonical({"state_digest": digest}))
        return digest
