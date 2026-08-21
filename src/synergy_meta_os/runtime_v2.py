from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from .manifest import ManifestError, ServiceDecision, reconcile_services


@dataclass
class ArtifactStore:
    """Content-addressed reference store. V2 stores bytes in memory; production storage is separate."""

    blobs: dict[str, bytes] = field(default_factory=dict)

    def put(self, payload: bytes) -> str:
        if not isinstance(payload, (bytes, bytearray)):
            raise ManifestError("artifact payload must be bytes")
        payload = bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        existing = self.blobs.get(digest)
        if existing is not None and existing != payload:
            raise ManifestError("sha256 collision/inconsistent artifact store")
        self.blobs[digest] = payload
        return digest

    def has(self, digest: str) -> bool:
        return digest in self.blobs

    def get_verified(self, digest: str) -> bytes:
        payload = self.blobs.get(digest)
        if payload is None:
            raise ManifestError("artifact missing")
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ManifestError("artifact store corruption")
        return payload


@dataclass
class GenerationGuard:
    """In-memory reference anti-rollback guard; production must persist this atomically."""

    highest_generation: dict[str, int] = field(default_factory=dict)
    accepted_body_digest: dict[str, str] = field(default_factory=dict)

    def accept(self, *, node_id: str, generation: int, body_digest: str) -> None:
        if not isinstance(node_id, str) or not node_id:
            raise ManifestError("node_id required")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1 or generation > 2**53 - 1:
            raise ManifestError("generation must be positive safe integer")
        _digest(body_digest, "body_digest")
        previous = self.highest_generation.get(node_id)
        if previous is not None and generation < previous:
            raise ManifestError("manifest generation rollback blocked")
        if previous == generation:
            prior_digest = self.accepted_body_digest[node_id]
            if prior_digest != body_digest:
                raise ManifestError("same manifest generation cannot change bytes")
            return
        self.highest_generation[node_id] = generation
        self.accepted_body_digest[node_id] = body_digest


@dataclass(frozen=True)
class CurrentServiceState:
    service_id: str
    state: str
    artifact_digest: str | None = None

    def validate(self) -> None:
        if not self.service_id:
            raise ManifestError("service_id required")
        if self.state not in {"STOPPED", "RUNNING"}:
            raise ManifestError("unknown current service state")
        if self.state == "RUNNING":
            if self.artifact_digest is None:
                raise ManifestError("running service requires artifact digest")
            _digest(self.artifact_digest, "artifact_digest")
        elif self.artifact_digest is not None:
            _digest(self.artifact_digest, "artifact_digest")


@dataclass(frozen=True)
class LifecycleAction:
    service_id: str
    action: str
    desired_artifact_digest: str | None
    blockers: tuple[str, ...] = ()
    execution_authority: str = "NONE"


_ALLOWED_ACTIONS = {
    "STARTABLE",
    "STOPPABLE",
    "UPGRADE_PENDING",
    "NOOP_RUNNING",
    "NOOP_STOPPED",
    "BLOCKED_CAPABILITY",
    "BLOCKED_ARTIFACT",
}


def plan_lifecycle(
    manifest_body: dict[str, Any],
    *,
    artifact_store: ArtifactStore,
    current_states: tuple[CurrentServiceState, ...] = (),
) -> tuple[LifecycleAction, ...]:
    decisions = {d.service_id: d for d in reconcile_services(manifest_body)}
    current: dict[str, CurrentServiceState] = {}
    for state in current_states:
        state.validate()
        if state.service_id in current:
            raise ManifestError("duplicate current service state")
        current[state.service_id] = state

    actions: list[LifecycleAction] = []
    service_by_id = {service["service_id"]: service for service in manifest_body["services"]}
    for service_id in sorted(service_by_id):
        service = service_by_id[service_id]
        decision: ServiceDecision = decisions[service_id]
        state = current.get(service_id, CurrentServiceState(service_id, "STOPPED"))
        desired_digest = service["artifact_digest"]

        if decision.state == "BLOCKED_CAPABILITY":
            actions.append(LifecycleAction(service_id, "BLOCKED_CAPABILITY", desired_digest, decision.blockers))
            continue

        if decision.state == "DISABLED":
            action = "STOPPABLE" if state.state == "RUNNING" else "NOOP_STOPPED"
            actions.append(LifecycleAction(service_id, action, None))
            continue

        if not artifact_store.has(desired_digest):
            actions.append(LifecycleAction(service_id, "BLOCKED_ARTIFACT", desired_digest, ("ARTIFACT_NOT_PRESENT",)))
            continue
        artifact_store.get_verified(desired_digest)

        if state.state == "STOPPED":
            actions.append(LifecycleAction(service_id, "STARTABLE", desired_digest))
        elif state.artifact_digest == desired_digest:
            actions.append(LifecycleAction(service_id, "NOOP_RUNNING", desired_digest))
        else:
            actions.append(LifecycleAction(service_id, "UPGRADE_PENDING", desired_digest))

    for action in actions:
        if action.action not in _ALLOWED_ACTIONS or action.execution_authority != "NONE":
            raise ManifestError("invalid lifecycle action")
    return tuple(actions)


def _digest(value: str, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise ManifestError(f"{label} must be lowercase sha256")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise ManifestError(f"{label} must be lowercase sha256")
