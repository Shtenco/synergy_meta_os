from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from synergy_meta_os.v31 import (
    ActivationError,
    ArtifactStore,
    AuditChain,
    ManifestError,
    NodeSupervisor,
    SupervisorState,
    canonical_json,
    make_activation_grant,
    make_manifest,
    sign_activation_grant,
    sign_manifest,
    validate_manifest_body,
    verify_manifest,
)


HOST_COMMIT = "81fa56ef8d7e33ceeaa9a829416c9c34f5aa1536"
HOST_RELEASE = "f2aa3424662a8e1b025fb253fb73da7897b50a6b3bd9c327379b580e726ee623"
GOOD_SCRIPT = b"#!/usr/bin/python3\nimport signal,time\nsignal.signal(signal.SIGTERM,lambda *_:exit(0))\nwhile True: time.sleep(1)\n"
BAD_SCRIPT = b"#!/bin/sh\nexit 23\n"


def utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def service(
    service_id: str,
    digest: str,
    *,
    kind: str = "DIAGNOSTICS",
    capabilities: list[str] | None = None,
    depends_on: list[str] | None = None,
    key_refs: list[str] | None = None,
) -> dict:
    return {
        "service_id": service_id,
        "kind": kind,
        "repository": "Shtenco/synergy_meta_os",
        "artifact_digest": digest,
        "argv": ["$ARTIFACT"],
        "capabilities": capabilities or ["observability.emit"],
        "depends_on": depends_on or [],
        "desired_state": "ENABLED",
        "limits": {
            "memory_mib": 256,
            "cpu_seconds": 60,
            "open_files": 64,
            "processes": 8,
            "file_mib": 8,
        },
        "health": {"kind": "process_alive", "grace_ms": 30},
        "key_refs": key_refs or [],
    }


class V31Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest_key = Ed25519PrivateKey.generate()
        self.governance_key = Ed25519PrivateKey.generate()
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.supervisor = NodeSupervisor(
            root=self.root,
            manifest_key_resolver=lambda key_id: {"manifest-dev": self.manifest_key.public_key()}[key_id],
            governance_key_resolver=lambda key_id: {"governance-dev": self.governance_key.public_key()}[key_id],
        )

    def tearDown(self) -> None:
        self.supervisor.stop_all()
        self.tmp.cleanup()

    def manifest(self, services: list[dict], *, generation: int = 1, expires_delta: timedelta = timedelta(hours=1)) -> dict:
        body = make_manifest(
            node_id="node-dev-01",
            generation=generation,
            issued_at=utc(self.now - timedelta(seconds=1)),
            expires_at=utc(self.now + expires_delta),
            profile="EDGE_CLIENT",
            development=True,
            attestation_level="DEVELOPMENT",
            attestation_evidence_digest=None,
            host_ref="turbo-v30-unified-hhdm-metastorage-rc",
            host_commit_sha=HOST_COMMIT,
            host_release_sha256=HOST_RELEASE,
            services=sorted(services, key=lambda item: item["service_id"]),
        )
        return sign_manifest(body, self.manifest_key, key_id="manifest-dev", now=self.now)

    def grant(self, envelope: dict, *, nonce: str = "nonce-0000000001") -> dict:
        body = envelope["body"]
        grant = make_activation_grant(
            node_id=body["node_id"],
            manifest_body_digest=envelope["body_digest"],
            manifest_generation=body["generation"],
            allowed_services=[item["service_id"] for item in body["services"] if item["desired_state"] == "ENABLED"],
            issued_at=utc(self.now - timedelta(seconds=1)),
            expires_at=utc(self.now + timedelta(hours=1)),
            nonce=nonce,
        )
        return sign_activation_grant(grant, self.governance_key, key_id="governance-dev", now=self.now)


