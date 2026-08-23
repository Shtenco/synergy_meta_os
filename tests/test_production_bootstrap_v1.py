import copy
import json
import unittest
from pathlib import Path

from synergy_meta_os.production_bootstrap_v1 import (
    LAB_ROOTS,
    ProductionBootstrapError,
    assess_production_inputs,
    verify_contract,
)

ROOT = Path(__file__).resolve().parents[1]


class ProductionBootstrapV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "production" / "autopilot_v5_ai_node_production_bootstrap_contract_v1.json").read_text(encoding="utf-8"))

    def test_canonical_contract(self):
        self.assertEqual(
            verify_contract(self.contract),
            "605c6c953e998efb9585a88c1c8f1a022d7160e3448139c2b80a33e6b6cbabd3",
        )

    def test_missing_inputs_fail_closed(self):
        result = assess_production_inputs(self.contract)
        self.assertEqual(result["status"], "BLOCKED_MISSING_FRESH_PRODUCTION_INPUTS")
        self.assertFalse(result["startup_allowed"])
        self.assertEqual(len(result["missing"]), 7)

    def test_all_fresh_inputs_only_reach_governance_review(self):
        supplied = {key: str(index + 1) * 64 for index, key in enumerate(self.contract["required_inputs"])}
        result = assess_production_inputs(self.contract, supplied)
        self.assertEqual(result["status"], "READY_FOR_GOVERNANCE_REVIEW_NOT_LAUNCHED")
        self.assertFalse(result["startup_allowed"])
        self.assertEqual(result["governance_status"], "REVIEW_REQUIRED")

    def test_reject_lab_root_reuse(self):
        supplied = {key: str(index + 1) * 64 for index, key in enumerate(self.contract["required_inputs"])}
        supplied["production_host_profile_digest"] = next(iter(LAB_ROOTS))
        with self.assertRaises(ProductionBootstrapError):
            assess_production_inputs(self.contract, supplied)

    def test_reject_fresh_hash_promotion(self):
        for field, value in (
            ("current_running", True),
            ("auto_start", True),
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
                with self.assertRaises(ProductionBootstrapError):
                    verify_contract(candidate)


if __name__ == "__main__":
    unittest.main()
