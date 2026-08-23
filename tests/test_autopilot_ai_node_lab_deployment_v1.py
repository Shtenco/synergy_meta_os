from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
import pytest
from synergy_meta_os.autopilot_ai_node_lab_deployment_v1 import LabDeploymentError,verify_result
ROOT=Path(__file__).resolve().parents[1]
H=ROOT/'host_profiles/synergy_autopilot_v5_ai_node_lab_host_profile_v1.json'
S=ROOT/'supervisors/synergy_autopilot_v5_ai_node_lab_supervisor_v1.json'
E=ROOT/'evidence/synergy_autopilot_v5_ai_node_lab_deployment_evidence_v1.json'
R=ROOT/'deployments/synergy_autopilot_v5_ai_node_lab_deployment_result_v1.json'
def load(p): return json.loads(p.read_text())
def fresh(v,f):
 b=dict(v);b.pop(f,None);v[f]=hashlib.sha256(json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();return v
def test_executed_lab_deployment_passes_and_is_not_currently_running():
 r=verify_result(load(R),load(E),load(H),load(S));assert r['running_snapshot_status']=='RUNNING_VERIFIED';assert r['current_running'] is False
@pytest.mark.parametrize('which,field,value',[
 ('h','network_scope','PUBLIC_INTERNET'),('h','persistent_secrets',True),('h','financial_authority','TREASURY'),
 ('s','nexus_network_access','FULL_EGRESS'),('s','execution_authority','ROOT'),('s','auto_restart',True),
 ('e','claim_tier','PRODUCTION'),('e','all_health_checks_passed',False),('e','final_state','RUNNING'),('e','financial_authority','TREASURY'),
 ('r','current_running',True),('r','production_status','RUNNING'),('r','production_blockers',[]),('r','node_execution_authority','ROOT')])
def test_fresh_hash_cannot_turn_lab_evidence_into_production(which,field,value):
 h,s,e,r=map(copy.deepcopy,(load(H),load(S),load(E),load(R)))
 target={'h':h,'s':s,'e':e,'r':r}[which];target[field]=value
 fresh(h,'host_profile_digest');s['host_profile_digest']=h['host_profile_digest'];fresh(s,'supervisor_config_digest');e['host_profile_digest']=h['host_profile_digest'];e['supervisor_config_digest']=s['supervisor_config_digest'];fresh(e,'deployment_evidence_digest');r['host_profile_digest']=h['host_profile_digest'];r['supervisor_config_digest']=s['supervisor_config_digest'];r['deployment_evidence_digest']=e['deployment_evidence_digest'];fresh(r,'deployment_result_digest')
 with pytest.raises(LabDeploymentError): verify_result(r,e,h,s)
