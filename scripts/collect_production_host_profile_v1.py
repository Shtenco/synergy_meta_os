from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import platform
import shutil
import socket
import sys
from pathlib import Path

BOOTSTRAP_V4 = "39d262d4d6b28ceba3f6ffacadebd79d023e214ba63db6dbef6f5a3ad15547c6"
RC4 = "a7239ebf88b07f41b390120e3b3e23448e28548b3b9d981eb80a1fc014325803"
REGISTRY_V3 = "af24fe8c4b3ddfd8832f7e5ac6d92b2d4d69761cb9ab869407cd4d085e475526"
ATTESTATION = "I_CONFIRM_THIS_IS_THE_INTENDED_PERSISTENT_SYNERGY_PRODUCTION_HOST"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def read_machine_id_hash() -> str:
    for path in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        if path.is_file():
            raw = path.read_text(encoding="utf-8", errors="strict").strip()
            if raw:
                return sha256_text(raw)
    raise SystemExit("FAIL_CLOSED: stable machine-id is unavailable; production HostProfile not emitted")


def main() -> int:
    p = argparse.ArgumentParser(description="Collect a fact-only SYNERGY production HostProfile; never starts processes")
    p.add_argument("--attestation", required=True, help="Explicit operator acknowledgement; exact phrase required")
    p.add_argument("--production-root", required=True, help="Absolute persistent deployment root already provisioned by operator")
    p.add_argument("--output", required=True, help="Output JSON path; must not already exist")
    p.add_argument("--host-role", default="PRIMARY_SYNERGY_AI_NODE")
    args = p.parse_args()

    if args.attestation != ATTESTATION:
        raise SystemExit("FAIL_CLOSED: persistent production-host attestation missing or incorrect")
    root = Path(args.production_root)
    if not root.is_absolute() or not root.exists() or not root.is_dir():
        raise SystemExit("FAIL_CLOSED: production root must be an existing absolute directory")
    out = Path(args.output)
    if out.exists():
        raise SystemExit("FAIL_CLOSED: refusing to overwrite existing HostProfile evidence")
    if platform.system() != "Linux":
        raise SystemExit("FAIL_CLOSED: production HostProfile v1 currently supports Linux only")

    stat = root.stat()
    payload = {
        "schema": "synergy.meta-os-production-host-profile/v1",
        "profile_id": "SYNERGY_AUTOPILOT_V5_AI_NODE_PRODUCTION_HOST_PROFILE_V1",
        "node_id": "synergy-autopilot-v5-ai-node",
        "production_bootstrap_v4_digest": BOOTSTRAP_V4,
        "preproduction_release_v4_digest": RC4,
        "federation_registry_v3_digest": REGISTRY_V3,
        "collector_scope": "FACT_COLLECTION_ONLY_NO_PROCESS_START_NO_AUTHORITY_GRANT",
        "operator_persistence_attestation": "PRESENT_EXPLICIT_NOT_INDEPENDENTLY_PROVEN_BY_COLLECTOR",
        "host_role": args.host_role,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        },
        "stable_machine_id_sha256": read_machine_id_hash(),
        "production_root": {
            "absolute_path": str(root.resolve()),
            "filesystem_device_id": int(stat.st_dev),
            "owner_uid": int(stat.st_uid),
            "owner_gid": int(stat.st_gid),
        },
        "runtime_identity": {
            "effective_uid": os.geteuid(),
            "effective_gid": os.getegid(),
            "username": getpass.getuser(),
        },
        "capability_observations": {
            "systemctl_present": shutil.which("systemctl") is not None,
            "python_present": shutil.which("python3") is not None,
        },
        "hostname_storage_policy": "RAW_HOSTNAME_NOT_RECORDED",
        "network_address_policy": "NO_NETWORK_ADDRESS_COLLECTED_IN_HOST_PROFILE_V1",
        "secrets_policy": "NO_SECRETS_TOKENS_KEYS_OR_CREDENTIALS_COLLECTED",
        "nexus_network_access": "NONE",
        "current_running": False,
        "auto_start": False,
        "financial_authority": "NONE",
        "payment_authority": "NONE",
        "accounting_authority": "NONE",
        "host_execution_authority": "NONE",
        "blockchain_submission_authority": "NONE",
        "node_execution_authority": "NONE",
    }
    payload["host_profile_digest"] = hashlib.sha256(canonical(payload)).hexdigest()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "HOST_PROFILE_FACTS_COLLECTED_NOT_DEPLOYED",
        "host_profile_digest": payload["host_profile_digest"],
        "startup_performed": False,
        "current_running": False,
        "execution_authority": "NONE",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
