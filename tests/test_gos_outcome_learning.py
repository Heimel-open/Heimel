"""Tests for GOS-001F outcome learning (#26)."""

import unittest

from lib.gos_outcome_learning import (
    ConstitutionalChangeRequiresRatification,
    OutcomeLearningEngine,
    OutcomeRecord,
    ProposedChange,
    SilentProductionMutationBlocked,
)


def _outcome(**overrides) -> OutcomeRecord:
    data = {
        "outcome_id": "o-1",
        "action_ref": "act-1",
        "expected_value_minor": 1000,
        "realized_value_minor": 800,
        "expected_cost_minor": 100,
        "realized_cost_minor": 150,
        "clearance_record_id": "clr-1",
    }
    data.update(overrides)
    return OutcomeRecord(**data)


class OutcomeLearningTest(unittest.TestCase):
    def test_expected_vs_realized_value_traceable(self):
        o = _outcome()
        self.assertEqual(o.value_delta, -200)
        self.assertEqual(o.cost_delta, 50)

    def test_expected_vs_realized_cost_traceable(self):
        o = _outcome(realized_cost_minor=300)
        self.assertEqual(o.cost_delta, 200)

    def test_omission_outcome_measured(self):
        o = _outcome(omission=True)
        self.assertTrue(o.omission)
        self.assertEqual(o.regret, 200)

    def test_delay_outcome_measured(self):
        o = _outcome(delay=True)
        self.assertTrue(o.delay)

    def test_regret_calculated(self):
        o = _outcome(expected_value_minor=1000, realized_value_minor=400)
        self.assertEqual(o.regret, 600)
        # no regret when realized >= expected
        self.assertEqual(_outcome(realized_value_minor=1200).regret, 0)

    def test_variance_via_outcome_digests(self):
        engine = OutcomeLearningEngine()
        engine.record_outcome(_outcome(outcome_id="o-a"))
        engine.record_outcome(_outcome(outcome_id="o-b"))
        digests = engine.outcome_digests_for("clr-1")
        self.assertEqual(len(digests), 2)
        self.assertEqual(len(set(digests)), 2)

    def test_proposed_change_includes_evidence(self):
        p = ProposedChange("p-1", "weight", "shift", evidence_refs=("ev-1",))
        self.assertEqual(p.evidence_refs, ("ev-1",))

    def test_proposed_change_includes_counterfactual(self):
        p = ProposedChange("p-2", "threshold", "lower", counterfactuals=("cf-1",))
        self.assertEqual(p.counterfactuals, ("cf-1",))

    def test_learning_cannot_silently_mutate_profile(self):
        engine = OutcomeLearningEngine()
        engine.apply_profile("profile-a", "digest-1")
        with self.assertRaises(SilentProductionMutationBlocked):
            engine.mutate_active_profile("profile-a", "digest-2")

    def test_constitutional_change_requires_ratification(self):
        engine = OutcomeLearningEngine()
        with self.assertRaises(ConstitutionalChangeRequiresRatification):
            engine.propose_change(ProposedChange(
                "p-3", "constitutional", "change purpose", is_constitutional=True))

    def test_non_constitutional_proposal_allowed(self):
        engine = OutcomeLearningEngine()
        pid = engine.propose_change(ProposedChange("p-4", "weight", "shift"))
        self.assertEqual(pid, "p-4")

    def test_human_ratification_creates_version(self):
        engine = OutcomeLearningEngine()
        engine.propose_change(ProposedChange("p-5", "threshold", "lower"))
        change = engine.ratify("p-5", "human-owner")
        self.assertTrue(change.version_id.startswith("v-"))
        self.assertTrue(change.receipt_digest)

    def test_human_ratification_creates_receipt(self):
        engine = OutcomeLearningEngine()
        engine.propose_change(ProposedChange("p-6", "weight", "shift"))
        change = engine.ratify("p-6", "human-owner")
        self.assertNotEqual(change.receipt_digest, "")

    def test_failed_outcome_does_not_erase_clearance_record(self):
        engine = OutcomeLearningEngine()
        engine.note_clearance_record("clr-1")
        engine.record_outcome(_outcome(realized_value_minor=0))  # failed outcome
        # The clearance record reference is retained (immutable).
        digests = engine.outcome_digests_for("clr-1")
        self.assertGreaterEqual(len(digests), 1)

    def test_deterministic_digest(self):
        a = _outcome().digest()
        b = _outcome().digest()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_outcome_digest_differs(self):
        a = _outcome(outcome_id="o-a").digest()
        b = _outcome(outcome_id="o-b").digest()
        self.assertNotEqual(a, b)

    def test_engine_no_authority_surface(self):
        engine = OutcomeLearningEngine()
        self.assertFalse(engine.has_authority_surface)
        self.assertFalse(hasattr(engine, "execute"))
        self.assertFalse(hasattr(engine, "authorize"))
        self.assertFalse(hasattr(engine, "clear"))

    def test_proposal_and_applied_separated(self):
        # Proposals are never auto-applied to active profiles.
        engine = OutcomeLearningEngine()
        engine.apply_profile("p-a", "d1")
        engine.propose_change(ProposedChange("p-7", "weight", "shift"))
        # Profile digest unchanged by the proposal.
        self.assertEqual(engine._active_profiles["p-a"], "d1")


if __name__ == "__main__":
    unittest.main()
