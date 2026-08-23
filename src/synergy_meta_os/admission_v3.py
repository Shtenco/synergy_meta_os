from __future__ import annotations
import hashlib,json
from typing import Any

class AdmissionV3Error(ValueError): pass

READINESS_COMMIT="349c8d506be14043b120be868851117990855d26"
READINESS="6714beff9f366ed19c6b000b9239afffcd797cfc9d3fc4319b70a8af53b9af1f"
PLAN="46a4ee4c01fba5fb8c5e3cff51b4f6b5e7090347ef1ec1ab6763a606a31aaa2e"
ASET="d479b71a0756288b5d8d6d7d7433881cbd448a63c22bc9f87f271df7f82479c2"
CENTRAL_NEG="564dfab1230dc28270dfc392125234208e4762400a6488c5d53a936f3d9bbdaa"
LOCATION_NEG="f17fdeab2dceb1aca3d939b57a6d5374eba6988c5f7b991ad80d3e9523d4e107"
TOOLCHAIN="af92c9f1909ae3b64aaea78bdce2c6d05deb974ad242482b36e0c8ce820a2848"
ADMISSION="e16e9c0334ed0dcd61aeac0ac1044139ec735c3fcbea92bb1eb55b171bfbb13e"
N_ART="e87d00809ff976c76655b892166ec1cf1f13a893927ead156295b6814fcd9325"
S_ART="7f22e68d80a7df879af71ebccdb45f8edb10cae3698bf07faa7076ce76fd0ef7"
N_LOC="341989039238b9735018bad71c2ac1f0114ae15b4736faa524b5f7a643c27f47"
S_LOC="c4102a8e668b79fc961a5f1767154154f4a600d320442770d74c7a006a5cee08"
N_RT="e7e9bfd5684e8a1c3b0964288945d750d8cc109869a5dae54fc3ad64de5e8998"
C_RT="abb35edd0336ea36f249d24b04e1b7482fea4ecebc5c881b655bf8a390d8b5ad"
R_RT="8c38cd130e3dd73723e3a3241d2df61bef218abdab2d16785ccec5b172fac4df"
N_FILE="1yyCOrePdOoYFybGZoDGA5jcNdQdiHPpy"
S_FILE="1zuB8rjKO0HHIZmvUEGZnAbnkKGNN59qp"

def canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(v:dict[str,Any],field:str)->str:
    b=dict(v);b.pop(field,None);return hashlib.sha256(canonical(b)).hexdigest()
def req(c:bool,m:str):
    if not c:raise AdmissionV3Error(m)
def selfhash(v,field,expected):req(v.get(field)==expected and digest(v,field)==expected,f"{field} mismatch")

def verify_location(v,kind):
    exp=(N_LOC,N_ART,56965,N_FILE,"Shtenco/agi_nexus") if kind=="nexus" else (S_LOC,S_ART,12837,S_FILE,"Shtenco/synergynet")
    selfhash(v,"location_evidence_digest",exp[0])
    req(v.get("schema")=="synergy.artifact-location-evidence/v2" and v.get("repository")==exp[4],"location identity drift")
    req((v.get("artifact_digest"),v.get("artifact_size"))==(exp[1],exp[2]),"location artifact drift")
    req(v.get("provider")=="GOOGLE_DRIVE_CONNECTED_FILE" and v.get("provider_file_id")==exp[3],"location provider drift")
    p=v.get("pre_upload_validation",{});req((p.get("sha256"),p.get("size"),p.get("status"))==(exp[1],exp[2],"PASS"),"location pre-upload drift")
    req(v.get("integrity_model")=="CANONICAL_SELF_DIGEST_AND_FETCH_TIME_ARTIFACT_SHA256_SIZE","location integrity drift")
    req(v.get("resolution_contract")=="FETCH_BY_PROVIDER_FILE_ID_THEN_VERIFY_SHA256_AND_SIZE_BEFORE_EXECUTION" and v.get("execution_authority")=="NONE","location contract/authority drift")

