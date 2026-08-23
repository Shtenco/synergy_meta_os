import copy
import unittest

from synergy_meta_os.production_bootstrap_v4 import FORBIDDEN, assess, load_default, verify_contract


class ProductionBootstrapV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = load_default()

    def test_canonical_contract(self):
        self.assertEqual(
            verify_contract(copy.deepcopy(self.value)),
            "39d262d4d6b28ceba3f6ffacadebd79d023e214ba63db6dbef6f5a3ad15547c6",
        )

    def test_default_is_blocked_on_exactly_seven_fresh_inputs(self):
        result = assess(self.value)
        self.assertEqual(
            result["status"],
            "BLOCKED_AWAITING_REAL_PERSISTENT_PRODUCTION_HOST_AND_FRESH_DEPLOYMENT_EVIDENCE",
        )
        self.assertEqual(len(result["missing"]), 7)
        self.assertFalse(result["startup_allowed"])
        self.assertFalse(result["current_running"])

    def test_all_fresh_inputs_only_reach_governance_review(self):
        supplied = {
            key: f"{index + 1:064x}"
            for index, key in enumerate(self.value["required_inputs"])
        }
        result = assess(self.value, supplied)
        self.assertEqual(result["status"], "READY_FOR_GOVERNANCE_EVIDENCE_VERIFICATION_NOT_LAUNCHED")
        self.assertEqual(result["missing"], [])
        self.assertFalse(result["startup_allowed"])
        self.assertEqual(result["governance_status"], "REVIEW_REQUIRED")

    def test_reject_historical_lab_reuse(self):
        supplied = {
            key: f"{index + 1:064x}"
            for index, key in enumerate(self.value["required_inputs"])
        }
        supplied["production_host_profile_digest"] = next(iter(FORBIDDEN))
        with self.assertRaises(ValueError):
            assess(self.value, supplied)

    def test_reject_duplicate_production_roots(self):
        supplied = {
            key: f"{index + 1:064x}"
            for index, key in enumerate(self.value["required_inputs"])
        }
        keys = list(supplied)
        supplied[keys[1]] = supplied[keys[0]]
        with self.assertRaises(ValueError):
            assess(self.value, supplied)

    def test_reject_upstream_substitution(self):
        for field in (
            "preproduction_release_v4_digest",
            "federation_registry_v3_digest",
            "meta_os_profile_v3_digest",
            "meta_os_admission_v3_digest",
            "synergynet_location_evidence_v3_digest",
            "synergynet_transport_binding_v2_digest",
        ):
            candidate = copy.deepcopy(self.value)
            candidate[field] = "0" * 64
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_contract(candidate)

    def test_reject_running_or_authority_escalation(self):
        for field, value in (
            ("startup_allowed", True),
            ("current_running", True),
            ("auto_start", True),
            ("nexus_network_access", "FULL"),
            ("financial_authority", "ROOT"),
            ("payment_authority", "ROOT"),
            ("accounting_authority", "ROOT"),
            ("host_execution_authority", "ROOT"),
            ("blockchain_submission_authority", "ROOT"),
            ("node_execution_authority", "ROOT"),
        ):
            candidate = copy.deepcopy(self.value)
            candidate[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_contract(candidate)


if __name__ == "__main__":
    unittest.main()
