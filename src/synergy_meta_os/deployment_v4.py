from __future__ import annotations
from .admission_v3 import AdmissionV3Error,ADMISSION,N_ART,S_ART,N_LOC,S_LOC,N_RT,C_RT,R_RT,N_FILE,S_FILE,selfhash,req,verify_admission_v3

REGISTRY="a67257b09688d08c6ddf39c0bed9847677de57df79c08d40a2e6bcc67e260960"
DEPLOYMENT="911e15e9b9913c6201d6a034654aac336f8bbf298b7d720b9c9f987dced51d7c"
PREV_REGISTRY="6acdfaefec3b927965018ada1b984a53af4ee325b4c11b5fed0acf8a45acce3f"
PREV_DEPLOYMENT="fe6d073d7ee69a2a45a9f657cd247dbd7a2d9042ffb232607dd842ee6e22f83a"
OLD_NEG="81f7a4007a170ea3136d0ae936b4c8bd8b82c3bc36201de0c9cd2d816a4d21d8"
CENTRAL_NEG="564dfab1230dc28270dfc392125234208e4762400a6488c5d53a936f3d9bbdaa"
LOCATION_NEG="f17fdeab2dceb1aca3d939b57a6d5374eba6988c5f7b991ad80d3e9523d4e107"
BLOCKERS=["HOST_PROFILE_NOT_BOUND","SUPERVISOR_CONFIG_NOT_MATERIALIZED","DEPLOYMENT_EVIDENCE_NOT_EXECUTED"]

def verify_artifact_registry_v4(registry,admission,readiness,plan,aset,central_negative,location_negative,nloc,sloc):
    verify_admission_v3(admission,readiness,plan,aset,central_negative,location_negative,nloc,sloc);selfhash(registry,"registry_digest",REGISTRY)
    req(registry.get("schema")=="synergy.meta-os-artifact-registry/v4" and registry.get("previous_registry_digest")==PREV_REGISTRY and registry.get("admission_digest")==ADMISSION,"registry ancestry drift")
    req(registry.get("artifact_set_digest")==aset.get("artifact_set_digest") and registry.get("negative_evidence_digests")==[OLD_NEG,CENTRAL_NEG,LOCATION_NEG],"registry evidence roots drift")
    entries=registry.get("entries",[]);req([x.get("artifact_id") for x in entries]==["nexus","synergynet"],"registry entry set drift")
    n,s=entries
    req((n.get("artifact_digest"),n.get("artifact_size"),n.get("runtime_spec_digest"),n.get("artifact_location_evidence_digest"))==(N_ART,56965,N_RT,N_LOC),"registry nexus identity drift")
    req(n.get("historical_artifact_digest")=="fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64" and n.get("historical_invalid_locator_negative_evidence_digest")==OLD_NEG,"registry nexus history drift")
    req((s.get("artifact_digest"),s.get("artifact_size"),s.get("artifact_location_evidence_digest"))==(S_ART,12837,S_LOC),"registry synergynet identity drift")
    req(s.get("runtime_spec_digests")=={"content-cache":C_RT,"synergynet":R_RT},"registry synergynet runtime binding drift")
    for x,fid in ((n,N_FILE),(s,S_FILE)):
        req(x.get("locator_status")=="VERIFIED_DURABLE_CONNECTED_BINARY_CANONICAL_EVIDENCE" and x.get("availability_status")=="DURABLE_CONNECTED_DRIVE_BINARY","registry locator state drift")
        req(x.get("provider")=="GOOGLE_DRIVE_CONNECTED_FILE" and x.get("provider_file_id")==fid and x.get("resolution_contract")=="FETCH_BY_PROVIDER_FILE_ID_THEN_VERIFY_SHA256_AND_SIZE_BEFORE_EXECUTION","registry locator binding drift")
    req(registry.get("registry_status")=="ALL_REQUIRED_ARTIFACTS_DURABLY_LOCATABLE_CANONICAL_EVIDENCE" and registry.get("blockers")==[],"registry blockers/status drift")
    for f in ("financial_authority","payment_authority","accounting_authority","execution_authority"):req(registry.get(f)=="NONE",f"registry {f} escalation")
    return registry

def verify_deployment_plan_v4(deployment,registry,admission,readiness,plan,aset,central_negative,location_negative,nloc,sloc):
    verify_artifact_registry_v4(registry,admission,readiness,plan,aset,central_negative,location_negative,nloc,sloc);selfhash(deployment,"deployment_digest",DEPLOYMENT)
    req(deployment.get("schema")=="synergy.meta-os-deployment-plan/v4" and deployment.get("previous_deployment_digest")==PREV_DEPLOYMENT and deployment.get("admission_digest")==ADMISSION and deployment.get("artifact_registry_digest")==REGISTRY,"deployment ancestry/root drift")
    req(deployment.get("host_binding_status")=="HOST_UNBOUND" and deployment.get("host_profile_digest") is None,"deployment cannot invent host")
    processes=deployment.get("processes",[]);req([x.get("service_id") for x in processes]==["nexus","content-cache","synergynet"],"deployment process set drift")
    expected={"nexus":(N_ART,N_RT,N_LOC,[],"NO_NETWORK",N_FILE),"content-cache":(S_ART,C_RT,S_LOC,["store_path","listen_host","listen_port"],"OPERATOR_LOCAL_BIND_ONLY",S_FILE),"synergynet":(S_ART,R_RT,S_LOC,["peer_directory","listen_host","listen_port"],"STATIC_OPERATOR_LOCAL_ALLOWLIST_ONLY",S_FILE)}
    for p in processes:
        e=expected[p["service_id"]]
        req((p.get("artifact_digest"),p.get("runtime_spec_digest"),p.get("artifact_location_evidence_digest"),p.get("operator_binding_required"),p.get("network_policy"),p.get("provider_file_id"))==e,f"{p['service_id']} deployment binding drift")
        req(p.get("artifact_location_status")=="DURABLE_CONNECTED_DRIVE_BINARY_CANONICAL_EVIDENCE" and p.get("resolution_contract")=="FETCH_BY_PROVIDER_FILE_ID_THEN_VERIFY_SHA256_AND_SIZE_BEFORE_EXECUTION" and p.get("planned_state")=="NOT_STARTED",f"{p['service_id']} state drift")
    req(deployment.get("supervisor_status")=="NOT_MATERIALIZED" and deployment.get("deployment_evidence_status")=="NOT_EXECUTED","deployment supervisor/evidence overclaim")
    req(deployment.get("blockers")==BLOCKERS and deployment.get("deployment_status")=="BLOCKED_NOT_LAUNCHABLE","deployment blockers/status drift")
    req(deployment.get("running") is False and deployment.get("auto_start") is False,"deployment cannot start node")
    for f in ("financial_authority","payment_authority","accounting_authority","execution_authority"):req(deployment.get(f)=="NONE",f"deployment {f} escalation")
    return deployment
