from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "synergy.economic-testnet-external-deployment-gate/v1"
GENESIS = "cfba3627eb65d933ed1dec416bfe1c28ecf586312028efc7e629859f315678b2"
TESTNET_SOURCE_COMMIT = "72a7853fba49d20c208bd2d9776d6c107648b882"
LOCAL_PERSISTENCE_EVIDENCE = "7c533e6ebb3b3177ef9191d1951c930ddd9d6f49541b0fa3982924f2dce86680"
META_OS_BOOTSTRAP_V5 = "6ccecccc03189c6de934abf146cab87bb25b022551ba8d453cfefd4f5a3cdffd"
HEX = frozenset("0123456789abcdef")
REQUIRED_NODE_COUNT = 3
NODE_ROOT_FIELDS = (
    "host_profile_digest",
    "supervisor_config_digest",
    "host_fingerprint_digest",
    "artifact_verification_digest",
    "persistent_storage_evidence_digest",
    "restart_recovery_evidence_digest",
    "deployment_evidence_digest",
    "deployment_result_digest",
    "transport_endpoint_digest",
)

class EconomicTestnetExternalDeploymentGateV1Error(ValueError):
    pass


def canonical_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EconomicTestnetExternalDeploymentGateV1Error(f"{name} required")
    return value.strip()


def _hex(value: Any, name: str) -> str:
    result = _text(value, name).lower()
    if len(result) != 64 or any(ch not in HEX for ch in result):
        raise EconomicTestnetExternalDeploymentGateV1Error(f"{name} must be hex64")
    return result


def verify_gate_contract_v1(contract: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, Mapping) or contract.get("schema") != SCHEMA:
        raise EconomicTestnetExternalDeploymentGateV1Error("gate schema mismatch")
    item = dict(contract)
    supplied = item.pop("digest", None)
    if supplied != canonical_digest(item):
        raise EconomicTestnetExternalDeploymentGateV1Error("gate digest mismatch")
    if item.get("economic_testnet_genesis_digest") != GENESIS:
        raise EconomicTestnetExternalDeploymentGateV1Error("genesis drift")
    if item.get("economic_testnet_source_commit") != TESTNET_SOURCE_COMMIT:
        raise EconomicTestnetExternalDeploymentGateV1Error("testnet source drift")
    if item.get("local_persistence_execution_evidence_digest") != LOCAL_PERSISTENCE_EVIDENCE:
        raise EconomicTestnetExternalDeploymentGateV1Error("local persistence evidence drift")
    if item.get("meta_os_production_bootstrap_v5_digest") != META_OS_BOOTSTRAP_V5:
        raise EconomicTestnetExternalDeploymentGateV1Error("Meta-OS bootstrap context drift")
    if item.get("required_node_count") != REQUIRED_NODE_COUNT:
        raise EconomicTestnetExternalDeploymentGateV1Error("external testnet requires exactly three nodes")
    if item.get("node_inputs") != [None, None, None]:
        raise EconomicTestnetExternalDeploymentGateV1Error("canonical gate must not fabricate hosts")
    if item.get("gate_status") != "BLOCKED_AWAITING_THREE_REAL_PERSISTENT_EXTERNAL_HOSTS":
        raise EconomicTestnetExternalDeploymentGateV1Error("canonical gate status drift")
    if item.get("startup_allowed") is not False or item.get("external_testnet_claim") is not False:
        raise EconomicTestnetExternalDeploymentGateV1Error("canonical gate cannot start/claim external testnet")
    if item.get("consensus_claim") != "NONE" or item.get("finality_claim") != "NONE":
        raise EconomicTestnetExternalDeploymentGateV1Error("gate cannot claim consensus/finality")
    for field in ("signing_authority", "blockchain_submission_authority", "financial_authority", "payment_authority", "accounting_authority", "execution_authority"):
        if item.get(field) != "NONE":
            raise EconomicTestnetExternalDeploymentGateV1Error("gate authority escalation")
    item["digest"] = supplied
    return item


