from __future__ import annotations

"""WHY Gate runtime safety tests.

Verifies:
- evaluate_why returns correct WhyDecision for all score bands
- min(authority, policy, reality, consequence) aggregation
- score clamping (< 0.0 → 0.0, > 1.0 → 1.0)
- WhyState fields are populated correctly
- state hash is deterministic
- verify_why_chain: empty → True
- verify_why_chain: valid single state → True
- verify_why_chain: valid two-state chain → True
- verify_why_chain: tampered state_hash → False
- verify_why_chain: broken previous_hash link → False
- decide_why boundary values
- every WHY decision can become an auditable receipt
"""

from typing import Optional

import pytest

from vaig.why_gate import (
    WhyDecision,
    WhyInputs,
    WhyReceipt,
    WhyState,
    decide_why,
    evaluate_why,
    make_why_receipt,
    verify_why_chain,
    verify_why_receipt,
)


# ── Helper ─────────────────────────────────────────────────────

def _inputs(
    action_id: str = "act-1",
    authority: float = 0.9,
    policy: float = 0.9,
    reality: float = 0.9,
    consequence: float = 0.9,
    previous_hash: Optional[str] = None,
) -> WhyInputs:
    return WhyInputs(
        action_id=action_id,
        authority_score=authority,
        policy_score=policy,
        reality_score=reality,
        consequence_score=consequence,
        previous_hash=previous_hash,
    )


# ── decide_why ─────────────────────────────────────────────────

class TestDecideWhy:
    def test_score_above_085_is_continue(self):
        assert decide_why(0.9) == WhyDecision.CONTINUE
        assert decide_why(1.0) == WhyDecision.CONTINUE
        assert decide_why(0.85) == WhyDecision.CONTINUE

    def test_score_065_to_084_is_watch(self):
        assert decide_why(0.70) == WhyDecision.WATCH
        assert decide_why(0.65) == WhyDecision.WATCH
        assert decide_why(0.84) == WhyDecision.WATCH

    def test_score_045_to_064_is_human_review(self):
        assert decide_why(0.50) == WhyDecision.HUMAN_REVIEW
        assert decide_why(0.45) == WhyDecision.HUMAN_REVIEW
        assert decide_why(0.64) == WhyDecision.HUMAN_REVIEW

    def test_score_below_045_is_halt(self):
        assert decide_why(0.44) == WhyDecision.HALT
        assert decide_why(0.0) == WhyDecision.HALT
        assert decide_why(0.1) == WhyDecision.HALT

    def test_score_clamped_negative(self):
        assert decide_why(-0.5) == WhyDecision.HALT

    def test_score_clamped_above_one(self):
        assert decide_why(1.5) == WhyDecision.CONTINUE


# ── evaluate_why ───────────────────────────────────────────────

class TestEvaluateWhy:
    def test_all_high_scores_continue(self):
        state = evaluate_why(_inputs(authority=0.95, policy=0.95, reality=0.95, consequence=0.95))
        assert state.decision == WhyDecision.CONTINUE

    def test_min_score_watch(self):
        state = evaluate_why(_inputs(authority=0.9, policy=0.9, reality=0.7, consequence=0.9))
        assert state.decision == WhyDecision.WATCH
        assert state.why_score == pytest.approx(0.7)

    def test_min_score_human_review(self):
        state = evaluate_why(_inputs(authority=0.9, policy=0.9, reality=0.5, consequence=0.9))
        assert state.decision == WhyDecision.HUMAN_REVIEW
        assert state.why_score == pytest.approx(0.5)

    def test_min_score_halt(self):
        state = evaluate_why(_inputs(authority=0.9, policy=0.9, reality=0.3, consequence=0.9))
        assert state.decision == WhyDecision.HALT
        assert state.why_score == pytest.approx(0.3)

    def test_single_low_authority_halts(self):
        state = evaluate_why(_inputs(authority=0.2, policy=0.95, reality=0.95, consequence=0.95))
        assert state.decision == WhyDecision.HALT
        assert state.why_score == pytest.approx(0.2)

    def test_single_low_consequence_halts(self):
        state = evaluate_why(_inputs(authority=0.95, policy=0.95, reality=0.95, consequence=0.1))
        assert state.decision == WhyDecision.HALT
        assert state.why_score == pytest.approx(0.1)

    def test_score_clamped_above_one(self):
        state = evaluate_why(_inputs(authority=1.5, policy=1.5, reality=1.5, consequence=1.5))
        assert state.why_score == pytest.approx(1.0)
        assert state.decision == WhyDecision.CONTINUE

    def test_score_clamped_negative(self):
        state = evaluate_why(_inputs(authority=-0.5, policy=0.9, reality=0.9, consequence=0.9))
        assert state.why_score == pytest.approx(0.0)
        assert state.decision == WhyDecision.HALT

    def test_state_fields_populated(self):
        state = evaluate_why(_inputs(action_id="my-action"))
        assert state.action_id == "my-action"
        assert state.why_id.startswith("why_")
        assert state.timestamp
        assert state.state_hash
        assert state.previous_hash is None

    def test_previous_hash_stored(self):
        state = evaluate_why(_inputs(previous_hash="abc123"))
        assert state.previous_hash == "abc123"

    def test_metadata_stored(self):
        inputs = WhyInputs(
            action_id="a",
            authority_score=0.9,
            policy_score=0.9,
            reality_score=0.9,
            consequence_score=0.9,
            metadata={"env": "prod", "version": 2},
        )
        state = evaluate_why(inputs)
        assert state.metadata == {"env": "prod", "version": 2}

    def test_state_hash_is_hex_string(self):
        state = evaluate_why(_inputs())
        assert len(state.state_hash) == 64
        int(state.state_hash, 16)

    def test_two_calls_produce_different_ids(self):
        s1 = evaluate_why(_inputs())
        s2 = evaluate_why(_inputs())
        assert s1.why_id != s2.why_id
        assert s1.state_hash != s2.state_hash


