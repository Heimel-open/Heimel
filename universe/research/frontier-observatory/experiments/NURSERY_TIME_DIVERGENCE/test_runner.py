from __future__ import annotations

import unittest

import numpy as np

import runner


class NurseryTimeDivergenceTest(unittest.TestCase):
    def test_seed_is_byte_equivalent_across_clones(self) -> None:
        seed = runner.make_seed()
        a = seed.clone()
        b = seed.clone()
        self.assertTrue(np.array_equal(a.state, b.state))
        self.assertTrue(np.array_equal(a.memory, b.memory))
        self.assertTrue(np.array_equal(a.relations, b.relations))

    def test_histories_have_matched_transition_counts(self) -> None:
        hs = runner.histories()
        self.assertEqual({8}, {len(v) for v in hs.values()})

    def test_different_histories_create_measurable_divergence(self) -> None:
        seed = runner.make_seed()
        hs = runner.histories()
        agents = {name: runner.apply_history(seed, h) for name, h in hs.items()}
        distances = [x["composite_distance"] for x in runner.pairwise_metrics(agents)]
        self.assertTrue(any(d > 1e-8 for d in distances))

    def test_order_changes_terminal_state(self) -> None:
        seed = runner.make_seed()
        hs = runner.histories()
        b = runner.apply_history(seed, hs["B_variation"])
        d = runner.apply_history(seed, hs["D_reordered"])
        self.assertGreater(runner.composite_distance(b, d), 1e-8)

    def test_replay_is_exact_in_deterministic_runtime(self) -> None:
        seed = runner.make_seed()
        hs = runner.histories()
        original = runner.apply_history(seed, hs["B_variation"])
        replay = runner.replay_test(seed, hs["B_variation"], original)
        self.assertAlmostEqual(replay["state_distance"], 0.0, places=12)
        self.assertAlmostEqual(replay["relation_distance"], 0.0, places=12)
        self.assertAlmostEqual(replay["behavior_distance"], 0.0, places=12)

    def test_common_experience_is_history_conditioned(self) -> None:
        seed = runner.make_seed()
        hs = runner.histories()
        agents = {name: runner.apply_history(seed, h) for name, h in hs.items()}
        crossed = runner.crossover(agents)
        effects = [runner.composite_distance(agents[name], crossed[name]) for name in agents]
        self.assertGreater(max(effects) - min(effects), 1e-8)

    def test_ablation_changes_reference_trajectory(self) -> None:
        seed = runner.make_seed()
        h = runner.histories()["B_variation"]
        reference = runner.apply_history(seed, h)
        amap = runner.ablation_map(seed, h, reference)
        self.assertEqual(len(h), len(amap))
        self.assertTrue(any(x["final_composite_delta_vs_reference"] > 1e-8 for x in amap))


if __name__ == "__main__":
    unittest.main()
