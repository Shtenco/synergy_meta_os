from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
import pytest
from synergy_meta_os.autopilot_ai_node_production_gate_v1 import ProductionGateError,verify_production_gate
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'gates/synergy_autopilot_v5_ai_node_production_transition_gate_v1.json'
def load(): return json.loads(P.read_text())
def fresh(v):
 b=dict(v);b.pop('gate_digest',None);v['gate_digest']=hashlib.sha256(json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();return v
def test_gate_is_blocked_and_lab_not_current():
 g=verify_production_gate(load());assert g['production_status']=='BLOCKED_NOT_DEPLOYED';assert g['current_running'] is False
@pytest.mark.parametrize('field,value',[
 ('current_running',True),('production_status','RUNNING'),('production_host_profile_digest','a'*64),('production_supervisor_config_digest','b'*64),('production_deployment_evidence_digest','c'*64),('production_deployment_result_digest','d'*64),('requirements',[]),('forbidden_reuse',[]),('nexus_network_access','FULL_EGRESS'),('auto_start',True),('financial_authority','TREASURY'),('blockchain_submission_authority','SIGN_AND_SUBMIT'),('node_execution_authority','ROOT')])
def test_fresh_hash_cannot_bypass_gate(field,value):
 g=copy.deepcopy(load());g[field]=value;fresh(g)
 with pytest.raises(ProductionGateError): verify_production_gate(g)