# ── WHY receipt invariant ──────────────────────────────────────

class TestWhyReceipt:
    def test_state_can_be_represented_as_receipt(self):
        state = evaluate_why(_inputs(action_id="receipt-action"))
        receipt = make_why_receipt(state)

        assert isinstance(receipt, WhyReceipt)
        assert receipt.receipt_id.startswith("why_receipt_")
        assert receipt.receipt_type == "WHY_GATE_DECISION"
        assert receipt.why_id == state.why_id
        assert receipt.action_id == state.action_id
        assert receipt.decision == state.decision
        assert receipt.why_score == state.why_score
        assert receipt.state_hash == state.state_hash
        assert receipt.previous_hash == state.previous_hash
        assert len(receipt.receipt_hash) == 64
        int(receipt.receipt_hash, 16)

    def test_receipt_to_dict_serializes_decision_value(self):
        state = evaluate_why(_inputs())
        receipt = make_why_receipt(state)
        data = receipt.to_dict()

        assert data["decision"] == state.decision.value
        assert data["receipt_hash"] == receipt.receipt_hash

    def test_receipt_verifies_standalone(self):
        state = evaluate_why(_inputs())
        receipt = make_why_receipt(state)

        assert verify_why_receipt(receipt) is True

    def test_receipt_verifies_against_state(self):
        state = evaluate_why(_inputs())
        receipt = make_why_receipt(state)

        assert verify_why_receipt(receipt, state) is True

    def test_tampered_receipt_hash_fails(self):
        state = evaluate_why(_inputs())
        receipt = make_why_receipt(state)
        tampered = WhyReceipt(
            receipt_id=receipt.receipt_id,
            receipt_type=receipt.receipt_type,
            why_id=receipt.why_id,
            action_id=receipt.action_id,
            timestamp=receipt.timestamp,
            decision=receipt.decision,
            why_score=receipt.why_score,
            state_hash=receipt.state_hash,
            previous_hash=receipt.previous_hash,
            receipt_hash="dead" * 16,
            metadata=receipt.metadata,
        )

        assert verify_why_receipt(tampered) is False

    def test_receipt_bound_to_wrong_state_fails(self):
        state = evaluate_why(_inputs(action_id="a1"))
        other_state = evaluate_why(_inputs(action_id="a2"))
        receipt = make_why_receipt(state)

        assert verify_why_receipt(receipt, other_state) is False


# ── verify_why_chain ───────────────────────────────────────────

class TestVerifyWhyChain:
    def test_empty_chain_is_valid(self):
        assert verify_why_chain([]) is True

    def test_single_valid_state(self):
        state = evaluate_why(_inputs())
        assert verify_why_chain([state]) is True

    def test_two_state_valid_chain(self):
        s1 = evaluate_why(_inputs(action_id="a1"))
        s2 = evaluate_why(_inputs(action_id="a2", previous_hash=s1.state_hash))
        assert verify_why_chain([s1, s2]) is True

    def test_three_state_valid_chain(self):
        s1 = evaluate_why(_inputs(action_id="a1"))
        s2 = evaluate_why(_inputs(action_id="a2", previous_hash=s1.state_hash))
        s3 = evaluate_why(_inputs(action_id="a3", previous_hash=s2.state_hash))
        assert verify_why_chain([s1, s2, s3]) is True

    def test_tampered_state_hash_fails(self):
        state = evaluate_why(_inputs())
        tampered = WhyState(
            why_id=state.why_id,
            action_id=state.action_id,
            timestamp=state.timestamp,
            authority_score=state.authority_score,
            policy_score=state.policy_score,
            reality_score=state.reality_score,
            consequence_score=state.consequence_score,
            why_score=state.why_score,
            decision=state.decision,
            previous_hash=state.previous_hash,
            state_hash="dead" * 16,
            metadata=state.metadata,
        )
        assert verify_why_chain([tampered]) is False

    def test_broken_chain_link_fails(self):
        s1 = evaluate_why(_inputs(action_id="a1"))
        # s2 points to wrong previous hash
        s2 = evaluate_why(_inputs(action_id="a2", previous_hash="wrong_hash_000"))
        assert verify_why_chain([s1, s2]) is False

    def test_wrong_first_previous_hash_fails(self):
        # First state must have previous_hash=None
        s1 = evaluate_why(_inputs(previous_hash="non_null_hash"))
        assert verify_why_chain([s1]) is False

    def test_reversed_chain_fails(self):
        s1 = evaluate_why(_inputs(action_id="a1"))
        s2 = evaluate_why(_inputs(action_id="a2", previous_hash=s1.state_hash))
        # Reversed order: s2 before s1 — s2.previous_hash != None
        assert verify_why_chain([s2, s1]) is False
