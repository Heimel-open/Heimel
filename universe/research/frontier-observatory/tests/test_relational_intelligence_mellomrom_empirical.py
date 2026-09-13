import unittest

from experiments.relational_intelligence.mellomrom_empirical import (
    build_empirical_control_pack,
    validate_raw_episodes,
)


class MellomromEmpiricalGateTests(unittest.TestCase):
    def _episodes(self, provenance="raw"):
        rows = []
        for index in range(4):
            rows.append(
                {
                    "episode_id": f"e{index}",
                    "chat_id": "035",
                    "timestamp": f"2026-08-23T10:0{index}:00Z",
                    "context_before": f"context {index}",
                    "assistant_output": f"output {index}",
                    "human_correction": f"correction {index}",
                    "assistant_repair": f"repair {index}",
                    "later_validation": f"validation {index}",
                    "error_labels": ["E02_REFERENCE_MISALIGNMENT"],
                    "lost_reference": f"reference {index}",
                    "correction_delta": f"delta {index}",
                    "ground_truth_type": "historical_reference",
                    "accepted_after_repair": "yes",
                    "recurs_later": "no",
                    "provenance": provenance,
                    "confidence": 1.0,
                }
            )
        return rows

    def test_raw_episodes_pass(self):
        episodes = self._episodes()
        validate_raw_episodes(episodes)
        pack = build_empirical_control_pack(episodes)
        self.assertEqual(pack["evidence_class"], "RAW_EMPIRICAL_SOURCE")
        self.assertEqual(pack["empirical_gate"], "RAW_PROVENANCE_REQUIRED")

    def test_derived_analysis_fails_closed(self):
        episodes = self._episodes("derived")
        with self.assertRaises(ValueError):
            build_empirical_control_pack(episodes)

    def test_quoted_analysis_fails_closed(self):
        episodes = self._episodes("quoted_in_analysis")
        with self.assertRaises(ValueError):
            build_empirical_control_pack(episodes)

    def test_missing_raw_field_fails_closed(self):
        episodes = self._episodes()
        episodes[2]["human_correction"] = ""
        with self.assertRaises(ValueError):
            build_empirical_control_pack(episodes)


if __name__ == "__main__":
    unittest.main()
