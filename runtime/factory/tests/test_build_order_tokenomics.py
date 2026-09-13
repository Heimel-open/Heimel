"""Tests for AI tokenomics operating rules in BuildOrderV1 (#45)."""

import unittest

from lib.build_order_intake import normalize, validate


def _minimal():
    return {
        "build_order_id": "bo-1",
        "issued_at": "2026-08-08T00:00:00Z",
        "principal": "founder",
        "issued_via": "github",
        "authority_basis": "founder-mandate",
        "target_repo": "nsolland/valo-platform",
        "target_base_ref": "main",
        "objective": "build tokenomics",
        "owned_files": ["src/"],
        "acceptance_criteria": ["tests pass"],
        "requires_independent_qc": True,
        "requires_receipt": True,
        "idempotency_key": "k-1",
    }


class TokenomicsNormalizationTest(unittest.TestCase):
    def test_defaults_are_safe(self):
        bo = normalize(_minimal())
        t = bo.tokenomics
        self.assertEqual(t.max_input_tokens, 0)
        self.assertTrue(t.deterministic_tool_preference)
        self.assertTrue(t.analysis_execution_separation)
        self.assertTrue(t.clean_session_boundaries)
        self.assertTrue(t.track_costs)
        self.assertEqual(t.max_retries, 0)

    def test_explicit_context_budget(self):
        raw = _minimal()
        raw["tokenomics"] = {
            "context_budget": {"max_input_tokens": 4000, "max_output_tokens": 2000},
            "bounded_retries": {"max_retries": 2, "max_autonomy_steps": 5},
            "deterministic_tool_preference": True,
        }
        bo = normalize(raw)
        self.assertEqual(bo.tokenomics.max_input_tokens, 4000)
        self.assertEqual(bo.tokenomics.max_output_tokens, 2000)
        self.assertEqual(bo.tokenomics.max_retries, 2)
        self.assertEqual(bo.tokenomics.max_autonomy_steps, 5)

    def test_invalid_int_values_default_to_zero(self):
        raw = _minimal()
        raw["tokenomics"] = {"context_budget": {"max_input_tokens": "many"}}
        bo = normalize(raw)
        self.assertEqual(bo.tokenomics.max_input_tokens, 0)

    def test_analysis_execution_separation_cannot_be_disabled(self):
        raw = _minimal()
        raw["tokenomics"] = {"analysis_execution_separation": False}
        bo = normalize(raw)
        self.assertTrue(bo.tokenomics.analysis_execution_separation)

    def test_to_dict_roundtrip_contains_tokenomics(self):
        bo = normalize(_minimal())
        d = bo.to_dict()
        self.assertIn("tokenomics", d)
        self.assertIn("context_budget", d["tokenomics"])
        self.assertIn("bounded_retries", d["tokenomics"])

    def test_tokenomics_does_not_affect_authority(self):
        bo = normalize(_minimal())
        self.assertEqual(bo.authority_effect, "none")
        self.assertEqual(validate(bo), ())


if __name__ == "__main__":
    unittest.main()