class TestCanonicalAndPolicy(V31Fixture):
    def test_canonical_rejects_float_and_unsafe_integer(self) -> None:
        with self.assertRaises(ManifestError):
            canonical_json({"x": 0.1})
        with self.assertRaises(ManifestError):
            canonical_json({"x": 2**53})

    def test_signature_tamper_is_rejected(self) -> None:
        digest = self.supervisor.artifacts.put(GOOD_SCRIPT)
        envelope = self.manifest([service("diag", digest)])
        verify_manifest(envelope, lambda _: self.manifest_key.public_key(), now=self.now)
        tampered = deepcopy(envelope)
        tampered["body"]["generation"] = 2
        with self.assertRaises(ManifestError):
            verify_manifest(tampered, lambda _: self.manifest_key.public_key(), now=self.now)

    def test_nexus_cannot_escalate_to_financial_execution(self) -> None:
        digest = "0" * 64
        item = service(
            "nexus",
            digest,
            kind="NEXUS",
            capabilities=["finance.execute", "nexus.infer", "observability.emit", "storage.read"],
        )
        body = make_manifest(
            node_id="nexus-node",
            generation=1,
            issued_at=utc(self.now - timedelta(seconds=1)),
            expires_at=utc(self.now + timedelta(hours=1)),
            profile="NEXUS_COMPUTE",
            development=True,
            attestation_level="DEVELOPMENT",
            attestation_evidence_digest=None,
            host_ref="turbo-v30-unified-hhdm-metastorage-rc",
            host_commit_sha=HOST_COMMIT,
            host_release_sha256=HOST_RELEASE,
            services=[item],
        )
        with self.assertRaises(ManifestError):
            validate_manifest_body(body, now=self.now)

    def test_raw_private_key_paths_are_rejected(self) -> None:
        digest = "0" * 64
        with self.assertRaises(ManifestError):
            self.manifest([service("diag", digest, key_refs=["/tmp/operator.pem"])])

    def test_dependency_cycle_is_rejected(self) -> None:
        digest = "0" * 64
        body = make_manifest(
            node_id="cycle-node",
            generation=1,
            issued_at=utc(self.now - timedelta(seconds=1)),
            expires_at=utc(self.now + timedelta(hours=1)),
            profile="EDGE_CLIENT",
            development=True,
            attestation_level="DEVELOPMENT",
            attestation_evidence_digest=None,
            host_ref="turbo-v30-unified-hhdm-metastorage-rc",
            host_commit_sha=HOST_COMMIT,
            host_release_sha256=HOST_RELEASE,
            services=[service("a", digest, depends_on=["b"]), service("b", digest, depends_on=["a"])],
        )
        with self.assertRaises(ManifestError):
            validate_manifest_body(body, now=self.now)

    def test_manifest_lifetime_is_bounded(self) -> None:
        digest = "0" * 64
        with self.assertRaises(ManifestError):
            self.manifest([service("diag", digest)], expires_delta=timedelta(days=8))


class TestArtifactsAndEvidence(V31Fixture):
    def test_artifact_corruption_is_detected(self) -> None:
        digest = self.supervisor.artifacts.put(b"payload")
        path = self.supervisor.artifacts.path_for(digest)
        os.chmod(path, 0o600)
        path.write_bytes(b"tampered")
        with self.assertRaises(ManifestError):
            self.supervisor.artifacts.get_verified(digest)

    def test_audit_chain_tamper_is_detected(self) -> None:
        self.supervisor.audit.append("TEST", value="one")
        path = self.supervisor.audit.path
        record = json.loads(path.read_text(encoding="utf-8"))
        record["data"]["value"] = "two"
        path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaises(ManifestError):
            self.supervisor.audit.verify()

    def test_state_chain_tamper_is_detected(self) -> None:
        digest = self.supervisor.artifacts.put(GOOD_SCRIPT)
        envelope = self.manifest([service("diag", digest)])
        self.supervisor.stage(envelope, now=self.now)
        with sqlite3.connect(self.supervisor.state.path) as db:
            db.execute("UPDATE state_history SET state_digest=? WHERE seq=1", ("f" * 64,))
            db.commit()
        with self.assertRaises(ManifestError):
            self.supervisor.state.verify_history()

    def test_cas_deduplicates_exact_bytes(self) -> None:
        store = ArtifactStore(self.root / "cas2")
        first = store.put(b"same")
        second = store.put(b"same")
        self.assertEqual(first, second)
        self.assertEqual(store.get_verified(first), b"same")


