import copy,unittest
from synergy_meta_os.autopilot_ai_node_admission_v3 import load,verify_profile,verify_admission
class AdmissionV3Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.p,cls.a=load()
 def test_canonical(self):
  self.assertEqual(verify_profile(copy.deepcopy(self.p)),'96ea31f50ff61b478390d682e88cca89c806e88dbaef1c4fc53b109724ca8222')
  self.assertEqual(verify_admission(copy.deepcopy(self.a)),'b1c151d4d5095278006d338c65f3a56b4853c3b3aa70a429205bea84fc5770e8')
 def test_reject_old_transport(self):
  x=copy.deepcopy(self.a);x['transport_binding_digest']='3c8198e10863c52c0492ca422c404a1e05e6fd2f48f4c393587d9d87eee3855f'
  with self.assertRaises(ValueError): verify_admission(x)
 def test_reject_lab_as_production(self):
  x=copy.deepcopy(self.p);x['production_host_profile_status']='BOUND_FROM_LAB'
  with self.assertRaises(ValueError): verify_profile(x)
 def test_reject_blocker_erasure(self):
  x=copy.deepcopy(self.a);x['blockers']=[]
  with self.assertRaises(ValueError): verify_admission(x)
 def test_reject_authority(self):
  x=copy.deepcopy(self.a);x['execution_authority']='ROOT'
  with self.assertRaises(ValueError): verify_admission(x)
if __name__=='__main__':unittest.main()
