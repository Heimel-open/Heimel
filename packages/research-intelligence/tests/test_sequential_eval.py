import unittest

from heimel_research_intelligence.sequential_eval import (
    SequentialEvaluationError,
    bounded_append,
    compare_reruns,
    run_sequential_evaluation,
)


class SequentialEvaluationTests(unittest.TestCase):
    def test_exposure_is_strictly_sequential_and_memory_is_bounded(self):
        seen = []

        def observer(exposure, memory):
            seen.append((exposure.index, exposure.content, memory))
            return exposure.content.upper()

        result = run_sequential_evaluation(
            ["one", "two", "three"],
            observer=observer,
            memory_reducer=bounded_append(2),
        )

        self.assertEqual([item[0] for item in seen], [0, 1, 2])
        self.assertEqual(result.memory, ("TWO", "THREE"))
        self.assertEqual(seen[2][2], ("ONE", "TWO"))

    def test_stop_is_irreversible_for_remaining_passages(self):
        seen = []

        def observer(exposure, memory):
            seen.append(exposure.index)
            return exposure.content

        result = run_sequential_evaluation(
            ["continue", "DROP", "must-not-be-seen"],
            observer=observer,
            memory_reducer=bounded_append(4),
            stop_rule=lambda exposure, response, memory: response == "DROP",
        )

        self.assertEqual(seen, [0, 1])
        self.assertEqual(result.stopped_at, 1)
        self.assertEqual(len(result.observations), 2)

    def test_recall_probe_receives_only_derived_memory(self):
        recall_inputs = []

        def recall(memory):
            recall_inputs.append(memory)
            return "|".join(memory)

        result = run_sequential_evaluation(
            ["secret-source-a", "secret-source-b"],
            observer=lambda exposure, memory: f"note-{exposure.index}",
            memory_reducer=bounded_append(8),
            recall_probe=recall,
        )

        self.assertEqual(recall_inputs, [("note-0", "note-1")])
        self.assertEqual(result.recall, "note-0|note-1")
        self.assertNotIn("secret-source", result.recall)

    def test_trace_binds_exact_exposures_and_derived_state(self):
        run_a = run_sequential_evaluation(
            ["a", "b"],
            observer=lambda exposure, memory: exposure.content,
            memory_reducer=bounded_append(2),
        )
        run_b = run_sequential_evaluation(
            ["a", "changed"],
            observer=lambda exposure, memory: exposure.content,
            memory_reducer=bounded_append(2),
        )
        self.assertNotEqual(run_a.trace_sha256, run_b.trace_sha256)
        self.assertNotEqual(
            run_a.observations[1].exposure_sha256,
            run_b.observations[1].exposure_sha256,
        )

    def test_rerun_comparison_reports_stability_without_overclaiming(self):
        def run_once():
            return run_sequential_evaluation(
                ["a", "b"],
                observer=lambda exposure, memory: exposure.content.upper(),
                memory_reducer=bounded_append(2),
                recall_probe=lambda memory: ",".join(memory),
            )

        comparison = compare_reruns([run_once(), run_once()])
        self.assertTrue(comparison["trace_stable"])
        self.assertTrue(comparison["recall_stable"])
        self.assertEqual(comparison["runs"], 2)

    def test_invalid_memory_bound_fails_closed(self):
        with self.assertRaises(SequentialEvaluationError):
            bounded_append(-1)


if __name__ == "__main__":
    unittest.main()
