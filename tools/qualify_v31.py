#!/usr/bin/env python3
"""Repeatable qualification for the v31 signed durable supervisor.

The runner uses only temporary state.  It never writes private keys or copies
repository credentials into release evidence.
"""

from __future__ import annotations

import argparse
import base64
import json
import platform
import sys
import tempfile
import time
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
    make_activation_grant,
    make_manifest,
    sha256_hex,
    sign_activation_grant,
    sign_manifest,
    verify_manifest,
)


HOST_COMMIT = "81fa56ef8d7e33ceeaa9a829416c9c34f5aa1536"
HOST_RELEASE = "f2aa3424662a8e1b025fb253fb73da7897b50a6b3bd9c327379b580e726ee623"
GOOD_SERVICE = (
    b"#!/usr/bin/python3\n"
    b"import signal,time\n"
    b"signal.signal(signal.SIGTERM,lambda *_:exit(0))\n"
    b"while True: time.sleep(1)\n"
)
BAD_SERVICE = b"#!/bin/sh\nexit 23\n"


def utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def service(service_id: str, digest: str) -> dict[str, object]:
    return {
        "service_id": service_id,
        "kind": "DIAGNOSTICS",
        "repository": "Shtenco/synergy_meta_os",
        "artifact_digest": digest,
        "argv": ["$ARTIFACT"],
        "capabilities": ["observability.emit"],
        "depends_on": [],
        "desired_state": "ENABLED",
        "limits": {
            "memory_mib": 128,
            "cpu_seconds": 30,
            "open_files": 32,
            "processes": 4,
            "file_mib": 4,
        },
        "health": {"kind": "process_alive", "grace_ms": 20},
        "key_refs": [],
    }


def manifest(
    private_key: Ed25519PrivateKey,
    now: datetime,
    digest: str,
    generation: int,
) -> dict[str, object]:
    body = make_manifest(
        node_id="qualification-node",
        generation=generation,
        issued_at=utc(now - timedelta(seconds=1)),
        expires_at=utc(now + timedelta(hours=1)),
        profile="EDGE_CLIENT",
        development=True,
        attestation_level="DEVELOPMENT",
        attestation_evidence_digest=None,
        host_ref="turbo-v30-unified-hhdm-metastorage-rc",
        host_commit_sha=HOST_COMMIT,
        host_release_sha256=HOST_RELEASE,
        services=[service("diagnostics", digest)],
    )
    return sign_manifest(body, private_key, key_id="manifest-qualification", now=now)


def grant(
    private_key: Ed25519PrivateKey,
    now: datetime,
    envelope: dict[str, object],
    nonce: str,
) -> dict[str, object]:
    body = envelope["body"]
    assert isinstance(body, dict)
    grant_body = make_activation_grant(
        node_id=str(body["node_id"]),
        manifest_body_digest=str(envelope["body_digest"]),
        manifest_generation=int(body["generation"]),
        allowed_services=["diagnostics"],
        issued_at=utc(now - timedelta(seconds=1)),
        expires_at=utc(now + timedelta(hours=1)),
        nonce=nonce,
    )
    return sign_activation_grant(grant_body, private_key, key_id="governance-qualification", now=now)


def timed(checks: dict[str, object], name: str, action: object) -> object:
    started = time.monotonic_ns()
    result = action()  # type: ignore[operator]
    elapsed_ms = (time.monotonic_ns() - started) // 1_000_000
    checks[name] = {"status": "PASS", "elapsed_ms": elapsed_ms, "result": result}
    return result


