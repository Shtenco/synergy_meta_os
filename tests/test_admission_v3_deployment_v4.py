from __future__ import annotations
import copy,json
from pathlib import Path
import pytest
from synergy_meta_os.admission_v3 import AdmissionV3Error,digest,verify_admission_v3
from synergy_meta_os.deployment_v4 import BLOCKERS,verify_artifact_registry_v4,verify_deployment_plan_v4

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def b():return {"admission":load("admissions/research_compute_node_admission_v3.json"),"readiness":load("evidence/research_compute_node_readiness_v6.json"),"plan":load("evidence/research_compute_node_build_plan_v7.json"),"aset":load("evidence/research_compute_node_artifact_set_v4.json"),"central":load("evidence/research_compute_node_self_digest_negative_evidence_v1.json"),"location":load("evidence/research_compute_node_location_evidence_self_digest_negative_evidence_v1.json"),"nloc":load("evidence/agi_nexus_artifact_location_evidence_v2.json"),"sloc":load("evidence/synergynet_artifact_location_evidence_v2.json"),"registry":load("registry/research_compute_node_artifact_registry_v4.json"),"deployment":load("deployments/research_compute_node_deployment_plan_v4.json")}
def args(x):return (x["admission"],x["readiness"],x["plan"],x["aset"],x["central"],x["location"],x["nloc"],x["sloc"])
def adm(x):return verify_admission_v3(*args(x))
def reg(x):return verify_artifact_registry_v4(x["registry"],*args(x))
def dep(x):return verify_deployment_plan_v4(x["deployment"],x["registry"],*args(x))

def test_canonical_v3_v4_v4_pass_fail_closed():
    x=b();adm(x);reg(x);out=dep(x);assert out["blockers"]==BLOCKERS;assert out["deployment_status"]=="BLOCKED_NOT_LAUNCHABLE";assert out["running"] is False and out["auto_start"] is False

def test_v2_admission_cannot_be_repromoted():
    x=b();a=copy.deepcopy(x["admission"]);a["schema"]="synergy.meta-os-admission/v2";a["admission_digest"]="8a157a199918b194cdaf1ad4b54c4586eb7bc8cdbd24b2f3ffe0c36d8734bc4c";x["admission"]=a
    with pytest.raises(AdmissionV3Error):adm(x)

def test_v1_location_evidence_cannot_reenter_through_fresh_admission_hash():
    x=b();a=copy.deepcopy(x["admission"]);a["artifacts"][1]["artifact_location_evidence_digest"]="65945f7cce45b6e7da40a59121b84013483da13f61027a1c93a8dc37fc659568";a["admission_digest"]=digest(a,"admission_digest");x["admission"]=a
    with pytest.raises(AdmissionV3Error):adm(x)

def test_drive_file_substitution_rejected():
    x=b();l=copy.deepcopy(x["nloc"]);l["provider_file_id"]="fake";l["location_evidence_digest"]=digest(l,"location_evidence_digest");x["nloc"]=l
    with pytest.raises(AdmissionV3Error):adm(x)

def test_registry_cannot_erase_location_negative_evidence():
    x=b();r=copy.deepcopy(x["registry"]);r["negative_evidence_digests"]=r["negative_evidence_digests"][:-1];r["registry_digest"]=digest(r,"registry_digest");x["registry"]=r
    with pytest.raises(AdmissionV3Error):reg(x)

def test_registry_cannot_repromote_historical_nexus_artifact():
    x=b();r=copy.deepcopy(x["registry"]);r["entries"][0]["artifact_digest"]="fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64";r["registry_digest"]=digest(r,"registry_digest");x["registry"]=r
    with pytest.raises(AdmissionV3Error):reg(x)

def test_deployment_must_keep_exact_three_host_runtime_blockers():
    x=b();d=copy.deepcopy(x["deployment"]);d["blockers"]=["DEPLOYMENT_EVIDENCE_NOT_EXECUTED"];d["deployment_digest"]=digest(d,"deployment_digest");x["deployment"]=d
    with pytest.raises(AdmissionV3Error):dep(x)

def test_deployment_cannot_reinsert_artifact_location_blocker():
    x=b();d=copy.deepcopy(x["deployment"]);d["blockers"]=["NEXUS_ARTIFACT_LOCATION_NOT_DURABLE"]+BLOCKERS;d["deployment_digest"]=digest(d,"deployment_digest");x["deployment"]=d
    with pytest.raises(AdmissionV3Error):dep(x)

def test_deployment_cannot_invent_host_supervisor_or_running_process():
    x=b();d=copy.deepcopy(x["deployment"]);d["host_binding_status"]="HOST_BOUND";d["host_profile_digest"]="0"*64;d["supervisor_status"]="MATERIALIZED";d["processes"][0]["planned_state"]="RUNNING";d["running"]=True;d["deployment_digest"]=digest(d,"deployment_digest");x["deployment"]=d
    with pytest.raises(AdmissionV3Error):dep(x)

def test_nexus_network_and_all_money_authorities_remain_none():
    x=b();d=copy.deepcopy(x["deployment"]);d["processes"][0]["network_policy"]="ARBITRARY_EGRESS";d["financial_authority"]="TREASURY";d["payment_authority"]="METAPAY";d["accounting_authority"]="FINANCIAL_OS";d["execution_authority"]="ROOT";d["deployment_digest"]=digest(d,"deployment_digest");x["deployment"]=d
    with pytest.raises(AdmissionV3Error):dep(x)
