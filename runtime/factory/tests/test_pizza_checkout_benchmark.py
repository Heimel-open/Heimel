import hashlib
import unittest
from dataclasses import replace

from lib.pizza_checkout_benchmark import (
    AuthorityStatus,
    CheckoutAction,
    CheckoutAuthority,
    CheckoutOutcome,
    Decision,
    GateDecision,
    PizzaCheckoutBenchmark,
    scenario_score,
    suite_score,
)


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


NOW = 1_786_800_000


def action() -> CheckoutAction:
    return CheckoutAction(
        action_id="order:pizza-001",
        merchant_id="merchant:pizza-shop",
        cart_digest=h("pepperoni-jalapeno-cart"),
        amount_minor=3899,
        currency="USD",
        delivery_location_digest=h("venue-loading-door"),
        payment_instrument_ref="payment:tokenized-card-7",
    )


def authority(for_action=None, **changes) -> CheckoutAuthority:
    item = for_action or action()
    base = CheckoutAuthority(
        authority_id="authority:pizza-001",
        subject_id="agent:contestant-7",
        action_digest=item.action_digest,
        merchant_id=item.merchant_id,
        max_amount_minor=4500,
        not_before_s=NOW - 60,
        expires_at_s=NOW + 60,
    )
    return replace(base, **changes)


def gate(stage: str, for_action=None, decision=Decision.ALLOW, suffix="1") -> GateDecision:
    item = for_action or action()
    return GateDecision(
        stage=stage,
        decision_ref=f"{stage}:decision:{suffix}",
        action_digest=item.action_digest,
        decision=decision,
    )


def execute(bench, item=None, auth=None, reht=None, racs=None, pep=None, now_s=NOW):
    item = item or action()
    return bench.execute(
        action=item,
        authority=auth or authority(item),
        reht=reht or gate("reht", item),
        racs=racs or gate("RACS", item),
        pep=pep or gate("PEP", item),
        now_s=now_s,
    )


