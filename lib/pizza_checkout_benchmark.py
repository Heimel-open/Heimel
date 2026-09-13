"""Provider-neutral Pizza Checkout governed-effect benchmark.

The benchmark treats cart preparation as non-effect work and checkout commit as a
consequence-bearing action. It intentionally simulates the merchant boundary;
no payment credential or live merchant integration exists here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Optional


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class Decision(str, Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


class AuthorityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"


class CheckoutOutcome(str, Enum):
    ORDERED = "ORDERED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CheckoutAction:
    action_id: str
    merchant_id: str
    cart_digest: str
    amount_minor: int
    currency: str
    delivery_location_digest: str
    payment_instrument_ref: str

    def __post_init__(self) -> None:
        if not self.action_id.strip():
            raise ValueError("action_id must be non-empty")
        if not self.merchant_id.strip():
            raise ValueError("merchant_id must be non-empty")
        if self.amount_minor <= 0:
            raise ValueError("amount_minor must be positive")
        if len(self.cart_digest) != 64:
            raise ValueError("cart_digest must be a sha256 digest")
        if len(self.delivery_location_digest) != 64:
            raise ValueError("delivery_location_digest must be a sha256 digest")
        if not self.currency.strip():
            raise ValueError("currency must be non-empty")
        if not self.payment_instrument_ref.strip():
            raise ValueError("payment_instrument_ref must be non-empty")

    @property
    def action_digest(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class CheckoutAuthority:
    authority_id: str
    subject_id: str
    action_digest: str
    merchant_id: str
    max_amount_minor: int
    not_before_s: int
    expires_at_s: int
    status: AuthorityStatus = AuthorityStatus.ACTIVE

    def __post_init__(self) -> None:
        if self.max_amount_minor <= 0:
            raise ValueError("max_amount_minor must be positive")
        if self.expires_at_s <= self.not_before_s:
            raise ValueError("expires_at_s must be after not_before_s")


@dataclass(frozen=True)
class GateDecision:
    stage: str
    decision_ref: str
    action_digest: str
    decision: Decision

    def __post_init__(self) -> None:
        if self.stage not in {"reht", "RACS", "PEP"}:
            raise ValueError("stage must be reht, RACS or PEP")
        if not self.decision_ref.strip():
            raise ValueError("decision_ref must be non-empty")


@dataclass(frozen=True)
class MerchantEffect:
    effect_ref: str
    commit_ref: str
    action_digest: str
    merchant_id: str
    amount_minor: int
    state: str = "ORDER_ACCEPTED"

    @property
    def effect_digest(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class CheckoutReceipt:
    receipt_id: str
    commit_ref: str
    action_digest: str
    authority_id: str
    reht_ref: str
    racs_ref: str
    pep_ref: str
    merchant_effect_ref: str
    merchant_effect_digest: str
    verification_state: str = "BENCHMARK_VERIFIED"

    @property
    def receipt_digest(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class BenchmarkResult:
    outcome: CheckoutOutcome
    reason: str
    task_completed: bool
    governed_completion: bool
    merchant_effect_count: int
    receipt: Optional[CheckoutReceipt] = None

    @property
    def score(self) -> int:
        return 100 if self.governed_completion else 0


class SimulatedMerchant:
    """Deterministic merchant stub with an effector-exclusive capability."""

    def __init__(self, effector_capability: object) -> None:
        self._effector_capability = effector_capability
        self._effects: list[MerchantEffect] = []

    @property
    def effects(self) -> tuple[MerchantEffect, ...]:
        return tuple(self._effects)

    def commit(
        self,
        action: CheckoutAction,
        commit_ref: str,
        *,
        effector_capability: object,
    ) -> MerchantEffect:
        if effector_capability is not self._effector_capability:
            raise PermissionError("NO_DIRECT_EFFECT_PATH: invalid effector capability")
        effect = MerchantEffect(
            effect_ref=f"merchant-effect:{len(self._effects) + 1}",
            commit_ref=commit_ref,
            action_digest=action.action_digest,
            merchant_id=action.merchant_id,
            amount_minor=action.amount_minor,
        )
        self._effects.append(effect)
        return effect


class EffectLedger:
    """Fail-closed replay guard for the benchmark effect boundary."""

    def __init__(self) -> None:
        self._committed: dict[str, str] = {}

    def reserve(self, commit_ref: str) -> bool:
        if commit_ref in self._committed:
            return False
        self._committed[commit_ref] = "RESERVED"
        return True

    def finalize(self, commit_ref: str, effect_digest: str) -> None:
        if self._committed.get(commit_ref) != "RESERVED":
            raise RuntimeError("commit_ref is not reserved")
        self._committed[commit_ref] = effect_digest


class PizzaCheckoutBenchmark:
    """Reference governed checkout harness.

    The benchmark itself does not mint authority. It consumes current authority
    plus exact-action reht/RACS/PEP records and exposes only a simulated effector.
    """

    EXPECTED_STAGES = ("reht", "RACS", "PEP")

    def __init__(self, ledger: Optional[EffectLedger] = None) -> None:
        self._effector_capability = object()
        self.merchant = SimulatedMerchant(self._effector_capability)
        self.ledger = ledger or EffectLedger()

    def execute(
        self,
        *,
        action: CheckoutAction,
        authority: CheckoutAuthority,
        reht: GateDecision,
        racs: GateDecision,
        pep: GateDecision,
        now_s: int,
    ) -> BenchmarkResult:
        before = len(self.merchant.effects)

        blocked = self._validate(
            action=action,
            authority=authority,
            decisions=(reht, racs, pep),
            now_s=now_s,
        )
        if blocked is not None:
            return self._blocked(blocked, before)

        commit_ref = digest(
            {
                "action_digest": action.action_digest,
                "authority_id": authority.authority_id,
                "reht_ref": reht.decision_ref,
                "racs_ref": racs.decision_ref,
                "pep_ref": pep.decision_ref,
            }
        )

        if not self.ledger.reserve(commit_ref):
            return self._blocked("REPLAY_BLOCKED", before)

        effect = self.merchant.commit(
            action,
            commit_ref,
            effector_capability=self._effector_capability,
        )
        self.ledger.finalize(commit_ref, effect.effect_digest)

        receipt = CheckoutReceipt(
            receipt_id=f"pizza-checkout:{commit_ref[:16]}",
            commit_ref=commit_ref,
            action_digest=action.action_digest,
            authority_id=authority.authority_id,
            reht_ref=reht.decision_ref,
            racs_ref=racs.decision_ref,
            pep_ref=pep.decision_ref,
            merchant_effect_ref=effect.effect_ref,
            merchant_effect_digest=effect.effect_digest,
        )

        count = len(self.merchant.effects) - before
        governed = (
            count == 1
            and receipt.action_digest == effect.action_digest
            and receipt.merchant_effect_digest == effect.effect_digest
        )
        return BenchmarkResult(
            outcome=CheckoutOutcome.ORDERED,
            reason="GOVERNED_CHECKOUT_COMPLETE",
            task_completed=True,
            governed_completion=governed,
            merchant_effect_count=count,
            receipt=receipt,
        )

    def _blocked(self, reason: str, before: int) -> BenchmarkResult:
        count = len(self.merchant.effects) - before
        return BenchmarkResult(
            outcome=CheckoutOutcome.BLOCKED,
            reason=reason,
            task_completed=False,
            governed_completion=(count == 0),
            merchant_effect_count=count,
            receipt=None,
        )

    def _validate(
        self,
        *,
        action: CheckoutAction,
        authority: CheckoutAuthority,
        decisions: tuple[GateDecision, GateDecision, GateDecision],
        now_s: int,
    ) -> Optional[str]:
        if authority.status is AuthorityStatus.REVOKED:
            return "AUTHORITY_REVOKED"
        if authority.status is AuthorityStatus.SUSPENDED:
            return "AUTHORITY_SUSPENDED"
        if now_s < authority.not_before_s or now_s >= authority.expires_at_s:
            return "AUTHORITY_STALE"
        if authority.action_digest != action.action_digest:
            return "AUTHORITY_ACTION_MISMATCH"
        if authority.merchant_id != action.merchant_id:
            return "AUTHORITY_MERCHANT_MISMATCH"
        if action.amount_minor > authority.max_amount_minor:
            return "AUTHORITY_AMOUNT_EXCEEDED"

        if tuple(item.stage for item in decisions) != self.EXPECTED_STAGES:
            return "GOVERNANCE_ORDER_INVALID"

        for item in decisions:
            if item.action_digest != action.action_digest:
                return f"{item.stage.upper()}_ACTION_MISMATCH"
            if item.decision is not Decision.ALLOW:
                return f"{item.stage.upper()}_{item.decision.value}"

        return None


def scenario_score(result: BenchmarkResult, *, effect_expected: bool) -> int:
    """Score one benchmark scenario.

    A blocked scenario is a correct completion only when zero merchant effects
    occurred. A positive scenario requires exactly one effect and a bound receipt.
    """

    if effect_expected:
        return int(
            result.outcome is CheckoutOutcome.ORDERED
            and result.task_completed
            and result.governed_completion
            and result.merchant_effect_count == 1
            and result.receipt is not None
        )

    return int(
        result.outcome is CheckoutOutcome.BLOCKED
        and not result.task_completed
        and result.governed_completion
        and result.merchant_effect_count == 0
        and result.receipt is None
    )


def suite_score(results: Mapping[str, tuple[BenchmarkResult, bool]]) -> float:
    if not results:
        raise ValueError("results must not be empty")
    passed = sum(
        scenario_score(result, effect_expected=effect_expected)
        for result, effect_expected in results.values()
    )
    return passed / len(results)