def _verify_node_candidate(raw: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise EconomicTestnetExternalDeploymentGateV1Error(f"node {ordinal} must be object")
    allowed = {"node_id", "host_scope", "network_scope", *NODE_ROOT_FIELDS}
    if set(raw) != allowed:
        raise EconomicTestnetExternalDeploymentGateV1Error(f"node {ordinal} fields mismatch")
    result = dict(raw)
    result["node_id"] = _text(result.get("node_id"), f"node {ordinal}.node_id")
    if result.get("host_scope") != "PERSISTENT_EXTERNAL_HOST":
        raise EconomicTestnetExternalDeploymentGateV1Error(f"node {ordinal} is not persistent external host scope")
    if result.get("network_scope") != "NON_LOOPBACK_CROSS_HOST":
        raise EconomicTestnetExternalDeploymentGateV1Error(f"node {ordinal} network scope invalid")
    for field in NODE_ROOT_FIELDS:
        result[field] = _hex(result.get(field), f"node {ordinal}.{field}")
    return result


def assess_external_deployment_candidate_v1(
    contract: Mapping[str, Any],
    *,
    nodes: Sequence[Mapping[str, Any]] | None,
    cross_host_checkpoint_transcript_digest: str | None,
) -> dict[str, Any]:
    gate = verify_gate_contract_v1(contract)
    if nodes is None or cross_host_checkpoint_transcript_digest is None:
        return {
            "status": "BLOCKED_MISSING_EXTERNAL_HOST_INPUTS",
            "blockers": ["THREE_PERSISTENT_EXTERNAL_HOST_INPUTS_REQUIRED", "CROSS_HOST_CHECKPOINT_TRANSCRIPT_REQUIRED"],
            "startup_allowed": False,
            "external_testnet_claim": False,
            "consensus_claim": "NONE",
            "execution_authority": "NONE",
            "gate_digest": gate["digest"],
        }
    if len(nodes) != REQUIRED_NODE_COUNT:
        raise EconomicTestnetExternalDeploymentGateV1Error("candidate requires exactly three external nodes")
    verified = [_verify_node_candidate(raw, i + 1) for i, raw in enumerate(nodes)]
    node_ids = [node["node_id"] for node in verified]
    fingerprints = [node["host_fingerprint_digest"] for node in verified]
    deployments = [node["deployment_evidence_digest"] for node in verified]
    results = [node["deployment_result_digest"] for node in verified]
    if len(set(node_ids)) != REQUIRED_NODE_COUNT:
        raise EconomicTestnetExternalDeploymentGateV1Error("node ids must be unique")
    if len(set(fingerprints)) != REQUIRED_NODE_COUNT:
        raise EconomicTestnetExternalDeploymentGateV1Error("host fingerprints must prove three distinct candidates")
    if len(set(deployments)) != REQUIRED_NODE_COUNT or len(set(results)) != REQUIRED_NODE_COUNT:
        raise EconomicTestnetExternalDeploymentGateV1Error("deployment evidence/results must be unique per host")
    transcript = _hex(cross_host_checkpoint_transcript_digest, "cross_host_checkpoint_transcript_digest")
    return {
        "status": "READY_FOR_EXTERNAL_DEPLOYMENT_EVIDENCE_VERIFICATION_NOT_EXECUTED",
        "blockers": ["INDEPENDENT_EXTERNAL_HOST_EVIDENCE_VERIFICATION_NOT_EXECUTED", "GOVERNANCE_PROMOTION_NOT_PERFORMED"],
        "node_count": REQUIRED_NODE_COUNT,
        "node_ids": node_ids,
        "host_fingerprint_digests": fingerprints,
        "cross_host_checkpoint_transcript_digest": transcript,
        "startup_allowed": False,
        "external_testnet_claim": False,
        "consensus_claim": "NONE",
        "finality_claim": "NONE",
        "signing_authority": "NONE",
        "blockchain_submission_authority": "NONE",
        "financial_authority": "NONE",
        "payment_authority": "NONE",
        "accounting_authority": "NONE",
        "execution_authority": "NONE",
        "gate_digest": gate["digest"],
    }
