from __future__ import annotations
import hashlib,json
from typing import Any

HOST="36a9092977e360b56fd7d1e21b4504f1215ed741df6f492b3ed37b79649573bb"
SUP="74797e02e0bb32722bbfffb76af42bb00d495fb3a5c0ea4a5b48a4e1d4275879"
EVIDENCE="8e1b05dca7e349d57e1908dca717d2c1d451ca79adde5cfe539e9e46f83d052b"
RESULT="011c3ce24cfd33dc99fbdea0ea2f5dcd344deefd927f57c1b9c1fa3e3eaa3833"
TRANSPORT="3c8198e10863c52c0492ca422c404a1e05e6fd2f48f4c393587d9d87eee3855f"
PROD_BLOCKERS=["PERSISTENT_PRODUCTION_HOST_NOT_BOUND","PRODUCTION_SUPERVISOR_NOT_MATERIALIZED","PRODUCTION_DEPLOYMENT_EVIDENCE_NOT_EXECUTED"]
class LabDeploymentError(ValueError): pass

def cd(v:dict[str,Any],field:str)->str:
 b=dict(v);b.pop(field,None);return hashlib.sha256(json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def verify_host(v):
 if v.get('schema')!='synergy.meta-os-host-profile/v1' or cd(v,'host_profile_digest')!=v.get('host_profile_digest') or v.get('host_profile_digest')!=HOST: raise LabDeploymentError('host digest')
 if v.get('scope')!='EPHEMERAL_LAB_EXECUTION_ONLY_NOT_PRODUCTION' or v.get('network_scope')!='LOOPBACK_ONLY' or v.get('bind_host')!='127.0.0.1': raise LabDeploymentError('host scope')
 if v.get('privileged_execution') is not False or v.get('persistent_secrets') is not False or v.get('auto_start') is not False: raise LabDeploymentError('host escalation')
 for f in ('node_host_execution_authority','financial_authority','payment_authority','accounting_authority','blockchain_submission_authority','execution_authority'):
  if v.get(f)!='NONE': raise LabDeploymentError(f)
 return v
def verify_supervisor(v,host):
 verify_host(host)
 if v.get('schema')!='synergy.meta-os-supervisor-config/v1' or cd(v,'supervisor_config_digest')!=v.get('supervisor_config_digest') or v.get('supervisor_config_digest')!=SUP: raise LabDeploymentError('supervisor digest')
 if v.get('host_profile_digest')!=HOST or v.get('transport_binding_digest')!=TRANSPORT: raise LabDeploymentError('supervisor binding')
 if v.get('scope')!='EPHEMERAL_LAB_EXECUTION_ONLY_NOT_PRODUCTION' or v.get('nexus_network_access')!='NONE': raise LabDeploymentError('supervisor scope')
 if v.get('execution_authority')!='BOUNDED_LAB_SUPERVISOR_ONLY' or v.get('auto_restart') is not False or v.get('secrets')!='NONE': raise LabDeploymentError('supervisor escalation')
 ids=[x.get('id') for x in v.get('processes',[])];
 if ids!=['autopilot-node','content-a','content-b','synergynet-relay']: raise LabDeploymentError('process set')
 return v
def verify_evidence(v,host,supervisor):
 verify_supervisor(supervisor,host)
 if v.get('schema')!='synergy.meta-os-deployment-evidence/v1' or cd(v,'deployment_evidence_digest')!=v.get('deployment_evidence_digest') or v.get('deployment_evidence_digest')!=EVIDENCE: raise LabDeploymentError('evidence digest')
 if v.get('host_profile_digest')!=HOST or v.get('supervisor_config_digest')!=SUP or v.get('transport_binding_digest')!=TRANSPORT: raise LabDeploymentError('evidence binding')
 if v.get('claim_tier')!='LOCAL_EXECUTED_LAB_EVIDENCE_NOT_PRODUCTION' or v.get('all_health_checks_passed') is not True: raise LabDeploymentError('claim')
 snap=v.get('running_snapshot',{})
 if snap.get('status')!='RUNNING_VERIFIED' or not all(snap.get('alive',{}).values()): raise LabDeploymentError('running snapshot')
 if snap.get('autopilot_resident',{}).get('status')!='READY' or snap.get('autopilot_resident',{}).get('nexus_status')!='READY': raise LabDeploymentError('node health')
 for k in ('content_a_status','content_b_status','relay_status'):
  if snap.get(k,{}).get('status')!='READY' or snap.get(k,{}).get('execution_authority')!='NONE': raise LabDeploymentError(k)
 if snap.get('relay_roundtrip',{}).get('destination_verified') is not True: raise LabDeploymentError('relay')
 if v.get('final_state')!='STOPPED_AFTER_VERIFICATION' or any(code!=0 for code in v.get('exit_codes',{}).values()): raise LabDeploymentError('shutdown')
 if v.get('nexus_network_access')!='NONE' or v.get('financial_authority')!='NONE' or v.get('payment_authority')!='NONE' or v.get('accounting_authority')!='NONE' or v.get('blockchain_submission_authority')!='NONE': raise LabDeploymentError('authority')
 return v
def verify_result(v,evidence,host,supervisor):
 verify_evidence(evidence,host,supervisor)
 if v.get('schema')!='synergy.meta-os-ai-node-deployment-result/v1' or cd(v,'deployment_result_digest')!=v.get('deployment_result_digest') or v.get('deployment_result_digest')!=RESULT: raise LabDeploymentError('result digest')
 if v.get('host_profile_digest')!=HOST or v.get('supervisor_config_digest')!=SUP or v.get('deployment_evidence_digest')!=EVIDENCE: raise LabDeploymentError('result binding')
 if v.get('running_snapshot_status')!='RUNNING_VERIFIED' or v.get('final_state')!='STOPPED_AFTER_VERIFICATION' or v.get('current_running') is not False: raise LabDeploymentError('current state overclaim')
 if v.get('lab_blockers')!=[] or v.get('production_status')!='NOT_RUNNING_NO_PERSISTENT_PRODUCTION_HOST' or v.get('production_blockers')!=PROD_BLOCKERS: raise LabDeploymentError('production overclaim')
 if v.get('nexus_network_access')!='NONE' or v.get('node_execution_authority')!='NONE' or v.get('supervisor_execution_authority')!='BOUNDED_LAB_SUPERVISOR_ONLY': raise LabDeploymentError('result authority')
 return v
