from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

EXPECTED_DIGEST = "6ccecccc03189c6de934abf146cab87bb25b022551ba8d453cfefd4f5a3cdffd"
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
PINNED = {
    "preproduction_rc5_digest": "0dd56320df6a1e18a7f77470b0609f55cb9c134ac67bbedeebdd3600e724124b",
    "deployment_reference_v2_digest": "87b9bb8158652dacc02832b465d94fddabfd31c9c6f5aa20bc9687b456bae879",
    "ai_blockchain_preproduction_commitment_v3_digest": "608b0ca91e905cb0345d345af9e1246489236a8e672a07fb60ea4cfb8691d397",
    "federation_registry_v3_digest": "af24fe8c4b3ddfd8832f7e5ac6d92b2d4d69761cb9ab869407cd4d085e475526",
    "meta_os_profile_v3_digest": "96ea31f50ff61b478390d682e88cca89c806e88dbaef1c4fc53b109724ca8222",
    "meta_os_admission_v3_digest": "b1c151d4d5095278006d338c65f3a56b4853c3b3aa70a429205bea84fc5770e8",
    "synergynet_location_evidence_v3_digest": "b1ca1c1f5849deac30a0aac14748c21b8a74a26776ba2134a448c9427a839220",
    "synergynet_transport_binding_v2_digest": "0c58185ea0af4a8abc7ce215c0b7ff077cea9357e831b9d197ec730a34ed6c7e",
}

class ProductionBootstrapV5Error(ValueError): pass

def canonical(v: Any) -> bytes:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def verify_contract(v: dict[str, Any]) -> str:
    if not isinstance(v, dict): raise ProductionBootstrapV5Error("contract must be object")
    p = dict(v); claimed = p.pop("bootstrap_contract_digest", None)
    actual = hashlib.sha256(canonical(p)).hexdigest()
    if claimed != EXPECTED_DIGEST or actual != EXPECTED_DIGEST: raise ProductionBootstrapV5Error("digest mismatch")
    for k, expected in PINNED.items():
        if p.get(k) != expected: raise ProductionBootstrapV5Error(f"pinned lineage mismatch: {k}")
    if p.get("current_running") is not False or p.get("auto_start") is not False or p.get("startup_allowed") is not False:
        raise ProductionBootstrapV5Error("invented startup/running state")
    if p.get("nexus_network_access") != "NONE": raise ProductionBootstrapV5Error("NEXUS network escalation")
    for k in ("financial_authority","payment_authority","accounting_authority","blockchain_submission_authority","node_execution_authority"):
        if p.get(k) != "NONE": raise ProductionBootstrapV5Error(f"authority escalation: {k}")
    return actual

def assess(contract: dict[str, Any], supplied: dict[str, str | None] | None = None) -> dict[str, Any]:
    verify_contract(contract)
    declared = contract["required_inputs"]
    if set(declared) != set(REQUIRED_INPUT_KEYS): raise ProductionBootstrapV5Error("required input shape mismatch")
    values = {k: (supplied or {}).get(k, declared[k]) for k in REQUIRED_INPUT_KEYS}
    present = [v for v in values.values() if v]
    if any(not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v) for v in present):
        raise ProductionBootstrapV5Error("malformed digest")
    if len(set(present)) != len(present): raise ProductionBootstrapV5Error("duplicate production roots")
    if any(v in LAB_ROOTS for v in present): raise ProductionBootstrapV5Error("LAB evidence reuse forbidden")
    missing = [k for k,v in values.items() if not v]
    if missing:
        return {"status":"BLOCKED_AWAITING_REAL_PERSISTENT_PRODUCTION_HOST_AND_FRESH_DEPLOYMENT_EVIDENCE","startup_allowed":False,"missing":missing,"current_running":False,"governance_status":"NOT_AUTHORIZED","execution_authority":"NONE"}
    return {"status":"READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED","startup_allowed":False,"missing":[],"current_running":False,"governance_status":"REVIEW_REQUIRED","execution_authority":"NONE"}

def load_default(root: Path | None = None):
    root = root or Path(__file__).resolve().parents[2]
    return json.loads((root/"production"/"autopilot_v5_ai_node_production_bootstrap_contract_v5.json").read_text(encoding="utf-8"))