def run(output: Path) -> dict[str, object]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    checks: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="synergy-v31-qualification-") as temp_name:
        root = Path(temp_name)
        manifest_key = Ed25519PrivateKey.generate()
        governance_key = Ed25519PrivateKey.generate()
        manifest_public = manifest_key.public_key()
        governance_public = governance_key.public_key()

        base_store = ArtifactStore(root / "base-cas")
        base_digest = base_store.put(GOOD_SERVICE)
        envelope = manifest(manifest_key, now, base_digest, 1)
        verify_manifest(envelope, lambda _: manifest_public, now=now)

        def signature_mutations() -> dict[str, int]:
            rejected = 0
            signature = envelope["signature"]
            assert isinstance(signature, dict)
            original = base64.b64decode(str(signature["value_b64"]), validate=True)
            for index in range(10_000):
                changed = bytearray(original)
                changed[index % len(changed)] ^= 1 << (index % 8)
                candidate = dict(envelope)
                candidate["signature"] = dict(signature)
                candidate["signature"]["value_b64"] = base64.b64encode(changed).decode("ascii")  # type: ignore[index]
                try:
                    verify_manifest(candidate, lambda _: manifest_public, now=now)
                except ManifestError:
                    rejected += 1
            if rejected != 10_000:
                raise AssertionError(f"accepted {10_000 - rejected} modified signatures")
            return {"mutations": 10_000, "rejected": rejected, "accepted": 0}

        timed(checks, "ed25519_signature_mutation", signature_mutations)

        def cas_roundtrips() -> dict[str, int]:
            store = ArtifactStore(root / "qualification-cas")
            unique: set[str] = set()
            for index in range(2_048):
                payload = (f"v31-artifact-{index % 257}:" + "x" * (index % 211)).encode("ascii")
                digest = store.put(payload)
                if store.get_verified(digest) != payload:
                    raise AssertionError("CAS roundtrip mismatch")
                unique.add(digest)
            return {"operations": 2_048, "unique_objects": len(unique), "verified": 2_048}

        timed(checks, "immutable_cas_roundtrip", cas_roundtrips)

        def durable_cycles() -> dict[str, int]:
            state_path = root / "durable" / "state.db"
            state = SupervisorState(state_path)
            for generation in range(1, 1_001):
                digest = sha256_hex(f"generation:{generation}".encode("ascii"))
                candidate = {
                    "body_digest": digest,
                    "body": {"node_id": "durable-node", "generation": generation},
                }
                state.stage(candidate, candidate["body"])
                state.commit_activation(
                    expected_digest=digest,
                    nonce=f"durable-nonce-{generation:08d}",
                    grant_digest=sha256_hex(f"grant:{generation}".encode("ascii")),
                )
            reopened = SupervisorState(state_path)
            status = reopened.status()
            active = status["slots"]["ACTIVE"]
            if active["generation"] != 1_000 or status["used_nonces"] != 1_000:
                raise AssertionError("durable state did not survive reopen")
            history = reopened.verify_history()
            if len(history) != 2_000:
                raise AssertionError("durable history length mismatch")
            lower = {
                "body_digest": "f" * 64,
                "body": {"node_id": "durable-node", "generation": 999},
            }
            try:
                reopened.stage(lower, lower["body"])
            except ManifestError:
                rollback_rejected = 1
            else:
                rollback_rejected = 0
            if rollback_rejected != 1:
                raise AssertionError("generation rollback was accepted")
            return {
                "activation_cycles": 1_000,
                "history_entries": len(history),
                "used_nonces": int(status["used_nonces"]),
                "rollback_rejected": rollback_rejected,
            }

        timed(checks, "sqlite_full_durable_state", durable_cycles)

        def audit_records() -> dict[str, int]:
            audit = AuditChain(root / "audit" / "audit.jsonl")
            for index in range(512):
                audit.append("QUALIFICATION_EVENT", index=index, execution_authority="NONE")
            records = audit.verify()
            if len(records) != 512:
                raise AssertionError("audit chain length mismatch")
            return {"appended": 512, "verified": len(records)}

        timed(checks, "fsync_audit_hash_chain", audit_records)

        def failed_upgrade_cycles() -> dict[str, int]:
            supervisor = NodeSupervisor(
                root=root / "supervisor",
                manifest_key_resolver=lambda _: manifest_public,
                governance_key_resolver=lambda _: governance_public,
            )
            try:
                good_digest = supervisor.artifacts.put(GOOD_SERVICE)
                bad_digest = supervisor.artifacts.put(BAD_SERVICE)
                active = manifest(manifest_key, now, good_digest, 1)
                supervisor.stage(active, now=now)
                supervisor.activate(grant(governance_key, now, active, "qualification-good-0001"), now=now)
                original_pid = supervisor.running["diagnostics"].process.pid
                rejected = 0
                for generation in range(2, 52):
                    candidate = manifest(manifest_key, now, bad_digest, generation)
                    supervisor.stage(candidate, now=now)
                    try:
                        supervisor.activate(
                            grant(governance_key, now, candidate, f"qualification-bad-{generation:08d}"),
                            now=now,
                        )
                    except ActivationError:
                        rejected += 1
                    if supervisor.running["diagnostics"].process.pid != original_pid:
                        raise AssertionError("failed upgrade replaced the active service")
                    if supervisor.running["diagnostics"].process.poll() is not None:
                        raise AssertionError("active service died during failed upgrade")
                    if supervisor.state.load_slot("ACTIVE")["body_digest"] != active["body_digest"]:  # type: ignore[index]
                        raise AssertionError("failed upgrade changed the active manifest")
                if rejected != 50:
                    raise AssertionError("a failing upgrade was accepted")
                if len(supervisor.audit.verify()) != 103:
                    raise AssertionError("supervisor audit record count mismatch")
                return {
                    "failed_upgrades": 50,
                    "rejected": rejected,
                    "old_process_preserved": 50,
                    "audit_records": 103,
                }
            finally:
                supervisor.stop_all()

        timed(checks, "transactional_failed_upgrade", failed_upgrade_cycles)

    result: dict[str, object] = {
        "schema": "synergy.v31-qualification/v1",
        "release": "v31-signed-durable-supervisor-rc1",
        "status": "PASS",
        "generated_at": utc(datetime.now(timezone.utc)),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "checks": checks,
        "private_keys_persisted": False,
        "production": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "SYNERGY_META_OS_V31_QUALIFICATION_PASS "
        "signature_mutations=10000 cas=2048 durable=1000 audit=512 failed_upgrades=50"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
