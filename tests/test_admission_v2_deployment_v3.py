from __future__ import annotations

import copy,json
from pathlib import Path
import pytest

from synergy_meta_os.admission_v2 import AdmissionV2Error,digest,verify_admission_v2
from synergy_meta_os.deployment_v3 import BLOCKERS,verify_artifact_registry_v3,verify_deployment_plan_v3

ROOT=Path(__file__).resolve().parents[1]
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))

def bundle():
    return {
      "admission":load("admissions/research_compute_node_admission_v2.json"),
      "readiness":load("evidence/research_compute_node_readiness_v5.json"),
      "plan":load("evidence/research_compute_node_build_plan_v6.json"),
      "aset":load("evidence/research_compute_node_artifact_set_v3.json"),
      "negative":load("evidence/research_compute_node_self_digest_negative_evidence_v1.json"),
      "nloc":load("evidence/agi_nexus_artifact_location_evidence_v1.json"),
      "sloc":load("evidence/synergynet_artifact_location_evidence_v1.json"),
      "registry":load("registry/research_compute_node_artifact_registry_v3.json"),
      "deployment":load("deployments/research_compute_node_deployment_plan_v3.json"),
    }

def args(b): return (b["admission"],b["readiness"],b["plan"],b["aset"],b["nloc"],b["sloc"],b["negative"])
def verify_adm(b): return verify_admission_v2(*args(b))
def verify_reg(b): return verify_artifact_registry_v3(b["registry"],*args(b))
def verify_dep(b): return verify_deployment_plan_v3(b["deployment"],b["registry"],*args(b))

def test_canonical_admission_v2_and_deployment_v3_pass():
    b=bundle(); verify_adm(b); verify_reg(b); out=verify_dep(b)
    assert out["blockers"]==BLOCKERS
    assert out["deployment_status"]=="BLOCKED_NOT_LAUNCHABLE"
    assert out["running"] is False and out["auto_start"] is False

def test_location_file_id_substitution_rejected_with_fresh_hash():
    b=bundle(); x=copy.deepcopy(b["nloc"]); x["provider_file_id"]="fake"; x["location_evidence_digest"]=digest(x,"location_evidence_digest"); b["nloc"]=x
    with pytest.raises(AdmissionV2Error): verify_adm(b)

def test_admission_cannot_start_or_gain_payment_authority():
    b=bundle(); a=copy.deepcopy(b["admission"]); a["running"]=True; a["payment_authority"]="METAPAY"; a["admission_digest"]=digest(a,"admission_digest"); b["admission"]=a
    with pytest.raises(AdmissionV2Error): verify_adm(b)

def test_registry_cannot_repromote_historical_nexus():
    b=bundle(); r=copy.deepcopy(b["registry"]); r["entries"][0]["artifact_digest"]="fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64"; r["registry_digest"]=digest(r,"registry_digest"); b["registry"]=r
    with pytest.raises(AdmissionV2Error): verify_reg(b)

def test_registry_cannot_erase_negative_evidence():
    b=bundle(); r=copy.deepcopy(b["registry"]); r["negative_evidence_digests"]=[]; r["registry_digest"]=digest(r,"registry_digest"); b["registry"]=r
    with pytest.raises(AdmissionV2Error): verify_reg(b)

def test_deployment_cannot_erase_host_blocker():
    b=bundle(); d=copy.deepcopy(b["deployment"]); d["blockers"]=["SUPERVISOR_CONFIG_NOT_MATERIALIZED","DEPLOYMENT_EVIDENCE_NOT_EXECUTED"]; d["deployment_digest"]=digest(d,"deployment_digest"); b["deployment"]=d
    with pytest.raises(AdmissionV2Error): verify_dep(b)

def test_deployment_cannot_invent_host_or_supervisor():
    b=bundle(); d=copy.deepcopy(b["deployment"]); d["host_binding_status"]="HOST_BOUND"; d["host_profile_digest"]="0"*64; d["supervisor_status"]="MATERIALIZED"; d["deployment_digest"]=digest(d,"deployment_digest"); b["deployment"]=d
    with pytest.raises(AdmissionV2Error): verify_dep(b)

def test_deployment_cannot_mark_process_running_or_change_nexus_network():
    b=bundle(); d=copy.deepcopy(b["deployment"]); d["processes"][0]["planned_state"]="RUNNING"; d["processes"][0]["network_policy"]="ARBITRARY_EGRESS"; d["running"]=True; d["deployment_digest"]=digest(d,"deployment_digest"); b["deployment"]=d
    with pytest.raises(AdmissionV2Error): verify_dep(b)

def test_deployment_cannot_gain_financial_accounting_execution_authority():
    b=bundle(); d=copy.deepcopy(b["deployment"]); d["financial_authority"]="TREASURY"; d["accounting_authority"]="FINANCIAL_OS"; d["execution_authority"]="ROOT"; d["deployment_digest"]=digest(d,"deployment_digest"); b["deployment"]=d
    with pytest.raises(AdmissionV2Error): verify_dep(b)
