from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
EXPECTED='00330d77273e5dd35ef7ba30cfe02a4cc4aef89522e374d1fb2ef833c318aa75'
REQUIRED=('production_host_profile_digest','production_supervisor_config_digest','fresh_artifact_verification_digest','fresh_health_transport_roundtrip_digest','production_deployment_evidence_digest','production_deployment_result_digest','governance_promotion_digest')
FORBIDDEN={'36a9092977e360b56fd7d1e21b4504f1215ed741df6f492b3ed37b79649573bb','74797e02e0bb32722bbfffb76af42bb00d495fb3a5c0ea4a5b48a4e1d4275879','8e1b05dca7e349d57e1908dca717d2c1d451ca79adde5cfe539e9e46f83d052b','011c3ce24cfd33dc99fbdea0ea2f5dcd344deefd927f57c1b9c1fa3e3eaa3833'}

def canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def verify_contract(v):
 p=dict(v); claimed=p.pop('bootstrap_contract_digest',None); actual=hashlib.sha256(canonical(p)).hexdigest()
 if claimed!=EXPECTED or actual!=EXPECTED: raise ValueError('bootstrap digest mismatch')
 if p.get('preproduction_release_v3_digest')!='be8ca90e514e72ddccdc67a38cdd9b8321c2b55eb17ba6f04a9c65dbd4a16129': raise ValueError('RC3 substitution')
 if p.get('synergynet_location_evidence_v3_digest')!='b1ca1c1f5849deac30a0aac14748c21b8a74a26776ba2134a448c9427a839220': raise ValueError('locator substitution')
 if p.get('synergynet_location_status')!='DURABLE_GITHUB_GIT_CARRIER_CURRENTLY_RESOLVABLE': raise ValueError('locator status substitution')
 if p.get('nexus_network_access')!='NONE' or p.get('startup_allowed') is not False or p.get('current_running') is not False or p.get('auto_start') is not False: raise ValueError('execution boundary escalation')
 for k in ('financial_authority','payment_authority','accounting_authority','blockchain_submission_authority','node_execution_authority'):
  if p.get(k)!='NONE': raise ValueError('authority escalation')
 if tuple(p.get('required_inputs',{}).keys())!=REQUIRED: raise ValueError('required input shape drift')
 return actual

def assess(v,supplied=None):
 verify_contract(v); supplied=dict(supplied or {}); vals={k:supplied.get(k,v['required_inputs'][k]) for k in REQUIRED}
 for k,x in vals.items():
  if x is not None:
   if not isinstance(x,str) or len(x)!=64 or any(c not in '0123456789abcdef' for c in x): raise ValueError(f'invalid digest {k}')
   if x in FORBIDDEN: raise ValueError(f'LAB reuse forbidden {k}')
 present=[x for x in vals.values() if x]
 if len(present)!=len(set(present)): raise ValueError('duplicate production roots')
 missing=[k for k,x in vals.items() if not x]
 if missing:return {'status':'BLOCKED_MISSING_FRESH_PRODUCTION_INPUTS','missing':missing,'startup_allowed':False,'current_running':False,'governance_status':'NOT_AUTHORIZED','execution_authority':'NONE'}
 return {'status':'READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED','missing':[],'startup_allowed':False,'current_running':False,'governance_status':'REVIEW_REQUIRED','execution_authority':'NONE'}
def load_default(root=None):
 root=root or Path(__file__).resolve().parents[2]; return json.loads((root/'production'/'autopilot_v5_ai_node_production_bootstrap_contract_v3.json').read_text())
