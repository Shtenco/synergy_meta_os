from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BOOTSTRAP_V4 = "39d262d4d6b28ceba3f6ffacadebd79d023e214ba63db6dbef6f5a3ad15547c6"
RC4 = "a7239ebf88b07f41b390120e3b3e23448e28548b3b9d981eb80a1fc014325803"
REGISTRY_V3 = "af24fe8c4b3ddfd8832f7e5ac6d92b2d4d69761cb9ab869407cd4d085e475526"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def verify(value):
    if not isinstance(value, dict):
        raise ValueError("HostProfile must be an object")
    payload = dict(value)
    claimed = payload.pop("host_profile_digest", None)
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("HostProfile digest missing")
    actual = hashlib.sha256(canonical(payload)).hexdigest()
    if actual != claimed:
        raise ValueError("HostProfile self-digest mismatch")
    checks = {
        "schema": "synergy.meta-os-production-host-profile/v1",
        "node_id": "synergy-autopilot-v5-ai-node",
        "production_bootstrap_v4_digest": BOOTSTRAP_V4,
        "preproduction_release_v4_digest": RC4,
        "federation_registry_v3_digest": REGISTRY_V3,
        "collector_scope": "FACT_COLLECTION_ONLY_NO_PROCESS_START_NO_AUTHORITY_GRANT",
        "operator_persistence_attestation": "PRESENT_EXPLICIT_NOT_INDEPENDENTLY_PROVEN_BY_COLLECTOR",
        "hostname_storage_policy": "RAW_HOSTNAME_NOT_RECORDED",
        "network_address_policy": "NO_NETWORK_ADDRESS_COLLECTED_IN_HOST_PROFILE_V1",
        "secrets_policy": "NO_SECRETS_TOKENS_KEYS_OR_CREDENTIALS_COLLECTED",
        "nexus_network_access": "NONE",
    }
    for key, expected in checks.items():
        if payload.get(key) != expected:
            raise ValueError(f"HostProfile invariant mismatch: {key}")
    if payload.get("current_running") is not False or payload.get("auto_start") is not False:
        raise ValueError("HostProfile cannot claim running or auto-start")
    for key in (
        "financial_authority", "payment_authority", "accounting_authority",
        "host_execution_authority", "blockchain_submission_authority", "node_execution_authority",
    ):
        if payload.get(key) != "NONE":
            raise ValueError(f"authority escalation: {key}")
    machine = payload.get("stable_machine_id_sha256")
    if not isinstance(machine, str) or len(machine) != 64 or any(c not in "0123456789abcdef" for c in machine):
        raise ValueError("invalid stable machine-id hash")
    root = payload.get("production_root")
    if not isinstance(root, dict) or not str(root.get("absolute_path", "")).startswith("/"):
        raise ValueError("invalid production root facts")
    return claimed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("profile")
    a = p.parse_args()
    value = json.loads(Path(a.profile).read_text(encoding="utf-8"))
    print(json.dumps({"status": "PASS", "host_profile_digest": verify(value), "execution_authority": "NONE"}, sort_keys=True))


if __name__ == "__main__":
    main()
