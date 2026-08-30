from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .v31 import AuditChain, SupervisorState, capability_registry_digest, verify_manifest


def _load_keys(path: Path) -> dict[str, Ed25519PublicKey]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("key file must be a key_id -> raw_public_key_b64 object")
    return {
        key_id: Ed25519PublicKey.from_public_bytes(base64.b64decode(value, validate=True))
        for key_id, value in raw.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="synergy-meta-os")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify-manifest")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("--keys", type=Path, required=True)

    status = sub.add_parser("status")
    status.add_argument("--root", type=Path, required=True)

    evidence = sub.add_parser("verify-evidence")
    evidence.add_argument("--root", type=Path, required=True)

    sub.add_parser("capability-registry-digest")
    args = parser.parse_args(argv)

    if args.command == "verify-manifest":
        envelope = json.loads(args.manifest.read_text(encoding="utf-8"))
        keys = _load_keys(args.keys)
        body = verify_manifest(envelope, lambda key_id: keys[key_id])
        print(json.dumps({"status": "ADMITTED", "node_id": body["node_id"], "generation": body["generation"], "execution_authority": "NONE"}, sort_keys=True))
        return 0
    if args.command == "capability-registry-digest":
        print(capability_registry_digest())
        return 0

    state = SupervisorState(args.root / "state" / "supervisor.db")
    if args.command == "status":
        print(json.dumps(state.status(), indent=2, sort_keys=True))
        return 0
    audit = AuditChain(args.root / "state" / "audit.jsonl")
    result = {"state_history_entries": len(state.verify_history()), "audit_records": len(audit.verify())}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