class TestLifecycle(V31Fixture):
    def test_manifest_is_admitted_but_does_not_run_without_grant(self) -> None:
        digest = self.supervisor.artifacts.put(GOOD_SCRIPT)
        envelope = self.manifest([service("diag", digest)])
        admitted = self.supervisor.stage(envelope, now=self.now)
        self.assertEqual(admitted["status"], "ADMITTED")
        self.assertEqual(self.supervisor.plan(now=self.now)["status"], "LAUNCHABLE")
        self.assertFalse(self.supervisor.running)
        self.assertEqual(self.supervisor.observed_status()["status"], "STOPPED")

    def test_exact_governance_grant_starts_and_nonce_replay_is_blocked(self) -> None:
        digest = self.supervisor.artifacts.put(GOOD_SCRIPT)
        envelope = self.manifest([service("diag", digest)])
        self.supervisor.stage(envelope, now=self.now)
        grant = self.grant(envelope)
        result = self.supervisor.activate(grant, now=self.now)
        self.assertEqual(result["status"], "RUNNING")
        self.assertFalse(result["production"])
        self.assertEqual(self.supervisor.observed_status()["status"], "RUNNING_OBSERVED")
        self.supervisor.stage(envelope, now=self.now)
        with self.assertRaises(ActivationError):
            self.supervisor.activate(grant, now=self.now)

    def test_generation_rollback_and_same_generation_fork_are_blocked(self) -> None:
        digest = self.supervisor.artifacts.put(GOOD_SCRIPT)
        gen2 = self.manifest([service("diag", digest)], generation=2)
        self.supervisor.stage(gen2, now=self.now)
        self.supervisor.activate(self.grant(gen2, nonce="generation-two-01"), now=self.now)
        gen1 = self.manifest([service("diag", digest)], generation=1)
        with self.assertRaises(ManifestError):
            self.supervisor.stage(gen1, now=self.now)
        fork = self.manifest([service("diag", digest), service("diag2", digest)], generation=2)
        with self.assertRaises(ManifestError):
            self.supervisor.stage(fork, now=self.now)

    def test_failed_upgrade_keeps_old_active_process_and_manifest(self) -> None:
        good_digest = self.supervisor.artifacts.put(GOOD_SCRIPT)
        first = self.manifest([service("diag", good_digest)], generation=1)
        self.supervisor.stage(first, now=self.now)
        self.supervisor.activate(self.grant(first, nonce="upgrade-good-0001"), now=self.now)
        old_pid = self.supervisor.running["diag"].process.pid

        bad_digest = self.supervisor.artifacts.put(BAD_SCRIPT)
        second = self.manifest([service("diag", bad_digest)], generation=2)
        self.supervisor.stage(second, now=self.now)
        with self.assertRaises(ActivationError):
            self.supervisor.activate(self.grant(second, nonce="upgrade-bad-00002"), now=self.now)
        self.assertIsNone(self.supervisor.running["diag"].process.poll())
        self.assertEqual(self.supervisor.running["diag"].process.pid, old_pid)
        self.assertEqual(self.supervisor.state.load_slot("ACTIVE")["body_digest"], first["body_digest"])

    def test_grant_cannot_expand_service_set(self) -> None:
        digest = self.supervisor.artifacts.put(GOOD_SCRIPT)
        envelope = self.manifest([service("diag", digest)])
        self.supervisor.stage(envelope, now=self.now)
        grant_body = make_activation_grant(
            node_id="node-dev-01",
            manifest_body_digest=envelope["body_digest"],
            manifest_generation=1,
            allowed_services=["diag", "invented"],
            issued_at=utc(self.now - timedelta(seconds=1)),
            expires_at=utc(self.now + timedelta(hours=1)),
            nonce="expanded-services-01",
        )
        grant = sign_activation_grant(grant_body, self.governance_key, key_id="governance-dev", now=self.now)
        with self.assertRaises(ActivationError):
            self.supervisor.activate(grant, now=self.now)


class TestDurability(unittest.TestCase):
    def test_reopen_preserves_generation_guard_and_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            state = SupervisorState(Path(td) / "state.db")
            envelope = {"body_digest": "a" * 64, "body": {"node_id": "n", "generation": 5}}
            state.stage(envelope, envelope["body"])
            state.commit_activation(expected_digest="a" * 64, nonce="durable-nonce-0001", grant_digest="b" * 64)
            reopened = SupervisorState(Path(td) / "state.db")
            self.assertEqual(reopened.status()["slots"]["ACTIVE"]["generation"], 5)
            self.assertEqual(len(reopened.verify_history()), 2)
            lower = {"body_digest": "c" * 64, "body": {"node_id": "n", "generation": 4}}
            with self.assertRaises(ManifestError):
                reopened.stage(lower, lower["body"])


if __name__ == "__main__":
    unittest.main()
