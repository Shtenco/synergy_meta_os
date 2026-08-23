from __future__ import annotations
import hashlib,json
from typing import Any

PROFILE_DIGEST="6a84a2dd132823756c9f159b04584ac384dca9514316b3ff5c9f4ce06e1696d3"
ADMISSION_DIGEST="4d3502dba28745b8a734c082ca0260cbbfd4ead11a1396537434844df9987ee3"
TRANSPORT_BINDING="3c8198e10863c52c0492ca422c404a1e05e6fd2f48f4c393587d9d87eee3855f"
EXPECTED_BLOCKERS=["HOST_PROFILE_NOT_BOUND","SUPERVISOR_CONFIG_NOT_MATERIALIZED","DEPLOYMENT_EVIDENCE_NOT_EXECUTED"]
class AdmissionV2Error(ValueError): pass

def digest(v:dict[str,Any],field:str)->str:
 b=dict(v);b.pop(field,None);return hashlib.sha256(json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def none_auth(v):
 for f in ("financial_authority","payment_authority","accounting_authority","host_execution_authority","blockchain_submission_authority","execution_authority"):
  if v.get(f)!="NONE": raise AdmissionV2Error(f)
def verify_profile_v2(v):
 if v.get("schema")!="synergy.meta-os-ai-node-profile/v2" or digest(v,"profile_digest")!=v.get("profile_digest") or v.get("profile_digest")!=PROFILE_DIGEST: raise AdmissionV2Error("profile")
 if v.get("transport_binding_digest")!=TRANSPORT_BINDING or v.get("transport_status")!="PROTOCOL_BOUND_HOST_ADDRESS_NOT_MATERIALIZED": raise AdmissionV2Error("transport")
 if v.get("transport_scope")!="OUTER_AUTOPILOT_NODE_ONLY" or v.get("nexus_network_access")!="NONE": raise AdmissionV2Error("scope")
 if v.get("host_profile_status")!="UNBOUND" or v.get("supervisor_status")!="NOT_MATERIALIZED": raise AdmissionV2Error("host")
 if v.get("running") is not False or v.get("auto_start") is not False: raise AdmissionV2Error("runtime")
 none_auth(v);return v
def verify_admission_v2(profile,admission):
 verify_profile_v2(profile)
 if admission.get("schema")!="synergy.meta-os-ai-node-admission/v2" or digest(admission,"admission_digest")!=admission.get("admission_digest") or admission.get("admission_digest")!=ADMISSION_DIGEST: raise AdmissionV2Error("admission")
 if admission.get("profile_digest")!=profile["profile_digest"] or admission.get("transport_binding_digest")!=TRANSPORT_BINDING: raise AdmissionV2Error("binding")
 if admission.get("decision")!="ADMITTED_TRANSPORT_BOUND_NOT_LAUNCHABLE_NOT_RUNNING" or admission.get("blockers")!=EXPECTED_BLOCKERS: raise AdmissionV2Error("decision")
 if admission.get("running") is not False or admission.get("auto_start") is not False: raise AdmissionV2Error("runtime")
 none_auth(admission);return admission
