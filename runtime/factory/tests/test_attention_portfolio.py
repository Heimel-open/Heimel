import unittest

from lib.attention_portfolio import (
    AttentionPortfolioEngine,
    Decision,
    IdeaCandidate,
    OutcomeEvent,
    SelectionPolicy,
)


class AttentionPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.engine = AttentionPortfolioEngine(
            SelectionPolicy(
                min_observations=3,
                scale_gcu_per_cost=1.0,
                kill_gcu_per_cost=0.15,
                exploration_share=0.20,
            )
        )
        self.candidates = [
            IdeaCandidate("winner", "mission:attention", "format A converts", "instagram", 10),
            IdeaCandidate("loser", "mission:attention", "format B converts", "youtube", 10),
            IdeaCandidate("young", "mission:attention", "format C converts", "linkedin", 10),
        ]

    def test_scale_kill_and_keep_testing(self):
        outcomes = [
            OutcomeEvent("winner", 20, 10, 5, ("receipt:winner",)),
            OutcomeEvent("loser", 1, 10, 5, ("receipt:loser",)),
            OutcomeEvent("young", 100, 10, 1, ("receipt:young",)),
        ]
        plan = self.engine.plan(self.candidates, outcomes, budget=100)
        by_id = {item.idea_id: item for item in plan.decisions}

        self.assertIs(by_id["winner"].decision, Decision.SCALE)
        self.assertIs(by_id["loser"].decision, Decision.KILL)
        self.assertIs(by_id["young"].decision, Decision.KEEP_TESTING)
        self.assertGreater(by_id["winner"].allocation, by_id["young"].allocation)
        self.assertEqual(by_id["loser"].allocation, 0)
        self.assertFalse(plan.direct_effect_path)

    def test_killed_idea_requests_materially_new_direction_from_idebank(self):
        outcome = OutcomeEvent("loser", 0, 10, 4, ())
        plan = self.engine.plan(self.candidates, [outcome], budget=50)

        self.assertEqual(len(plan.feedback_to_idebank), 1)
        request = plan.feedback_to_idebank[0]
        self.assertEqual(request["type"], "new_direction_request")
        self.assertEqual(request["idea_id"], "loser")
        self.assertIn("materially different", request["instruction"])

    def test_positive_gcu_requires_evidence(self):
        with self.assertRaisesRegex(ValueError, "requires outcome evidence"):
            OutcomeEvent("winner", 5, 1, 4)

    def test_deterministic_allocation(self):
        outcomes = [
            OutcomeEvent("winner", 20, 10, 5, ("receipt:winner",)),
            OutcomeEvent("young", 4, 10, 5, ("receipt:young",)),
        ]
        first = self.engine.plan(self.candidates, outcomes, budget=100)
        second = self.engine.plan(self.candidates, outcomes, budget=100)
        self.assertEqual(first, second)

    def test_budget_is_allocation_only_not_direct_spend(self):
        outcome = OutcomeEvent("winner", 20, 10, 5, ("receipt:winner",))
        plan = self.engine.plan(self.candidates, [outcome], budget=100)
        self.assertFalse(plan.direct_effect_path)
        self.assertAlmostEqual(plan.decisions[0].allocation, 80.0)
        self.assertAlmostEqual(plan.unallocated_budget, 20.0)


if __name__ == "__main__":
    unittest.main()
