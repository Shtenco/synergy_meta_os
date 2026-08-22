from __future__ import annotations
from .admission_v2 import ADMISSION, N_ART, S_ART, N_RUNTIME, C_RUNTIME, R_RUNTIME, require_self, req, verify_admission_v2

REGISTRY="6acdfaefec3b927965018ada1b984a53af4ee325b4c11b5fed0acf8a45acce3f"
DEPLOYMENT="fe6d073d7ee69a2a45a9f657cd247dbd7a2d9042ffb232607dd842ee6e22f83a"
PREV_REGISTRY="46809f10fd648ad24bf002c54708cd977eaaab8b1d65486a2f0fdb505140de7c"
PREV_DEPLOYMENT="381ac687eeff4b771c3cf18900b4485325bd98be7995c6982a251e68074c72f6"
N_LOC="65945f7cce45b6e7da40a59121b84013483da13f61027a1c93a8dc37fc659568"
S_LOC="de7d250414701a1b5a4e9fb31b8853d17882345829804121c569955075224fad"
OLD_NEG="81f7a4007a170ea3136d0ae936b4c8bd8b82c3bc36201de0c9cd2d816a4d21d8"
CENTRAL_NEG="564dfab1230dc28270dfc392125234208e4762400a6488c5d53a936f3d9bbdaa"
BLOCKERS=["HOST_PROFILE_NOT_BOUND","SUPERVISOR_CONFIG_NOT_MATERIALIZED","DEPLOYMENT_EVIDENCE_NOT_EXECUTED"]

def verify_artifact_registry_v3(registry,admission,readiness,plan,aset,nloc,sloc,negative):
    verify_admission_v2(admission,readiness,plan,aset,nloc,sloc,negative);require_self(registry,"registry_digest",REGISTRY)
    req(registry.get("schema")=="synergy.meta-os-artifact-registry/v3" and registry.get("previous_registry_digest")==PREV_REGISTRY and registry.get("admission_digest")==ADMISSION,"registry ancestry drift")
    req(registry.get("artifact_set_digest")==aset.get("artifact_set_digest"),"registry artifact-set drift")
    req(registry.get("negative_evidence_digests")==[OLD_NEG,CENTRAL_NEG],"registry negative evidence drift")
    entries=registry.get("entries",[]);req([x.get("artifact_id") for x in entries]==["nexus","synergynet"],"registry entry set drift")
    n,s=entries
    req((n.get("artifact_digest"),n.get("artifact_size"),n.get("runtime_spec_digest"),n.get("artifact_location_evidence_digest"))==(N_ART,56965,N_RUNTIME,N_LOC),"registry nexus identity drift")
    req(n.get("historical_artifact_digest")=="fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64" and n.get("historical_invalid_locator_negative_evidence_digest")==OLD_NEG,"registry nexus history drift")
    req((s.get("artifact_digest"),s.get("artifact_size"),s.get("artifact_location_evidence_digest"))==(S_ART,12837,S_LOC),"registry synergynet identity drift")
    for x,fid in ((n,"1yyCOrePdOoYFybGZoDGA5jcNdQdiHPpy"),(s,"1zuB8rjKO0HHIZmvUEGZnAbnkKGNN59qp")):
        req(x.get("locator_status")=="VERIFIED_DURABLE_CONNECTED_BINARY" and x.get("availability_status")=="DURABLE_CONNECTED_DRIVE_BINARY","registry locator status drift")
        req(x.get("provider")=="GOOGLE_DRIVE_CONNECTED_FILE" and x.get("provider_file_id")==fid and x.get("resolution_contract")=="FETCH_BY_PROVIDER_FILE_ID_THEN_VERIFY_SHA256_AND_SIZE_BEFORE_EXECUTION","registry locator binding drift")
    req(registry.get("registry_status")=="ALL_REQUIRED_ARTIFACTS_DURABLY_LOCATABLE" and registry.get("blockers")==[],"registry blockers/status drift")
    for f in ("financial_authority","payment_authority","accounting_authority","execution_authority"): req(registry.get(f)=="NONE",f"registry {f} escalation")
    return registry

def verify_deployment_plan_v3(deployment,registry,admission,readiness,plan,aset,nloc,sloc,negative):
    verify_artifact_registry_v3(registry,admission,readiness,plan,aset,nloc,sloc,negative);require_self(deployment,"deployment_digest",DEPLOYMENT)
    req(deployment.get("schema")=="synergy.meta-os-deployment-plan/v3" and deployment.get("previous_deployment_digest")==PREV_DEPLOYMENT and deployment.get("admission_digest")==ADMISSION and deployment.get("artifact_registry_digest")==REGISTRY,"deployment ancestry drift")
    req(deployment.get("host_binding_status")=="HOST_UNBOUND" and deployment.get("host_profile_digest") is None,"deployment cannot invent host")
    processes=deployment.get("processes",[]);req([x.get("service_id") for x in processes]==["nexus","content-cache","synergynet"],"deployment process set drift")
    expected={"nexus":(N_ART,N_RUNTIME,[],"NO_NETWORK","1yyCOrePdOoYFybGZoDGA5jcNdQdiHPpy"),"content-cache":(S_ART,C_RUNTIME,["store_path","listen_host","listen_port"],"OPERATOR_LOCAL_BIND_ONLY","1zuB8rjKO0HHIZmvUEGZnAbnkKGNN59qp"),"synergynet":(S_ART,R_RUNTIME,["peer_directory","listen_host","listen_port"],"STATIC_OPERATOR_LOCAL_ALLOWLIST_ONLY","1zuB8rjKO0HHIZmvUEGZnAbnkKGNN59qp")}
    for p in processes:
        e=expected[p["service_id"]]
        req((p.get("artifact_digest"),p.get("runtime_spec_digest"),p.get("operator_binding_required"),p.get("network_policy"),p.get("provider_file_id"))==e,f"{p['service_id']} deployment binding drift")
        req(p.get("artifact_location_status")=="DURABLE_CONNECTED_DRIVE_BINARY" and p.get("resolution_contract")=="FETCH_BY_PROVIDER_FILE_ID_THEN_VERIFY_SHA256_AND_SIZE_BEFORE_EXECUTION" and p.get("planned_state")=="NOT_STARTED",f"{p['service_id']} state drift")
    req(deployment.get("supervisor_status")=="NOT_MATERIALIZED" and deployment.get("deployment_evidence_status")=="NOT_EXECUTED","deployment supervisor/evidence overclaim")
    req(deployment.get("blockers")==BLOCKERS and deployment.get("deployment_status")=="BLOCKED_NOT_LAUNCHABLE","deployment blockers/status drift")
    req(deployment.get("running") is False and deployment.get("auto_start") is False,"deployment cannot start node")
    for f in ("financial_authority","payment_authority","accounting_authority","execution_authority"): req(deployment.get(f)=="NONE",f"deployment {f} escalation")
    return deployment