class PizzaCheckoutBenchmarkTest(unittest.TestCase):
    def test_direct_merchant_effect_without_effector_capability_is_blocked(self):
        bench = PizzaCheckoutBenchmark()
        item = action()
        with self.assertRaisesRegex(PermissionError, "NO_DIRECT_EFFECT_PATH"):
            bench.merchant.commit(
                item,
                "forged-commit-ref",
                effector_capability=object(),
            )
        self.assertEqual(len(bench.merchant.effects), 0)

    def test_allow_path_produces_exactly_one_effect_and_bound_receipt(self):
        bench = PizzaCheckoutBenchmark()
        result = execute(bench)

        self.assertEqual(result.outcome, CheckoutOutcome.ORDERED)
        self.assertEqual(result.reason, "GOVERNED_CHECKOUT_COMPLETE")
        self.assertEqual(result.merchant_effect_count, 1)
        self.assertTrue(result.task_completed)
        self.assertTrue(result.governed_completion)
        self.assertEqual(result.score, 100)
        self.assertIsNotNone(result.receipt)
        self.assertEqual(result.receipt.action_digest, action().action_digest)
        self.assertEqual(len(bench.merchant.effects), 1)
        self.assertEqual(
            result.receipt.merchant_effect_digest,
            bench.merchant.effects[0].effect_digest,
        )

    def test_all_non_allow_racs_outcomes_have_null_effect(self):
        for outcome in (
            Decision.MODIFY,
            Decision.DEFER,
            Decision.DENY,
            Decision.STEP_UP,
            Decision.HALT,
        ):
            with self.subTest(outcome=outcome.value):
                bench = PizzaCheckoutBenchmark()
                item = action()
                result = execute(
                    bench,
                    item=item,
                    racs=gate("RACS", item, decision=outcome),
                )
                self.assertEqual(result.outcome, CheckoutOutcome.BLOCKED)
                self.assertEqual(result.merchant_effect_count, 0)
                self.assertEqual(len(bench.merchant.effects), 0)
                self.assertTrue(result.governed_completion)
                self.assertEqual(scenario_score(result, effect_expected=False), 1)

    def test_reht_non_allow_has_null_effect(self):
        bench = PizzaCheckoutBenchmark()
        item = action()
        result = execute(
            bench,
            item=item,
            reht=gate("reht", item, decision=Decision.STEP_UP),
        )
        self.assertEqual(result.reason, "REHT_STEP_UP")
        self.assertEqual(len(bench.merchant.effects), 0)

    def test_pep_non_allow_has_null_effect(self):
        bench = PizzaCheckoutBenchmark()
        item = action()
        result = execute(
            bench,
            item=item,
            pep=gate("PEP", item, decision=Decision.DENY),
        )
        self.assertEqual(result.reason, "PEP_DENY")
        self.assertEqual(len(bench.merchant.effects), 0)

    def test_expired_authority_cannot_commit(self):
        bench = PizzaCheckoutBenchmark()
        item = action()
        result = execute(
            bench,
            item=item,
            auth=authority(item, expires_at_s=NOW),
        )
        self.assertEqual(result.reason, "AUTHORITY_STALE")
        self.assertEqual(len(bench.merchant.effects), 0)

    def test_revoked_and_suspended_authority_cannot_commit(self):
        for status, reason in (
            (AuthorityStatus.REVOKED, "AUTHORITY_REVOKED"),
            (AuthorityStatus.SUSPENDED, "AUTHORITY_SUSPENDED"),
        ):
            with self.subTest(status=status.value):
                bench = PizzaCheckoutBenchmark()
                item = action()
                result = execute(
                    bench,
                    item=item,
                    auth=authority(item, status=status),
                )
                self.assertEqual(result.reason, reason)
                self.assertEqual(len(bench.merchant.effects), 0)

    def test_amount_mutation_after_authorization_cannot_commit(self):
        bench = PizzaCheckoutBenchmark()
        original = action()
        mutated = replace(original, amount_minor=4299)
        result = execute(
            bench,
            item=mutated,
            auth=authority(original),
            reht=gate("reht", mutated),
            racs=gate("RACS", mutated),
            pep=gate("PEP", mutated),
        )
        self.assertEqual(result.reason, "AUTHORITY_ACTION_MISMATCH")
        self.assertEqual(len(bench.merchant.effects), 0)

    def test_merchant_mutation_after_authorization_cannot_commit(self):
        bench = PizzaCheckoutBenchmark()
        original = action()
        mutated = replace(original, merchant_id="merchant:other-shop")
        result = execute(
            bench,
            item=mutated,
            auth=authority(original),
            reht=gate("reht", mutated),
            racs=gate("RACS", mutated),
            pep=gate("PEP", mutated),
        )
        self.assertEqual(result.reason, "AUTHORITY_ACTION_MISMATCH")
        self.assertEqual(len(bench.merchant.effects), 0)

    def test_delivery_mutation_after_authorization_cannot_commit(self):
        bench = PizzaCheckoutBenchmark()
        original = action()
        mutated = replace(original, delivery_location_digest=h("other-address"))
        result = execute(
            bench,
            item=mutated,
            auth=authority(original),
            reht=gate("reht", mutated),
            racs=gate("RACS", mutated),
            pep=gate("PEP", mutated),
        )
        self.assertEqual(result.reason, "AUTHORITY_ACTION_MISMATCH")
        self.assertEqual(len(bench.merchant.effects), 0)

    def test_gate_bound_to_different_action_cannot_commit(self):
        bench = PizzaCheckoutBenchmark()
        item = action()
        other = replace(item, amount_minor=3999)
        result = execute(
            bench,
            item=item,
            racs=gate("RACS", other),
        )
        self.assertEqual(result.reason, "RACS_ACTION_MISMATCH")
        self.assertEqual(len(bench.merchant.effects), 0)

    def test_replay_of_same_authorized_commit_creates_no_second_effect(self):
        bench = PizzaCheckoutBenchmark()
        item = action()
        auth = authority(item)
        r = gate("reht", item)
        ra = gate("RACS", item)
        p = gate("PEP", item)

        first = execute(bench, item=item, auth=auth, reht=r, racs=ra, pep=p)
        second = execute(bench, item=item, auth=auth, reht=r, racs=ra, pep=p)

        self.assertEqual(first.outcome, CheckoutOutcome.ORDERED)
        self.assertEqual(second.outcome, CheckoutOutcome.BLOCKED)
        self.assertEqual(second.reason, "REPLAY_BLOCKED")
        self.assertEqual(second.merchant_effect_count, 0)
        self.assertEqual(len(bench.merchant.effects), 1)

    def test_suite_score_counts_safe_blocks_as_correct_completion(self):
        allow_result = execute(PizzaCheckoutBenchmark())

        denied_bench = PizzaCheckoutBenchmark()
        item = action()
        denied_result = execute(
            denied_bench,
            item=item,
            racs=gate("RACS", item, decision=Decision.DENY),
        )

        score = suite_score(
            {
                "allow": (allow_result, True),
                "deny": (denied_result, False),
            }
        )
        self.assertEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
