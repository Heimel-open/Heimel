import math
import unittest

from experiments.TS_Relational_Substrate.ts_relational_substrate import (
    RelationalState,
    ScheduleRun,
    add_relation,
    baseline_state,
    causal_trace,
    compute_rule_hash,
    geometry_distance,
    relational_time_to_target,
    remove_relation,
    run_ts1,
    run_ts4,
)


class RelationalSubstrateTests(unittest.TestCase):
    def test_baseline_two_projections_are_derived_from_same_geometry(self):
        state = baseline_state()
        self.assertEqual(relational_time_to_target(state, "A", "E"), 3.0)
        self.assertEqual(geometry_distance(state, "A", "E"), 3.0)

    def test_ts1_schedule_perturbation_preserves_causal_trace(self):
        result = run_ts1()
        self.assertTrue(result["same_causal_trace"])
        self.assertEqual(result["relational_alignment"], 1.0)
        self.assertLess(result["wall_clock_alignment"], 0.8)
        self.assertTrue(result["pass"])

    def test_ts4_bridge_removal_changes_both_projections(self):
        result = run_ts4()
        self.assertEqual(result["bridge_removed"]["delta_t_rel"], 1.0)
        self.assertEqual(result["bridge_removed"]["delta_space"], 1.0)
        self.assertTrue(result["coordinated_bridge_effect"])

    def test_ts4_irrelevant_relation_is_clean_negative_control(self):
        result = run_ts4()
        self.assertEqual(result["irrelevant_relation_control"]["delta_t_rel"], 0.0)
        self.assertEqual(result["irrelevant_relation_control"]["delta_space"], 0.0)
        self.assertTrue(result["clean_negative_control"])
        self.assertTrue(result["pass"])

    def test_local_compute_identity_does_not_change_under_geometry_intervention(self):
        state = baseline_state()
        altered = remove_relation(state, "B", "D")
        self.assertEqual(state.nodes, altered.nodes)
        self.assertEqual(compute_rule_hash(), run_ts4()["compute_rule_hash"])

    def test_unreachable_target_is_infinite_in_both_projections(self):
        state = RelationalState(
            nodes=("A", "B", "C"),
            edges=(("A", "B", 1.0),),
        )
        self.assertTrue(math.isinf(relational_time_to_target(state, "A", "C")))
        self.assertTrue(math.isinf(geometry_distance(state, "A", "C")))

    def test_schedule_requires_strictly_increasing_event_times(self):
        trace = causal_trace(baseline_state(), "A", "E")
        with self.assertRaises(ValueError):
            ScheduleRun(trace=trace, event_times=(0.0, 1.0, 1.0, 3.0))

    def test_duplicate_relations_are_rejected(self):
        state = baseline_state()
        with self.assertRaises(ValueError):
            add_relation(state, "B", "D")


if __name__ == "__main__":
    unittest.main()
