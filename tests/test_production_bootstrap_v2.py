import copy
import json
import unittest
from pathlib import Path

from synergy_meta_os.production_bootstrap_v2 import (
    FORBIDDEN_REUSE,
    ProductionBootstrapV2Error,
    assess_inputs,
    verify_contract,
)

ROOT = Path(__file__).resolve().parents[1]


class ProductionBootstrapV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "production" / "autopilot_v5_ai_node_production_bootstrap_contract_v2.json").read_text(encoding="utf-8"))

    def fresh_inputs(self):
        alphabet = "123456789abcdef0"
        return {key: alphabet[index] * 64 for index, key in enumerate(self.contract["required_inputs"])}

    def test_canonical_contract(self):
        self.assertEqual(
            verify_contract(self.contract),
            "3e2f1eb8c34b3beba75157b88aedc13c354d4450b9c0ab611cd63bb51f4f9a8c",
        )

    def test_default_is_blocked_on_eight_inputs(self):
        result = assess_inputs(self.contract)
        self.assertEqual(result["status"], "BLOCKED_MISSING_NEW_LOCATOR_AND_FRESH_PRODUCTION_INPUTS")
        self.assertFalse(result["startup_allowed"])
        self.assertEqual(len(result["missing"]), 8)
        self.assertIn("new_synergynet_location_evidence_v3_digest", result["missing"])

    def test_all_fresh_roots_still_do_not_launch(self):
        result = assess_inputs(self.contract, self.fresh_inputs())
        self.assertEqual(result["status"], "READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED")
        self.assertFalse(result["startup_allowed"])
        self.assertFalse(result["current_running"])

    def test_old_location_evidence_cannot_be_reused_as_v3(self):
        supplied = self.fresh_inputs()
        supplied["new_synergynet_location_evidence_v3_digest"] = "c4102a8e668b79fc961a5f1767154154f4a600d320442770d74c7a006a5cee08"
        with self.assertRaises(ProductionBootstrapV2Error):
            assess_inputs(self.contract, supplied)

    def test_reject_any_forbidden_reuse(self):
        for old_root in FORBIDDEN_REUSE:
            supplied = self.fresh_inputs()
            supplied["production_deployment_evidence_digest"] = old_root
            with self.subTest(old_root=old_root):
                with self.assertRaises(ProductionBootstrapV2Error):
                    assess_inputs(self.contract, supplied)

    def test_reject_fresh_hash_promotion(self):
        for field, value in (
            ("current_running", True),
            ("auto_start", True),
            ("startup_allowed", True),
            ("nexus_network_access", "FULL"),
            ("financial_authority", "ROOT"),
            ("payment_authority", "ROOT"),
            ("accounting_authority", "ROOT"),
            ("blockchain_submission_authority", "ROOT"),
            ("node_execution_authority", "ROOT"),
        ):
            candidate = copy.deepcopy(self.contract)
            candidate[field] = value
            candidate["bootstrap_contract_digest"] = "0" * 64
            with self.subTest(field=field):
                with self.assertRaises(ProductionBootstrapV2Error):
                    verify_contract(candidate)


if __name__ == "__main__":
    unittest.main()