def verify_upstream(readiness,plan,aset,central_negative,location_negative,nloc,sloc):
    selfhash(central_negative,"evidence_digest",CENTRAL_NEG);selfhash(location_negative,"evidence_digest",LOCATION_NEG)
    req(location_negative.get("effect")=="DO_NOT_USE_V1_LOCATION_EVIDENCE_OR_DEPENDENT_ROOTS_AS_CANONICAL","location-negative effect drift")
    deps=location_negative.get("dependent_superseded_roots",{})
    req((deps.get("meta_admission_v2"),deps.get("meta_registry_v3"),deps.get("meta_deployment_v3"))==("8a157a199918b194cdaf1ad4b54c4586eb7bc8cdbd24b2f3ffe0c36d8734bc4c","6acdfaefec3b927965018ada1b984a53af4ee325b4c11b5fed0acf8a45acce3f","fe6d073d7ee69a2a45a9f657cd247dbd7a2d9042ffb232607dd842ee6e22f83a"),"superseded Meta roots drift")
    verify_location(nloc,"nexus");verify_location(sloc,"synergynet")
    selfhash(aset,"artifact_set_digest",ASET);req(aset.get("schema")=="synergy.node-artifact-set/v4" and aset.get("location_evidence_self_digest_negative_evidence_digest")==LOCATION_NEG,"artifact set root drift")
    services=aset.get("services",[]);req([x.get("service_id") for x in services]==["content-cache","nexus","synergynet"],"artifact service set drift")
    req(services[0].get("artifact_digest")==S_ART and services[0].get("artifact_location_evidence_digest")==S_LOC and services[0].get("provider_file_id")==S_FILE,"content-cache binding drift")
    req(services[1].get("artifact_digest")==N_ART and services[1].get("artifact_location_evidence_digest")==N_LOC and services[1].get("provider_file_id")==N_FILE,"nexus binding drift")
    req(services[1].get("network_access")=="NONE" and services[1].get("process_execution_authority")=="NONE" and services[1].get("financial_authority")=="NONE" and services[1].get("execution_authority")=="NONE","nexus authority drift")
    req(services[2].get("artifact_digest")==S_ART and services[2].get("artifact_location_evidence_digest")==S_LOC,"synergynet binding drift")
    selfhash(plan,"plan_digest",PLAN);req(plan.get("schema")=="synergy.node-build-plan/v7" and plan.get("artifact_set_digest")==ASET and plan.get("services")==services and plan.get("build_blockers")==[],"plan root/services drift")
    selfhash(readiness,"readiness_digest",READINESS);req(readiness.get("schema")=="synergy.node-readiness/v6" and readiness.get("build_plan_digest")==PLAN and readiness.get("artifact_set_digest")==ASET,"readiness root drift")
    req(readiness.get("blockers")==[] and readiness.get("node_status")=="NODE_ADMISSION_READY_NOT_RUNNING" and readiness.get("auto_start") is False,"readiness state drift")
    for f in ("financial_authority","payment_authority","accounting_authority","execution_authority"):req(readiness.get(f)=="NONE",f"readiness {f} escalation")

def expected_artifacts():
    return [{"service_id":"content-cache","artifact_digest":S_ART,"runtime_spec_digest":C_RT,"artifact_location_evidence_digest":S_LOC},{"service_id":"nexus","artifact_digest":N_ART,"runtime_spec_digest":N_RT,"artifact_location_evidence_digest":N_LOC},{"service_id":"synergynet","artifact_digest":S_ART,"runtime_spec_digest":R_RT,"artifact_location_evidence_digest":S_LOC}]

def verify_admission_v3(admission,readiness,plan,aset,central_negative,location_negative,nloc,sloc):
    verify_upstream(readiness,plan,aset,central_negative,location_negative,nloc,sloc);selfhash(admission,"admission_digest",ADMISSION)
    req(admission.get("schema")=="synergy.meta-os-admission/v3" and admission.get("subject")=="RESEARCH_COMPUTE_NODE","admission identity drift")
    exact={"previous_admission_digest":"8a157a199918b194cdaf1ad4b54c4586eb7bc8cdbd24b2f3ffe0c36d8734bc4c","readiness_repository":"Shtenco/synergy_system","readiness_commit":READINESS_COMMIT,"readiness_digest":READINESS,"build_plan_digest":PLAN,"toolchain_lock_digest":TOOLCHAIN,"artifact_set_digest":ASET,"central_self_digest_negative_evidence_digest":CENTRAL_NEG,"location_evidence_self_digest_negative_evidence_digest":LOCATION_NEG}
    for k,v in exact.items():req(admission.get(k)==v,f"admission {k} drift")
    req(admission.get("artifacts")==expected_artifacts(),"admission artifact bindings drift")
    req(admission.get("decision")=="ADMITTED_CANONICAL_DURABLE_ARTIFACTS_NOT_RUNNING" and admission.get("admission_effect")=="REGISTRY_ELIGIBILITY_ONLY","admission decision/effect drift")
    req(admission.get("running") is False and admission.get("auto_start") is False and admission.get("network_authority_change")=="NONE","admission start/network escalation")
    for f in ("financial_authority","payment_authority","accounting_authority","execution_authority"):req(admission.get(f)=="NONE",f"admission {f} escalation")
    return admission
