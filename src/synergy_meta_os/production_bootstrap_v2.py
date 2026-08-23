from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_DIGEST = "3e2f1eb8c34b3beba75157b88aedc13c354d4450b9c0ab611cd63bb51f4f9a8c"
REQUIRED_INPUT_KEYS = (
    "new_synergynet_location_evidence_v3_digest",
    "production_host_profile_digest",
    "production_supervisor_config_digest",
    "fresh_artifact_verification_digest",
    "fresh_health_transport_roundtrip_digest",
    "production_deployment_evidence_digest",
    "production_deployment_result_digest",
    "governance_promotion_digest",
)
FORBIDDEN_REUSE = {
    "c4102a8e668b79fc961a5f1767154154f4a600d320442770d74c7a006a5cee08",
    "36a9092977e360b56fd7d1e21b4504f1215ed741df6f492b3ed37b79649573bb",
    "74797e02e0bb32722bbfffb76af42bb00d495fb3a5c0ea4a5b48a4e1d4275879",
    "8e1b05dca7e349d57e1908dca717d2c1d451ca79adde5cfe539e9e46f83d052b",
    "011c3ce24cfd33dc99fbdea0ea2f5dcd344deefd927f57c1b9c1fa3e3eaa3833",
}


class ProductionBootstrapV2Error(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def verify_contract(value: dict[str, Any]) -> str:
    if not isinstance(value, dict):
        raise ProductionBootstrapV2Error("contract must be object")
    payload = dict(value)
    claimed = payload.pop("bootstrap_contract_digest", None)
    actual = hashlib.sha256(canonical(payload)).hexdigest()
    if claimed != EXPECTED_DIGEST or actual != EXPECTED_DIGEST:
        raise ProductionBootstrapV2Error("bootstrap v2 digest mismatch")
    fixed = {
        "previous_bootstrap_contract_digest": "605c6c953e998efb9585a88c1c8f1a022d7160e3448139c2b80a33e6b6cbabd3",
        "preproduction_release_v2_digest": "03914c9199b25227026d02a2a2b2d0d8a11e958982c76865701729fff55710ba",
        "deployment_reference_digest": "19375c02a286a4c14e704ad0496d1c6084ddb00e7c4bcf3506a304a6b0946b70",
        "production_transition_gate_digest": "fd3f97c1422376ae507e7ec0ab1dcff529cba4ad9b5f6b1e9b7b62ef43d75b8c",
        "synergynet_locator_negative_evidence_digest": "2529d725e426c5028daab7346d1c704d643ffd209d35ceace7f7330203a6353f",
        "launch_status": "BLOCKED_MISSING_NEW_LOCATOR_AND_FRESH_PRODUCTION_INPUTS",
        "nexus_network_access": "NONE",
        "startup_allowed": False,
        "current_running": False,
        "auto_start": False,
    }
    for key, expected in fixed.items():
        if payload.get(key) != expected:
            raise ProductionBootstrapV2Error(f"fixed field mismatch: {key}")
    for key in ("financial_authority", "payment_authority", "accounting_authority", "blockchain_submission_authority", "node_execution_authority"):
        if payload.get(key) != "NONE":
            raise ProductionBootstrapV2Error(f"authority escalation: {key}")
    return actual


def assess_inputs(contract: dict[str, Any], supplied: dict[str, str | None] | None = None) -> dict[str, Any]:
    verify_contract(contract)
    supplied = dict(supplied or {})
    if set(supplied) - set(REQUIRED_INPUT_KEYS):
        raise ProductionBootstrapV2Error("unknown production input")
    declared = contract["required_inputs"]
    if set(declared) != set(REQUIRED_INPUT_KEYS):
        raise ProductionBootstrapV2Error("required input shape mismatch")
    values = {key: supplied.get(key, declared[key]) for key in REQUIRED_INPUT_KEYS}
    missing = [key for key, value in values.items() if value is None]
    malformed = [key for key, value in values.items() if value is not None and not is_digest(value)]
    if malformed:
        raise ProductionBootstrapV2Error("malformed digest: " + ",".join(malformed))
    reused = [key for key, value in values.items() if value in FORBIDDEN_REUSE]
    if reused:
        raise ProductionBootstrapV2Error("historical/LAB evidence reuse forbidden: " + ",".join(reused))
    present = [value for value in values.values() if value is not None]
    if len(present) != len(set(present)):
        raise ProductionBootstrapV2Error("production roots must be distinct")
    if missing:
        return {"status": "BLOCKED_MISSING_NEW_LOCATOR_AND_FRESH_PRODUCTION_INPUTS", "startup_allowed": False, "missing": missing, "current_running": False, "execution_authority": "NONE"}
    return {"status": "READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED", "startup_allowed": False, "missing": [], "current_running": False, "execution_authority": "NONE"}


def load_default_contract(root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[2]
    return json.loads((root / "production" / "autopilot_v5_ai_node_production_bootstrap_contract_v2.json").read_text(encoding="utf-8"))
