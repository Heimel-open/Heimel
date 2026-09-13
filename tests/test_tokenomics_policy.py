import importlib.machinery
import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parent.parent / "bin" / "valo-run"
SPEC = importlib.util.spec_from_file_location(
    "valo_run",
    MODULE_PATH,
    loader=importlib.machinery.SourceFileLoader("valo_run", str(MODULE_PATH)),
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class TokenomicsPolicyTests(unittest.TestCase):
    def test_canonical_policy_contains_all_eleven_rules(self):
        policy, path = mod._load_tokenomics_policy()
        self.assertTrue(path.exists())
        self.assertEqual(policy["status"], "canonical")
        self.assertEqual(len(policy["rules"]), 11)
        self.assertEqual(
            policy["principle"],
            "Context is a budgeted runtime resource.",
        )
        self.assertIn("human_attention", policy["cost_of_cognition"])
        self.assertIn("error_rework", policy["cost_of_cognition"])
        self.assertIn("opportunity_cost", policy["cost_of_cognition"])
        self.assertIn("technical_debt", policy["cost_of_cognition"])
        self.assertIn("time_saved", policy["value_of_cognition"])
        self.assertIn("verified_business_outcome", policy["value_of_cognition"])
        self.assertTrue(policy["economic_observability"]["bind_cost_to_verified_outcome"])

    def test_worker_run_materializes_explicit_work_budget(self):
        policy, policy_path = mod._load_tokenomics_policy()
        with tempfile.TemporaryDirectory() as tmp:
            args = types.SimpleNamespace(issue="45")
            path = mod._write_work_budget(
                tmp,
                args,
                "run-abc123",
                "a" * 40,
                "adopt/ai-tokenomics-work-contract",
                policy,
                policy_path,
            )
            budget = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(budget["schema"], "valo.work-budget.v1")
        self.assertEqual(budget["context"]["scope"], ["issue:45"])
        self.assertEqual(budget["context"]["retrieval"], "targeted_only")
        self.assertEqual(budget["controls"]["max_same_correction_count"], 2)
        self.assertEqual(budget["controls"]["max_retry_cycles"], 3)
        self.assertEqual(budget["controls"]["stuck_action"], "revert_or_restart")
        self.assertTrue(budget["controls"]["session_reset_on_goal_change"])
        self.assertIn("tokens", budget["cost_of_cognition"])
        self.assertIn("verification", budget["cost_of_cognition"])
        self.assertIn("cancelled_opportunity_cost", budget["cost_of_cognition"])
        self.assertIn("enabled_opportunity_value", budget["value_of_cognition"])
        self.assertTrue(budget["economic_observability"]["measure_positive_time_value"])


if __name__ == "__main__":
    unittest.main()
