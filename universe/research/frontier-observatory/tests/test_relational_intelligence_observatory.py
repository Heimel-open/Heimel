import unittest

from experiments.relational_intelligence.observatory import (
    bayes_optimal_accuracy,
    observe,
    synthetic_path_dependent_rows,
)


class RelationalIntelligenceObservatoryTests(unittest.TestCase):
    def setUp(self):
        self.rows = synthetic_path_dependent_rows(repeats=4)

    def test_single_nodes_do_not_determine_target(self):
        self.assertEqual(bayes_optimal_accuracy(self.rows, ("a",)), 0.5)
        self.assertEqual(bayes_optimal_accuracy(self.rows, ("b",)), 0.5)

    def test_current_snapshot_is_insufficient(self):
        self.assertEqual(bayes_optimal_accuracy(self.rows, ("a", "b")), 0.5)

    def test_relational_history_recovers_function(self):
        result = observe(self.rows)
        self.assertEqual(result.relational_history_accuracy, 1.0)
        self.assertGreaterEqual(result.synergy_gain, 0.5)

    def test_history_ablation_destroys_signature(self):
        result = observe(self.rows)
        self.assertLessEqual(result.shuffled_history_accuracy, 0.5)
        self.assertGreaterEqual(result.history_dependence, 0.5)

    def test_relation_rewiring_destroys_signature(self):
        result = observe(self.rows)
        self.assertLessEqual(result.rewired_relation_accuracy, 0.5)
        self.assertGreaterEqual(result.relation_specificity, 0.5)

    def test_candidate_signature_is_bounded_positive(self):
        self.assertTrue(observe(self.rows).candidate_signature())


if __name__ == "__main__":
    unittest.main()
