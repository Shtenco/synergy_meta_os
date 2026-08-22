from __future__ import annotations
import hashlib,json
from typing import Any

class AdmissionV2Error(ValueError): pass

READY_COMMIT="1bc670d865dbebe48ab3ab02ebde88acafc3ab9b"
READY="01c706352c6a63d8545373b29999dba9a9d3407bcf5c5e804e3e82a2571e2112"
PLAN="74c32607bc9fdadf43dddc87c58aa58adeaa2d795553d02cba87cf55ca12ec98"
ASET="bc7d89378424a18727b90072c86e06238ea14e64bfb9dfc4464f184297eddf84"
NEG="564dfab1230dc28270dfc392125234208e4762400a6488c5d53a936f3d9bbdaa"
TOOLCHAIN="af92c9f1909ae3b64aaea78bdce2c6d05deb974ad242482b36e0c8ce820a2848"
ADMISSION="8a157a199918b194cdaf1ad4b54c4586eb7bc8cdbd24b2f3ffe0c36d8734bc4c"
N_LOC="65945f7cce45b6e7da40a59121b84013483da13f61027a1c93a8dc37fc659568"
S_LOC="de7d250414701a1b5a4e9fb31b8853d17882345829804121c569955075224fad"
N_ART="e87d00809ff976c76655b892166ec1cf1f13a893927ead156295b6814fcd9325"
S_ART="7f22e68d80a7df879af71ebccdb45f8edb10cae3698bf07faa7076ce76fd0ef7"
N_RUNTIME="e7e9bfd5684e8a1c3b0964288945d750d8cc109869a5dae54fc3ad64de5e8998"
C_RUNTIME="abb35edd0336ea36f249d24b04e1b7482fea4ecebc5c881b655bf8a390d8b5ad"
R_RUNTIME="8c38cd130e3dd73723e3a3241d2df61bef218abdab2d16785ccec5b172fac4df"

def canonical(v:Any)->bytes: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(v,field): b=dict(v);b.pop(field,None);return hashlib.sha256(canonical(b)).hexdigest()
def req(c,m):
    if not c: raise AdmissionV2Error(m)
def require_self(v,field,expected): req(v.get(field)==expected and digest(v,field)==expected,f"{field} mismatch")

def verify_negative(v):
    require_self(v,"evidence_digest",NEG)
    req(v.get("effect")=="DO_NOT_USE_V2_OR_V5_AS_CANONICAL_ROOT" and v.get("execution_authority")=="NONE","negative evidence drift")
    req(v.get("artifact_set_v2",{}).get("canonical_recomputed_self_digest")=="8a9617369ce5b60f9b86da866300053f6cdb24f9f90322877e9a5e0a24300f3b","negative artifact-set digest drift")
    req(v.get("build_plan_v5",{}).get("canonical_recomputed_self_digest")=="97266c83362027530feaeec9d84791be4029a9963948b17379b53b6e5f982567","negative plan digest drift")

def verify_location(v,kind):
    expected=(N_LOC,N_ART,56965,"1yyCOrePdOoYFybGZoDGA5jcNdQdiHPpy") if kind=="nexus" else (S_LOC,S_ART,12837,"1zuB8rjKO0HHIZmvUEGZnAbnkKGNN59qp")
    require_self(v,"location_evidence_digest",expected[0])
    req(v.get("artifact_digest")==expected[1] and v.get("artifact_size")==expected[2],"location artifact drift")
    req(v.get("provider")=="GOOGLE_DRIVE_CONNECTED_FILE" and v.get("provider_file_id")==expected[3],"location provider drift")
    p=v.get("pre_upload_validation",{})
    req((p.get("sha256"),p.get("size"),p.get("status"))==(expected[1],expected[2],"PASS"),"location pre-upload drift")
    req(v.get("availability_status")=="DURABLE_CONNECTED_DRIVE_BINARY" and v.get("resolution_contract")=="FETCH_BY_PROVIDER_FILE_ID_THEN_VERIFY_SHA256_AND_SIZE_BEFORE_EXECUTION" and v.get("execution_authority")=="NONE","location contract drift")

