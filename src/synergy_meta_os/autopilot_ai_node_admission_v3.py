from __future__ import annotations
import hashlib,json
from pathlib import Path
PROFILE_DIGEST='96ea31f50ff61b478390d682e88cca89c806e88dbaef1c4fc53b109724ca8222'
ADMISSION_DIGEST='b1c151d4d5095278006d338c65f3a56b4853c3b3aa70a429205bea84fc5770e8'
EXPECTED_BLOCKERS=['PRODUCTION_HOST_PROFILE_NOT_BOUND','PRODUCTION_SUPERVISOR_CONFIG_NOT_MATERIALIZED','PRODUCTION_DEPLOYMENT_EVIDENCE_NOT_EXECUTED']

def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def _verify(v,field,expected):
 p=dict(v); claimed=p.pop(field,None); actual=hashlib.sha256(canonical(p)).hexdigest()
 if claimed!=expected or actual!=expected: raise ValueError(f'{field} mismatch')
 return p

def verify_profile(v):
 p=_verify(v,'profile_digest',PROFILE_DIGEST)
 checks={
  'previous_profile_digest':'6a84a2dd132823756c9f159b04584ac384dca9514316b3ff5c9f4ce06e1696d3',
  'preproduction_release_v3_digest':'be8ca90e514e72ddccdc67a38cdd9b8321c2b55eb17ba6f04a9c65dbd4a16129',
  'production_bootstrap_v3_digest':'00330d77273e5dd35ef7ba30cfe02a4cc4aef89522e374d1fb2ef833c318aa75',
  'synergynet_location_evidence_v3_digest':'b1ca1c1f5849deac30a0aac14748c21b8a74a26776ba2134a448c9427a839220',
  'transport_binding_digest':'0c58185ea0af4a8abc7ce215c0b7ff077cea9357e831b9d197ec730a34ed6c7e',
  'nexus_network_access':'NONE',
  'production_host_profile_status':'UNBOUND',
  'production_supervisor_status':'NOT_MATERIALIZED',
  'production_deployment_evidence_status':'NOT_EXECUTED',
 }
 for k,x in checks.items():
  if p.get(k)!=x: raise ValueError(f'{k} substitution')
 if p.get('running') is not False or p.get('auto_start') is not False: raise ValueError('running escalation')
 for k in ('financial_authority','payment_authority','accounting_authority','host_execution_authority','blockchain_submission_authority','execution_authority'):
  if p.get(k)!='NONE': raise ValueError(f'authority escalation {k}')
 return PROFILE_DIGEST

def verify_admission(v):
 p=_verify(v,'admission_digest',ADMISSION_DIGEST)
 checks={
  'previous_admission_digest':'4d3502dba28745b8a734c082ca0260cbbfd4ead11a1396537434844df9987ee3',
  'profile_digest':PROFILE_DIGEST,
  'preproduction_release_v3_digest':'be8ca90e514e72ddccdc67a38cdd9b8321c2b55eb17ba6f04a9c65dbd4a16129',
  'production_bootstrap_v3_digest':'00330d77273e5dd35ef7ba30cfe02a4cc4aef89522e374d1fb2ef833c318aa75',
  'synergynet_location_evidence_v3_digest':'b1ca1c1f5849deac30a0aac14748c21b8a74a26776ba2134a448c9427a839220',
  'transport_binding_digest':'0c58185ea0af4a8abc7ce215c0b7ff077cea9357e831b9d197ec730a34ed6c7e',
  'decision':'ADMITTED_ARTIFACT_AND_TRANSPORT_RESOLVED_PRODUCTION_NOT_LAUNCHABLE_NOT_RUNNING',
  'admission_effect':'PRODUCTION_REGISTRY_ELIGIBILITY_ONLY',
 }
 for k,x in checks.items():
  if p.get(k)!=x: raise ValueError(f'{k} substitution')
 if p.get('blockers')!=EXPECTED_BLOCKERS: raise ValueError('production blocker drift')
 if p.get('running') is not False or p.get('auto_start') is not False: raise ValueError('running escalation')
 for k in ('financial_authority','payment_authority','accounting_authority','host_execution_authority','blockchain_submission_authority','execution_authority'):
  if p.get(k)!='NONE': raise ValueError(f'authority escalation {k}')
 return ADMISSION_DIGEST

def load(root=None):
 root=root or Path(__file__).resolve().parents[2]
 return json.loads((root/'profiles'/'synergy_autopilot_v5_ai_node_profile_v3.json').read_text()),json.loads((root/'admissions'/'synergy_autopilot_v5_ai_node_admission_v3.json').read_text())
