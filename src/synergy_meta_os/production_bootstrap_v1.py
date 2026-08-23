from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_DIGEST = "605c6c953e998efb9585a88c1c8f1a022d7160e3448139c2b80a33e6b6cbabd3"
LAB_ROOTS = {
    "36a9092977e360b56fd7d1e21b4504f1215ed741df6f492b3ed37b79649573bb",
    "74797e02e0bb32722bbfffb76af42bb00d495fb3a5c0ea4a5b48a4e1d4275879",
    "8e1b05dca7e349d57e1908dca717d2c1d451ca79adde5cfe539e9e46f83d052b",
    "011c3ce24cfd33dc99fbdea0ea2f5dcd344deefd927f57c1b9c1fa3e3eaa3833",
}
REQUIRED_INPUT_KEYS = (
    "production_host_profile_digest",
    "production_supervisor_config_digest",
    "fresh_artifact_verification_digest",
    "fresh_health_transport_roundtrip_digest",
    "production_deployment_evidence_digest",
    "production_deployment_result_digest",
    "governance_promotion_digest",
)


class ProductionBootstrapError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def verify_contract(value: dict[str, Any]) -> str:
    if not isinstance(value, dict):
        raise ProductionBootstrapError("contract must be object")
    payload = dict(value)
    claimed = payload.pop("bootstrap_contract_digest", None)
    if claimed != EXPECTED_DIGEST:
        raise ProductionBootstrapError("bootstrap contract digest mismatch")
    actual = hashlib.sha256(_canonical(payload)).hexdigest()
    if actual != EXPECTED_DIGEST:
        raise ProductionBootstrapError("canonical payload mismatch")
    if payload.get("preproduction_release_digest") != "717b473fc67fbbdef89385d04b260ae2c8a8e85c75365ba8627785e1c8c271c7":
        raise ProductionBootstrapError("preproduction root substitution")
    if payload.get("deployment_reference_digest") != "19375c02a286a4c14e704ad0496d1c6084ddb00e7c4bcf3506a304a6b0946b70":
        raise ProductionBootstrapError("deployment reference substitution")
    if payload.get("production_transition_gate_digest") != "fd3f97c1422376ae507e7ec0ab1dcff529cba4ad9b5f6b1e9b7b62ef43d75b8c":
        raise ProductionBootstrapError("production gate substitution")
    if payload.get("nexus_network_access") != "NONE":
        raise ProductionBootstrapError("NEXUS network escalation")
    if payload.get("auto_start") is not False or payload.get("current_running") is not False:
        raise ProductionBootstrapError("invented running/auto-start state")
    for field in (
        "financial_authority",
        "payment_authority",
        "accounting_authority",
        "blockchain_submission_authority",
        "node_execution_authority",
    ):
        if payload.get(field) != "NONE":
            raise ProductionBootstrapError(f"authority escalation: {field}")
    return actual


def assess_production_inputs(contract: dict[str, Any], supplied: dict[str, str | None] | None = None) -> dict[str, Any]:
    verify_contract(contract)
    supplied = dict(supplied or {})
    declared = contract["required_inputs"]
    if set(declared) != set(REQUIRED_INPUT_KEYS):
        raise ProductionBootstrapError("required input shape mismatch")
    values = {key: supplied.get(key, declared[key]) for key in REQUIRED_INPUT_KEYS}
    missing = [key for key, value in values.items() if not value]
    reused = [key for key, value in values.items() if value in LAB_ROOTS]
    if reused:
        raise ProductionBootstrapError("LAB evidence reuse forbidden: " + ",".join(sorted(reused)))
    if missing:
        return {
            "status": "BLOCKED_MISSING_FRESH_PRODUCTION_INPUTS",
            "startup_allowed": False,
            "missing": missing,
            "current_running": False,
            "governance_status": "NOT_AUTHORIZED",
            "execution_authority": "NONE",
        }
    return {
        "status": "READY_FOR_GOVERNANCE_REVIEW_NOT_LAUNCHED",
        "startup_allowed": False,
        "missing": [],
        "current_running": False,
        "governance_status": "REVIEW_REQUIRED",
        "execution_authority": "NONE",
    }


def load_default_contract(root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[2]
    return json.loads((root / "production" / "autopilot_v5_ai_node_production_bootstrap_contract_v1.json").read_text(encoding="utf-8"))