def verify_artifact_set(aset,nloc,sloc,negative):
    verify_negative(negative);verify_location(nloc,"nexus");verify_location(sloc,"synergynet");require_self(aset,"artifact_set_digest",ASET)
    req(aset.get("schema")=="synergy.node-artifact-set/v3" and aset.get("central_self_digest_negative_evidence_digest")==NEG,"artifact set root drift")
    s=aset.get("services",[]);req([x.get("service_id") for x in s]==["content-cache","nexus","synergynet"],"artifact service set drift")
    req(s[0].get("artifact_digest")==S_ART and s[0].get("artifact_location_evidence_digest")==S_LOC and s[0].get("provider_file_id")=="1zuB8rjKO0HHIZmvUEGZnAbnkKGNN59qp","content-cache binding drift")
    req(s[1].get("artifact_digest")==N_ART and s[1].get("artifact_location_evidence_digest")==N_LOC and s[1].get("provider_file_id")=="1yyCOrePdOoYFybGZoDGA5jcNdQdiHPpy","nexus binding drift")
    req(s[1].get("financial_authority")=="NONE" and s[1].get("network_access")=="NONE" and s[1].get("process_execution_authority")=="NONE","nexus authority drift")
    req(s[2].get("artifact_digest")==S_ART and s[2].get("artifact_location_evidence_digest")==S_LOC,"relay binding drift")
    req(aset.get("artifact_set_status")=="ALL_ARTIFACTS_VERIFIED_AND_DURABLY_LOCATABLE" and aset.get("execution_authority")=="NONE","artifact set status drift")
    return aset

def verify_plan(plan,aset,nloc,sloc,negative):
    verify_artifact_set(aset,nloc,sloc,negative);require_self(plan,"plan_digest",PLAN)
    req(plan.get("schema")=="synergy.node-build-plan/v6" and plan.get("artifact_set_digest")==ASET and plan.get("central_self_digest_negative_evidence_digest")==NEG,"plan root drift")
    req(plan.get("services")==aset.get("services") and plan.get("build_blockers")==[],"plan services/blockers drift")
    req(plan.get("plan_status")=="BUILD_ARTIFACTS_VERIFIED_REPRODUCIBLE_DURABLY_LOCATABLE" and plan.get("execution_authority")=="NONE","plan status drift")

def verify_readiness(readiness,plan,aset,nloc,sloc,negative):
    verify_plan(plan,aset,nloc,sloc,negative);require_self(readiness,"readiness_digest",READY)
    req(readiness.get("schema")=="synergy.node-readiness/v5" and readiness.get("build_plan_digest")==PLAN and readiness.get("artifact_set_digest")==ASET and readiness.get("central_self_digest_negative_evidence_digest")==NEG,"readiness root drift")
    req(readiness.get("blockers")==[] and readiness.get("node_status")=="NODE_ADMISSION_READY_NOT_RUNNING" and readiness.get("auto_start") is False,"readiness state drift")
    for f in ("financial_authority","payment_authority","accounting_authority","execution_authority"): req(readiness.get(f)=="NONE",f"readiness {f} escalation")
    return readiness

def expected_artifacts():
    return [{"service_id":"content-cache","artifact_digest":S_ART,"runtime_spec_digest":C_RUNTIME,"artifact_location_evidence_digest":S_LOC},{"service_id":"nexus","artifact_digest":N_ART,"runtime_spec_digest":N_RUNTIME,"artifact_location_evidence_digest":N_LOC},{"service_id":"synergynet","artifact_digest":S_ART,"runtime_spec_digest":R_RUNTIME,"artifact_location_evidence_digest":S_LOC}]

def verify_admission_v2(admission,readiness,plan,aset,nloc,sloc,negative):
    verify_readiness(readiness,plan,aset,nloc,sloc,negative);require_self(admission,"admission_digest",ADMISSION)
    req(admission.get("schema")=="synergy.meta-os-admission/v2" and admission.get("subject")=="RESEARCH_COMPUTE_NODE","admission identity drift")
    exact={"readiness_repository":"Shtenco/synergy_system","readiness_commit":READY_COMMIT,"readiness_digest":READY,"build_plan_digest":PLAN,"toolchain_lock_digest":TOOLCHAIN,"artifact_set_digest":ASET,"central_self_digest_negative_evidence_digest":NEG}
    for k,v in exact.items(): req(admission.get(k)==v,f"admission {k} drift")
    req(admission.get("artifacts")==expected_artifacts(),"admission artifact bindings drift")
    req(admission.get("decision")=="ADMITTED_DURABLE_ARTIFACTS_NOT_RUNNING" and admission.get("admission_effect")=="REGISTRY_ELIGIBILITY_ONLY","admission effect drift")
    req(admission.get("running") is False and admission.get("auto_start") is False and admission.get("network_authority_change")=="NONE","admission start/network escalation")
    for f in ("financial_authority","payment_authority","accounting_authority","execution_authority"): req(admission.get(f)=="NONE",f"admission {f} escalation")
    return admission
