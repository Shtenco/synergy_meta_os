import copy,json,unittest
from pathlib import Path
from synergy_meta_os.production_bootstrap_v3 import assess,verify_contract,FORBIDDEN
ROOT=Path(__file__).resolve().parents[1]
class ProductionBootstrapV3Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.v=json.loads((ROOT/'production'/'autopilot_v5_ai_node_production_bootstrap_contract_v3.json').read_text())
 def test_canonical(self): self.assertEqual(verify_contract(copy.deepcopy(self.v)),'00330d77273e5dd35ef7ba30cfe02a4cc4aef89522e374d1fb2ef833c318aa75')
 def test_default_blocked_seven(self):
  r=assess(self.v); self.assertEqual(r['status'],'BLOCKED_MISSING_FRESH_PRODUCTION_INPUTS'); self.assertEqual(len(r['missing']),7); self.assertFalse(r['startup_allowed'])
 def test_fresh_inputs_only_reach_review(self):
  s={k:f'{i+1:064x}' for i,k in enumerate(self.v['required_inputs'])}; r=assess(self.v,s); self.assertEqual(r['status'],'READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED'); self.assertFalse(r['startup_allowed'])
 def test_reject_lab_reuse(self):
  s={k:f'{i+1:064x}' for i,k in enumerate(self.v['required_inputs'])}; s['production_host_profile_digest']=next(iter(FORBIDDEN))
  with self.assertRaises(ValueError): assess(self.v,s)
 def test_reject_locator_substitution(self):
  x=copy.deepcopy(self.v); x['synergynet_location_evidence_v3_digest']='0'*64
  with self.assertRaises(ValueError): verify_contract(x)
if __name__=='__main__':unittest.main()
