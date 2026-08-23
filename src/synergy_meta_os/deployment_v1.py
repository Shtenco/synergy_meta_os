from __future__ import annotations

from .admission_v1 import AdmissionV1Error, ARTIFACTS, ADMISSION, canonical, digest, require_digest


class DeploymentV1Error(ValueError):
    pass

REGISTRY="8ecec30555e8a2a7930549b2e67583c2ea1fb90a422e6ed6523a5d8e01ff2d49"
DEPLOYMENT="dd66bef640aba79aa9055c590e6126c541b59f9f909ee033fc7b1982c4505c14"
NEXUS_COMMIT="a47840e6c76b3eefcc5b0053317f5219682e9ee1"
NEXUS_BLOB="bb541be8b71ebad5977b3849e66e10224f0e1ded"
NEXUS_PATH="artifacts/fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64.pyz"
REGISTRY_BLOCKERS=["SYNERGYNET_ARTIFACT_LOCATION_NOT_DURABLE"]
DEPLOYMENT_BLOCKERS=["SYNERGYNET_ARTIFACT_LOCATION_NOT_DURABLE","HOST_PROFILE_NOT_BOUND","SUPERVISOR_CONFIG_NOT_MATERIALIZED","DEPLOYMENT_EVIDENCE_NOT_EXECUTED"]


def _req(cond: bool, message: str) -> None:
    if not cond:
        raise DeploymentV1Error(message)


def verify_artifact_registry_v1(registry):
    _req(registry.get("schema")=="synergy.meta-os-artifact-registry/v1", "wrong registry schema")
    _req(registry.get("subject")=="RESEARCH_COMPUTE_NODE" and registry.get("admission_digest")==ADMISSION, "registry admission drifted")
    require_digest(registry,"registry_digest",REGISTRY)
    entries=registry.get("entries")
    _req(isinstance(entries,list) and [x.get("artifact_id") for x in entries]==["nexus","synergynet"], "registry entry set drifted")
    nexus,synet=entries
    _req(nexus.get("artifact_digest")==ARTIFACTS["nexus"][0] and nexus.get("artifact_size")==56967, "NEXUS artifact identity drifted")
    _req(nexus.get("repository")=="Shtenco/agi_nexus" and nexus.get("repository_commit")==NEXUS_COMMIT and nexus.get("repository_path")==NEXUS_PATH and nexus.get("git_blob")==NEXUS_BLOB, "NEXUS durable locator drifted")
    _req(nexus.get("locator_status")=="DURABLE_GIT_TREE_PATH" and nexus.get("availability_status")=="RESOLVABLE", "NEXUS location overclaim")
    _req(nexus.get("runtime_spec_digest")==ARTIFACTS["nexus"][1], "NEXUS runtime binding drifted")
    _req(synet.get("artifact_digest")==ARTIFACTS["synergynet"][0] and synet.get("artifact_size")==12837 and synet.get("repository")=="Shtenco/synergynet", "SynergyNet artifact identity drifted")
    _req(synet.get("build_recipe_digest")=="37cb503fb8c6d5e8ef2305ce03d0332abee2d9eed5bb29f90364e20874d128df" and synet.get("build_evidence_digest")=="8c4f44f1b0b95221d660bb4a7c0598ada17e86f59bade16e85d93789bf1ddd8c", "SynergyNet reconstruction evidence drifted")
    _req(synet.get("locator_status")=="NO_DURABLE_BINARY_LOCATION" and synet.get("availability_status")=="RECONSTRUCTABLE_ONLY", "SynergyNet locator overclaim")
    _req(synet.get("runtime_spec_digests")=={"content-cache":ARTIFACTS["content-cache"][1],"synergynet":ARTIFACTS["synergynet"][1]}, "SynergyNet role binding drifted")
    _req(registry.get("registry_status")=="PARTIAL_LOCATION_COVERAGE" and registry.get("blockers")==REGISTRY_BLOCKERS, "registry blockers/status drifted")
    _req(registry.get("execution_authority")=="NONE", "registry authority escalation")
    return registry


def verify_deployment_plan_v1(plan, registry):
    verify_artifact_registry_v1(registry)
    _req(plan.get("schema")=="synergy.meta-os-deployment-plan/v1" and plan.get("subject")=="RESEARCH_COMPUTE_NODE", "deployment identity drifted")
    require_digest(plan,"deployment_digest",DEPLOYMENT)
    _req(plan.get("admission_digest")==ADMISSION and plan.get("artifact_registry_digest")==REGISTRY, "deployment root binding drifted")
    _req(plan.get("host_binding_status")=="HOST_UNBOUND" and plan.get("host_profile_digest") is None, "deployment cannot invent host binding")
    processes=plan.get("processes")
    _req(isinstance(processes,list) and [x.get("service_id") for x in processes]==["nexus","content-cache","synergynet"], "deployment process set drifted")
    expected={
      "nexus":(ARTIFACTS["nexus"][0],ARTIFACTS["nexus"][1],"RESOLVABLE",[],"NO_NETWORK"),
      "content-cache":(ARTIFACTS["content-cache"][0],ARTIFACTS["content-cache"][1],"RECONSTRUCTABLE_ONLY",["store_path","listen_host","listen_port"],"OPERATOR_LOCAL_BIND_ONLY"),
      "synergynet":(ARTIFACTS["synergynet"][0],ARTIFACTS["synergynet"][1],"RECONSTRUCTABLE_ONLY",["peer_directory","listen_host","listen_port"],"STATIC_OPERATOR_LOCAL_ALLOWLIST_ONLY"),
    }
    for p in processes:
        sid=p["service_id"]; e=expected[sid]
        _req((p.get("artifact_digest"),p.get("runtime_spec_digest"),p.get("artifact_location_status"),p.get("operator_binding_required"),p.get("network_policy"))==e, f"{sid} deployment binding drifted")
        _req(p.get("planned_state")=="NOT_STARTED", f"{sid} cannot be marked started")
    _req(plan.get("supervisor_status")=="NOT_MATERIALIZED" and plan.get("deployment_evidence_status")=="NOT_EXECUTED", "deployment evidence/supervisor overclaim")
    _req(plan.get("blockers")==DEPLOYMENT_BLOCKERS and plan.get("deployment_status")=="BLOCKED_NOT_LAUNCHABLE", "deployment blockers/status drifted")
    _req(plan.get("running") is False and plan.get("auto_start") is False, "deployment cannot start node")
    _req(plan.get("execution_authority")=="NONE" and plan.get("financial_authority")=="NONE", "deployment authority escalation")
    return plan
