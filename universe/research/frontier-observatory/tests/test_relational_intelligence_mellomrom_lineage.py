import unittest

from experiments.relational_intelligence.mellomrom_lineage import (
    adjacency_signature,
    build_control_pack,
    content_chars,
    score_judgments,
)


class MellomromLineageTests(unittest.TestCase):
    def setUp(self):
        self.episodes = []
        for index in range(6):
            self.episodes.append(
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
                    "provenance": "raw",
                    "confidence": 1.0,
                }
            )

    def test_controls_preserve_episode_multiset_and_volume(self):
        pack = build_control_pack(self.episodes)
        conditions = pack["conditions"]
        intact = conditions["intact"]["episodes"]

        self.assertEqual(pack["status"], "CONTROL_PACK_READY")
        self.assertEqual(pack["episode_count"], 6)
        for name in ("shuffled", "endpoint_matched"):
            control = conditions[name]["episodes"]
            self.assertEqual(content_chars(control), content_chars(intact))
            self.assertEqual(control[0]["episode_id"], intact[0]["episode_id"])
            self.assertEqual(control[-1]["episode_id"], intact[-1]["episode_id"])
            self.assertCountEqual(
                [row["episode_id"] for row in control],
                [row["episode_id"] for row in intact],
            )

    def test_controls_change_lineage_adjacency(self):
        pack = build_control_pack(self.episodes)
        conditions = pack["conditions"]
        intact = conditions["intact"]["episodes"]
        for name in ("shuffled", "endpoint_matched"):
            self.assertNotEqual(
                adjacency_signature(intact),
                adjacency_signature(conditions[name]["episodes"]),
            )

    def test_scoring_requires_matched_tasks_and_reports_gain(self):
        judgments = []
        values = {
            "intact": (0.9, 0.8, 1.0),
            "shuffled": (0.5, 0.4, 0.6),
            "endpoint_matched": (0.6, 0.5, 0.5),
        }
        for condition, scores in values.items():
            for index, score in enumerate(scores):
                judgments.append(
                    {"condition": condition, "task_id": f"t{index}", "score": score}
                )

        result = score_judgments(judgments)
        self.assertAlmostEqual(result["condition_means"]["intact"], 0.9)
        self.assertAlmostEqual(result["history_gain"], 0.4)
        self.assertGreater(result["lineage_specificity"], 0.3)
        self.assertTrue(result["candidate_signature"])

    def test_duplicate_episode_ids_fail_closed(self):
        duplicated = list(self.episodes)
        duplicated[-1] = dict(duplicated[-1], episode_id="e0")
        with self.assertRaises(ValueError):
            build_control_pack(duplicated)


if __name__ == "__main__":
    unittest.main()
