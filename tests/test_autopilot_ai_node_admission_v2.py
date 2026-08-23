from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
import pytest
from synergy_meta_os.autopilot_ai_node_admission_v2 import AdmissionV2Error,verify_admission_v2
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'profiles/synergy_autopilot_v5_ai_node_profile_v2.json'
A=ROOT/'admissions/synergy_autopilot_v5_ai_node_admission_v2.json'
def load(p): return json.loads(p.read_text())
def fresh(v,f):
 b=dict(v);b.pop(f,None);v[f]=hashlib.sha256(json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();return v
def test_canonical_transport_bound_admission_passes(): assert verify_admission_v2(load(P),load(A))['blockers']==['HOST_PROFILE_NOT_BOUND','SUPERVISOR_CONFIG_NOT_MATERIALIZED','DEPLOYMENT_EVIDENCE_NOT_EXECUTED']
@pytest.mark.parametrize('target,field,value',[
 ('p','transport_binding_digest','0'*64),('p','transport_status','RUNNING'),('p','transport_scope','NEXUS_DIRECT_NETWORK'),('p','nexus_network_access','FULL_EGRESS'),('p','host_profile_status','BOUND'),('p','supervisor_status','MATERIALIZED'),('p','running',True),('p','financial_authority','TREASURY'),('a','blockers',['DEPLOYMENT_EVIDENCE_NOT_EXECUTED']),('a','decision','RUNNING'),('a','auto_start',True),('a','execution_authority','ROOT')])
def test_fresh_hash_cannot_overpromote(target,field,value):
 p,a=copy.deepcopy(load(P)),copy.deepcopy(load(A));(p if target=='p' else a)[field]=value;fresh(p,'profile_digest');a['profile_digest']=p['profile_digest'];fresh(a,'admission_digest')
 with pytest.raises(AdmissionV2Error): verify_admission_v2(p,a)
