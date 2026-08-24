import copy, hashlib, json, unittest
from pathlib import Path
from synergy_meta_os.production_bootstrap_v5 import verify_contract, assess, ProductionBootstrapV5Error, canonical, LAB_ROOTS

ROOT = Path(__file__).resolve().parents[1]

class ProductionBootstrapV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT/"production"/"autopilot_v5_ai_node_production_bootstrap_contract_v5.json").read_text(encoding="utf-8"))

    def test_canonical(self):
        self.assertEqual(verify_contract(self.contract), "6ccecccc03189c6de934abf146cab87bb25b022551ba8d453cfefd4f5a3cdffd")

    def test_default_is_blocked(self):
        result = assess(self.contract)
        self.assertFalse(result["startup_allowed"])
        self.assertEqual(len(result["missing"]), 7)

    def test_all_fresh_roots_only_reach_review(self):
        supplied = {k: format(i+1, "064x") for i,k in enumerate(self.contract["required_inputs"])}
        result = assess(self.contract, supplied)
        self.assertEqual(result["status"], "READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED")
        self.assertFalse(result["startup_allowed"])

    def test_reject_lab_reuse(self):
        supplied = {k: format(i+1, "064x") for i,k in enumerate(self.contract["required_inputs"])}
        supplied["production_host_profile_digest"] = next(iter(LAB_ROOTS))
        with self.assertRaises(ProductionBootstrapV5Error): assess(self.contract, supplied)

    def test_reject_lineage_or_authority_promotion_even_with_fresh_hash(self):
        for field, value in (
            ("preproduction_rc5_digest", "0"*64),
            ("deployment_reference_v2_digest", "0"*64),
            ("ai_blockchain_preproduction_commitment_v3_digest", "0"*64),
            ("current_running", True), ("auto_start", True), ("startup_allowed", True),
            ("nexus_network_access", "FULL"), ("financial_authority", "ROOT"),
            ("blockchain_submission_authority", "ROOT"), ("node_execution_authority", "ROOT"),
        ):
            c = copy.deepcopy(self.contract); c[field] = value
            p = dict(c); p.pop("bootstrap_contract_digest", None)
            c["bootstrap_contract_digest"] = hashlib.sha256(canonical(p)).hexdigest()
            with self.subTest(field=field), self.assertRaises(ProductionBootstrapV5Error): verify_contract(c)

if __name__ == "__main__": unittest.main()
