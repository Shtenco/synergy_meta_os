from __future__ import annotations
import hashlib,json
from typing import Any
GATE="fd3f97c1422376ae507e7ec0ab1dcff529cba4ad9b5f6b1e9b7b62ef43d75b8c"
LAB_RESULT="011c3ce24cfd33dc99fbdea0ea2f5dcd344deefd927f57c1b9c1fa3e3eaa3833"
REQ=["NEW_PERSISTENT_PRODUCTION_HOST_PROFILE","NEW_PRODUCTION_SUPERVISOR_CONFIG","FRESH_ARTIFACT_RESOLUTION_AND_HASH_VERIFICATION","FRESH_PRODUCTION_HEALTH_AND_TRANSPORT_ROUNDTRIP","FRESH_PRODUCTION_DEPLOYMENT_EVIDENCE","FRESH_PRODUCTION_DEPLOYMENT_RESULT","EXPLICIT_GOVERNANCE_PROMOTION"]
FORBID=["LAB_PIDS_AS_PRODUCTION_PIDS","LAB_TIMESTAMPS_AS_PRODUCTION_TIMESTAMPS","LAB_HOST_PROFILE_AS_PRODUCTION_HOST_PROFILE","LAB_SUPERVISOR_AS_PRODUCTION_SUPERVISOR","LAB_DEPLOYMENT_EVIDENCE_AS_PRODUCTION_EVIDENCE"]
class ProductionGateError(ValueError): pass
def cd(v:dict[str,Any])->str:
 b=dict(v);b.pop('gate_digest',None);return hashlib.sha256(json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def verify_production_gate(v):
 if v.get('schema')!='synergy.meta-os-production-transition-gate/v1' or cd(v)!=v.get('gate_digest') or v.get('gate_digest')!=GATE: raise ProductionGateError('digest')
 if v.get('lab_deployment_result_digest')!=LAB_RESULT or v.get('lab_state')!='RUNNING_VERIFIED_THEN_STOPPED_GRACEFULLY' or v.get('current_running') is not False: raise ProductionGateError('lab state')
 if v.get('production_status')!='BLOCKED_NOT_DEPLOYED': raise ProductionGateError('production status')
 for f in ('production_host_profile_digest','production_supervisor_config_digest','production_deployment_evidence_digest','production_deployment_result_digest'):
  if v.get(f) is not None: raise ProductionGateError('invented production evidence')
 if v.get('requirements')!=REQ or v.get('forbidden_reuse')!=FORBID: raise ProductionGateError('gate policy')
 if v.get('nexus_network_access')!='NONE' or v.get('auto_start') is not False: raise ProductionGateError('runtime escalation')
 for f in ('financial_authority','payment_authority','accounting_authority','blockchain_submission_authority','node_execution_authority'):
  if v.get(f)!='NONE': raise ProductionGateError(f)
 return v
