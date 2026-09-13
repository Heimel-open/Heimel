import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parent.parent


class EngineeringEvidencePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(
            (ROOT / "config" / "engineering-evidence-policy.json").read_text(
                encoding="utf-8"
            )
        )

    def test_instruction_context_is_guidance_not_correctness_evidence(self):
        requirements = self.policy["requirements"]
        self.assertFalse(requirements["guidance_is_evidence"])
        self.assertFalse(requirements["instruction_compliance_attests_correctness"])
        self.assertIn("AGENTS.md", self.policy["guidance_classes"])
        self.assertIn("CLAUDE.md", self.policy["guidance_classes"])
        self.assertIn("executable_contract", self.policy["correctness_evidence_classes"])
        self.assertIn("deterministic_test", self.policy["correctness_evidence_classes"])
        self.assertIn("sha_bound_ci_result", self.policy["correctness_evidence_classes"])

    def test_self_attestation_cannot_replace_independent_verification(self):
        requirements = self.policy["requirements"]
        gate = self.policy["promotion_gate"]
        self.assertFalse(
            requirements["worker_self_attestation_satisfies_independent_verification"]
        )
        self.assertTrue(gate["requires_executable_evidence"])
        self.assertTrue(gate["requires_exact_sha_binding"])
        self.assertTrue(gate["independent_verification_when_required"])
        self.assertFalse(gate["instruction_compliance_alone_can_pass"])

    def test_verification_is_scope_bound_and_not_execution_authority(self):
        requirements = self.policy["requirements"]
        self.assertTrue(requirements["test_evidence_is_scope_bounded"])
        self.assertTrue(requirements["verification_gaps_must_remain_explicit"])
        self.assertFalse(requirements["technical_correctness_grants_execution_authority"])
        self.assertEqual(self.policy["authority_effect"], "none")

    def test_guidance_and_evidence_refs_are_separate_receipt_classes(self):
        separation = self.policy["receipt_separation"]
        self.assertEqual(separation["guidance_refs"], "workflow_context_only")
        self.assertEqual(separation["evidence_refs"], "verification_inputs_only")
        self.assertEqual(separation["verification_status"], "verified_scope_only")
        self.assertEqual(
            separation["verification_gaps"], "explicit_unknown_or_unverified_scope"
        )


if __name__ == "__main__":
    unittest.main()
