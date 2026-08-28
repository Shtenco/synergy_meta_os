from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "economic_testnet_external_deployment_gate_v1",
    ROOT / "src" / "synergy_meta_os" / "economic_testnet_external_deployment_gate_v1.py",
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def gate():
    return json.loads((ROOT / "production" / "economic_testnet_external_deployment_gate_v1.json").read_text(encoding="utf-8"))


def node(i):
    return {
        "node_id": f"economic-node-{i}",
        "host_scope": "PERSISTENT_EXTERNAL_HOST",
        "network_scope": "NON_LOOPBACK_CROSS_HOST",
        "host_profile_digest": f"{100+i:064x}",
        "supervisor_config_digest": f"{200+i:064x}",
        "host_fingerprint_digest": f"{300+i:064x}",
        "artifact_verification_digest": f"{400+i:064x}",
        "persistent_storage_evidence_digest": f"{500+i:064x}",
        "restart_recovery_evidence_digest": f"{600+i:064x}",
        "deployment_evidence_digest": f"{700+i:064x}",
        "deployment_result_digest": f"{800+i:064x}",
        "transport_endpoint_digest": f"{900+i:064x}",
    }


def rehash(value):
    body = dict(value); body.pop("digest", None)
    value["digest"] = MOD.canonical_digest(body)
    return value


def test_canonical_gate_is_blocked_with_null_hosts():
    verified = MOD.verify_gate_contract_v1(gate())
    assert verified["digest"] == MOD.EXPECTED_GATE_DIGEST
    assessment = MOD.assess_external_deployment_candidate_v1(verified, nodes=None, cross_host_checkpoint_transcript_digest=None)
    assert assessment["status"] == "BLOCKED_MISSING_EXTERNAL_HOST_INPUTS"
    assert assessment["startup_allowed"] is False
    assert assessment["external_testnet_claim"] is False


def test_three_distinct_structural_host_candidates_only_reach_verification_ready():
    assessment = MOD.assess_external_deployment_candidate_v1(
        gate(), nodes=[node(1), node(2), node(3)], cross_host_checkpoint_transcript_digest=f"{999:064x}"
    )
    assert assessment["status"] == "READY_FOR_EXTERNAL_DEPLOYMENT_EVIDENCE_VERIFICATION_NOT_EXECUTED"
    assert assessment["node_count"] == 3
    assert assessment["startup_allowed"] is False
    assert assessment["external_testnet_claim"] is False
    assert assessment["consensus_claim"] == "NONE"


def test_duplicate_host_fingerprint_is_rejected():
    nodes = [node(1), node(2), node(3)]
    nodes[2]["host_fingerprint_digest"] = nodes[0]["host_fingerprint_digest"]
    with pytest.raises(MOD.EconomicTestnetExternalDeploymentGateV1Error, match="fingerprints"):
        MOD.assess_external_deployment_candidate_v1(gate(), nodes=nodes, cross_host_checkpoint_transcript_digest=f"{999:064x}")


def test_loopback_scope_is_rejected():
    nodes = [node(1), node(2), node(3)]
    nodes[0]["network_scope"] = "LOOPBACK"
    with pytest.raises(MOD.EconomicTestnetExternalDeploymentGateV1Error, match="network scope"):
        MOD.assess_external_deployment_candidate_v1(gate(), nodes=nodes, cross_host_checkpoint_transcript_digest=f"{999:064x}")


def test_wrong_node_count_is_rejected():
    with pytest.raises(MOD.EconomicTestnetExternalDeploymentGateV1Error, match="exactly three"):
        MOD.assess_external_deployment_candidate_v1(gate(), nodes=[node(1), node(2)], cross_host_checkpoint_transcript_digest=f"{999:064x}")


def test_fresh_hash_cannot_populate_canonical_gate_or_claim_testnet():
    item = copy.deepcopy(gate())
    item["node_inputs"] = [node(1), node(2), node(3)]
    item["gate_status"] = "EXTERNAL_TESTNET_RUNNING"
    item["startup_allowed"] = True
    item["external_testnet_claim"] = True
    rehash(item)
    with pytest.raises(MOD.EconomicTestnetExternalDeploymentGateV1Error):
        MOD.verify_gate_contract_v1(item)


def test_fresh_hash_cannot_weaken_required_evidence_fields():
    item = copy.deepcopy(gate())
    item["required_node_root_fields"] = ["host_profile_digest", "deployment_result_digest"]
    rehash(item)
    with pytest.raises(MOD.EconomicTestnetExternalDeploymentGateV1Error, match="gate digest mismatch"):
        MOD.verify_gate_contract_v1(item)


def test_fresh_hash_cannot_change_network_requirement():
    item = copy.deepcopy(gate())
    item["network_requirement"] = "ANY_THREE_PROCESSES"
    rehash(item)
    with pytest.raises(MOD.EconomicTestnetExternalDeploymentGateV1Error, match="gate digest mismatch"):
        MOD.verify_gate_contract_v1(item)
