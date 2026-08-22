from __future__ import annotations

import hashlib
import json
from typing import Any


class AdmissionV1Error(ValueError):
    pass

READINESS_COMMIT="c2ec96ef24a39d397f0903f5a7f5ef7e96e46865"
READINESS="ee20353d76d377f31f8054dae0c6463db4b3aae1a57b4ccfc2d7631e2251a95b"
PLAN="8f37d84645e78818b17c884e7c46d1ba680e79a53a2125faab64de42a290953f"
TOOLCHAIN="af92c9f1909ae3b64aaea78bdce2c6d05deb974ad242482b36e0c8ce820a2848"
ARTIFACT_SET="14a67cfbe75361a8ca2f3bd43befd3aef97eddc29d4d725bd83f289ed829bc77"
ADMISSION="4ace5623bc0a3100e2502132056f76821eda930199eb74498cc1cbe4f4008e37"
ARTIFACTS={
 "content-cache":("7f22e68d80a7df879af71ebccdb45f8edb10cae3698bf07faa7076ce76fd0ef7","abb35edd0336ea36f249d24b04e1b7482fea4ecebc5c881b655bf8a390d8b5ad"),
 "nexus":("fa7bbd141566d1542a5c03ee485de8ebd5f2ed76557ac56ff728196429fbbb64","376f6a85fb1ddb2abe529559b73964241fb3f25a2a8832657eb0f19a1ecc6738"),
 "synergynet":("7f22e68d80a7df879af71ebccdb45f8edb10cae3698bf07faa7076ce76fd0ef7","8c38cd130e3dd73723e3a3241d2df61bef218abdab2d16785ccec5b172fac4df"),
}


def canonical(value:Any)->bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

def digest(payload:dict[str,Any],field:str)->str:
    body=dict(payload); body.pop(field,None); return hashlib.sha256(canonical(body)).hexdigest()

def require_digest(payload,field,expected):
    if payload.get(field)!=expected or digest(payload,field)!=expected: raise AdmissionV1Error(f"{field} mismatch")

def artifact_set_from_services(services):
    if not isinstance(services,list) or [x.get("service_id") for x in services] != ["content-cache","nexus","synergynet"]:
        raise AdmissionV1Error("service set drifted")
    mapping={}
    for item in services:
        sid=item["service_id"]; expected=ARTIFACTS[sid]
        if item.get("artifact_digest")!=expected[0] or item.get("artifact_runtime_spec_digest")!=expected[1]:
            raise AdmissionV1Error(f"{sid} artifact binding drifted")
        if item.get("artifact_status")!="VERIFIED_EXECUTABLE" or item.get("reproducibility_status")!="REPRODUCIBLE_BYTE_IDENTICAL" or item.get("execution_authority")!="NONE":
            raise AdmissionV1Error(f"{sid} artifact state drifted")
        mapping[sid]=item["artifact_digest"]
    return hashlib.sha256(canonical(mapping)).hexdigest()

def verify_build_plan_v4(plan):
    if plan.get("schema")!="synergy.node-build-plan/v4": raise AdmissionV1Error("wrong build plan schema")
    require_digest(plan,"plan_digest",PLAN)
    if plan.get("toolchain_lock_digest")!=TOOLCHAIN or plan.get("build_blockers")!=[] or plan.get("plan_status")!="BUILD_ARTIFACTS_VERIFIED_REPRODUCIBLE" or plan.get("execution_authority")!="NONE":
        raise AdmissionV1Error("build plan is not admission eligible")
    aset=artifact_set_from_services(plan.get("services"))
    if aset!=ARTIFACT_SET or plan.get("artifact_set_digest")!=ARTIFACT_SET: raise AdmissionV1Error("artifact set drifted")
    return plan

def verify_readiness_v4(readiness,plan):
    verify_build_plan_v4(plan)
    if readiness.get("schema")!="synergy.node-readiness/v4": raise AdmissionV1Error("wrong readiness schema")
    require_digest(readiness,"readiness_digest",READINESS)
    if readiness.get("build_plan_digest")!=PLAN or readiness.get("toolchain_lock_digest")!=TOOLCHAIN or readiness.get("artifact_set_digest")!=ARTIFACT_SET:
        raise AdmissionV1Error("readiness evidence binding drifted")
    if readiness.get("blockers")!=[] or readiness.get("build_status")!="BUILD_ARTIFACTS_VERIFIED_REPRODUCIBLE" or readiness.get("service_status")!="ALL_REQUIRED_SERVICES_ARTIFACT_VERIFIED":
        raise AdmissionV1Error("readiness has unresolved evidence state")
    if readiness.get("node_status")!="NODE_ADMISSION_READY_NOT_RUNNING" or readiness.get("auto_start") is not False or readiness.get("execution_authority")!="NONE":
        raise AdmissionV1Error("readiness attempts to start/authorize node")
    return readiness

def verify_admission_v1(admission,readiness,plan):
    verify_readiness_v4(readiness,plan)
    if admission.get("schema")!="synergy.meta-os-admission/v1" or admission.get("subject")!="RESEARCH_COMPUTE_NODE": raise AdmissionV1Error("admission identity drifted")
    require_digest(admission,"admission_digest",ADMISSION)
    exact={"readiness_repository":"Shtenco/synergy_system","readiness_commit":READINESS_COMMIT,"readiness_digest":READINESS,"build_plan_digest":PLAN,"toolchain_lock_digest":TOOLCHAIN,"artifact_set_digest":ARTIFACT_SET}
    for k,v in exact.items():
        if admission.get(k)!=v: raise AdmissionV1Error(f"admission {k} drifted")
    arts=admission.get("artifacts")
    if not isinstance(arts,list) or [x.get("service_id") for x in arts] != ["content-cache","nexus","synergynet"]: raise AdmissionV1Error("admission artifact set drifted")
    for item in arts:
        if (item.get("artifact_digest"),item.get("runtime_spec_digest")) != ARTIFACTS[item["service_id"]]: raise AdmissionV1Error("admission artifact binding drifted")
    if admission.get("decision")!="ADMITTED_ARTIFACT_VERIFIED_NOT_RUNNING" or admission.get("admission_effect")!="REGISTRY_ELIGIBILITY_ONLY": raise AdmissionV1Error("admission effect drifted")
    if admission.get("running") is not False or admission.get("auto_start") is not False: raise AdmissionV1Error("admission cannot start node")
    if admission.get("execution_authority")!="NONE" or admission.get("financial_authority")!="NONE" or admission.get("network_authority_change")!="NONE": raise AdmissionV1Error("admission authority escalation")
    return admission
