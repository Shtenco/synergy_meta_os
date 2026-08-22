from __future__ import annotations

from .admission_v1 import ARTIFACTS, ADMISSION, require_digest
from .deployment_v1 import DeploymentV1Error

REGISTRY_V1="8ecec30555e8a2a7930549b2e67583c2ea1fb90a422e6ed6523a5d8e01ff2d49"
REGISTRY_V2="46809f10fd648ad24bf002c54708cd977eaaab8b1d65486a2f0fdb505140de7c"
DEPLOYMENT_V1="dd66bef640aba79aa9055c590e6126c541b59f9f909ee033fc7b1982c4505c14"
DEPLOYMENT_V2="381ac687eeff4b771c3cf18900b4485325bd98be7995c6982a251e68074c72f6"
NEGATIVE="81f7a4007a170ea3136d0ae936b4c8bd8b82c3bc36201de0c9cd2d816a4d21d8"
NEXUS_REJECTED_COMMIT="a47840e6c76b3eefcc5b0053317f5219682e9ee1"
NEXUS_REJECTED_BLOB="bb541be8b71ebad5977b3849e66e10224f0e1ded"
NEXUS_REJECTED_SIZE=15009
REGISTRY_BLOCKERS=["NEXUS_ARTIFACT_LOCATION_NOT_DURABLE","SYNERGYNET_ARTIFACT_LOCATION_NOT_DURABLE"]
DEPLOYMENT_BLOCKERS=REGISTRY_BLOCKERS+["HOST_PROFILE_NOT_BOUND","SUPERVISOR_CONFIG_NOT_MATERIALIZED","DEPLOYMENT_EVIDENCE_NOT_EXECUTED"]


def _req(cond: bool, message: str) -> None:
    if not cond:
        raise DeploymentV1Error(message)


def verify_artifact_registry_v2(registry):
    _req(registry.get("schema")=="synergy.meta-os-artifact-registry/v2", "wrong corrected registry schema")
    require_digest(registry,"registry_digest",REGISTRY_V2)
    _req(registry.get("previous_registry_digest")==REGISTRY_V1 and registry.get("admission_digest")==ADMISSION, "registry ancestry drifted")
    _req(registry.get("negative_evidence_digests")==[NEGATIVE], "negative evidence omitted")
    entries=registry.get("entries")
    _req(isinstance(entries,list) and [x.get("artifact_id") for x in entries]==["nexus","synergynet"], "registry entry set drifted")
    nexus,synet=entries
    _req(nexus.get("artifact_digest")==ARTIFACTS["nexus"][0] and nexus.get("artifact_size")==56967, "NEXUS artifact identity drifted")
    _req(nexus.get("build_recipe_digest")=="3bbe2bf1f90a9ed1abade80782062256a1a72619b72345da41f7ed9897b4a735" and nexus.get("build_evidence_digest")=="cd14275a264ec1f0ef7045721eb18e31787d918cd78563f93ebb486333f8daee", "NEXUS build evidence drifted")
    _req(nexus.get("locator_status")=="NO_VERIFIED_DURABLE_BINARY_LOCATION" and nexus.get("availability_status")=="RECONSTRUCTABLE_ONLY", "NEXUS location overclaim")
    rejected=nexus.get("rejected_locator")
    _req(isinstance(rejected,dict) and rejected.get("commit")==NEXUS_REJECTED_COMMIT and rejected.get("git_blob")==NEXUS_REJECTED_BLOB and rejected.get("observed_size")==NEXUS_REJECTED_SIZE and rejected.get("negative_evidence_digest")==NEGATIVE, "NEXUS rejected locator evidence drifted")
    _req(nexus.get("runtime_spec_digest")==ARTIFACTS["nexus"][1], "NEXUS runtime binding drifted")
    _req(synet.get("artifact_digest")==ARTIFACTS["synergynet"][0] and synet.get("artifact_size")==12837, "SynergyNet artifact identity drifted")
    _req(synet.get("build_input_digest")=="c9945102a36d1191d6bd15737e7834ae8d9a3ec66979b318cae503906b359608", "SynergyNet deterministic build input drifted")
    _req(synet.get("locator_status")=="NO_VERIFIED_DURABLE_BINARY_LOCATION" and synet.get("availability_status")=="RECONSTRUCTABLE_ONLY", "SynergyNet location overclaim")
    _req(registry.get("registry_status")=="NO_VERIFIED_DURABLE_BINARY_LOCATIONS" and registry.get("blockers")==REGISTRY_BLOCKERS, "corrected registry blockers/status drifted")
    _req(registry.get("execution_authority")=="NONE", "registry authority escalation")
    return registry


def verify_deployment_plan_v2(plan, registry):
    verify_artifact_registry_v2(registry)
    _req(plan.get("schema")=="synergy.meta-os-deployment-plan/v2", "wrong corrected deployment schema")
    require_digest(plan,"deployment_digest",DEPLOYMENT_V2)
    _req(plan.get("previous_deployment_digest")==DEPLOYMENT_V1 and plan.get("admission_digest")==ADMISSION and plan.get("artifact_registry_digest")==REGISTRY_V2, "deployment ancestry/root drifted")
    _req(plan.get("host_binding_status")=="HOST_UNBOUND" and plan.get("host_profile_digest") is None, "deployment cannot invent host")
    processes=plan.get("processes")
    _req(isinstance(processes,list) and [x.get("service_id") for x in processes]==["nexus","content-cache","synergynet"], "deployment process set drifted")
    expected={
      "nexus":(ARTIFACTS["nexus"][0],ARTIFACTS["nexus"][1],[],"NO_NETWORK"),
      "content-cache":(ARTIFACTS["content-cache"][0],ARTIFACTS["content-cache"][1],["store_path","listen_host","listen_port"],"OPERATOR_LOCAL_BIND_ONLY"),
      "synergynet":(ARTIFACTS["synergynet"][0],ARTIFACTS["synergynet"][1],["peer_directory","listen_host","listen_port"],"STATIC_OPERATOR_LOCAL_ALLOWLIST_ONLY"),
    }
    for p in processes:
        sid=p["service_id"]; e=expected[sid]
        _req((p.get("artifact_digest"),p.get("runtime_spec_digest"),p.get("operator_binding_required"),p.get("network_policy"))==e, f"{sid} binding drifted")
        _req(p.get("artifact_location_status")=="RECONSTRUCTABLE_ONLY" and p.get("planned_state")=="NOT_STARTED", f"{sid} location/state overclaim")
    _req(plan.get("supervisor_status")=="NOT_MATERIALIZED" and plan.get("deployment_evidence_status")=="NOT_EXECUTED", "supervisor/evidence overclaim")
    _req(plan.get("blockers")==DEPLOYMENT_BLOCKERS and plan.get("deployment_status")=="BLOCKED_NOT_LAUNCHABLE", "corrected deployment blockers/status drifted")
    _req(plan.get("running") is False and plan.get("auto_start") is False, "deployment cannot start node")
    _req(plan.get("execution_authority")=="NONE" and plan.get("financial_authority")=="NONE", "deployment authority escalation")
    return plan
