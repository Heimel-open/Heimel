"""
VALO Exploration Budget v0.1

A bounded creativity gate for governed AI spend.

Core idea:
    Production work needs ROI.
    Exploration needs bounded cost, low risk, and captured learning.

This module prevents uncontrolled token spend without turning VALO into a
creativity blocker. Low-risk play, learning, and experiments are allowed inside
an explicit budget wallet.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class SpendClass(Enum):
    PRODUCTION = "production"
    EXPERIMENT = "experiment"
    LEARNING = "learning"
    PLAY = "play"
    INCIDENT = "incident"
    REGULATED_ACTION = "regulated_action"


class BudgetDecision(Enum):
    ALLOW = "ALLOW"
    STEP_UP = "STEP_UP"
    DEFER = "DEFER"
    DENY = "DENY"
    HALT = "HALT"


@dataclass(frozen=True)
class BudgetWallet:
    wallet_id: str
    owner_id: str
    period: str
    total_budget_usd: float
    used_budget_usd: float = 0.0
    local_token_budget: int = 0
    used_local_tokens: int = 0
    remote_token_budget: int = 0
    used_remote_tokens: int = 0
    frontier_call_budget: int = 0
    used_frontier_calls: int = 0

    @property
    def remaining_budget_usd(self) -> float:
        return self.total_budget_usd - self.used_budget_usd

    @property
    def remaining_local_tokens(self) -> int:
        return self.local_token_budget - self.used_local_tokens

    @property
    def remaining_remote_tokens(self) -> int:
        return self.remote_token_budget - self.used_remote_tokens

    @property
    def remaining_frontier_calls(self) -> int:
        return self.frontier_call_budget - self.used_frontier_calls


@dataclass(frozen=True)
class ExplorationRequest:
    request_id: str
    spend_class: SpendClass
    estimated_cost_usd: float
    estimated_local_tokens: int = 0
    estimated_remote_tokens: int = 0
    uses_frontier_model: bool = False
    risk_level: str = "low"
    data_class: str = "internal"
    external_action: bool = False
    irreversible: bool = False
    expected_learning: str = ""
    capture_learning: bool = True


@dataclass(frozen=True)
class ExplorationPolicy:
    allow_classes: tuple[SpendClass, ...] = (SpendClass.EXPERIMENT, SpendClass.LEARNING, SpendClass.PLAY)
    require_learning_capture: bool = True
    max_single_exploration_cost_usd: float = 5.0
    max_single_remote_tokens: int = 20_000
    max_single_local_tokens: int = 200_000
    allowed_risk_levels: tuple[str, ...] = ("low", "medium")
    blocked_data_classes: tuple[str, ...] = ("restricted", "secret")
    step_up_data_classes: tuple[str, ...] = ("personal",)
    frontier_requires_step_up: bool = True
    external_action_requires_step_up: bool = True
    irreversible_requires_step_up: bool = True


@dataclass(frozen=True)
class ExplorationResult:
    decision: BudgetDecision
    reason: str
    request: ExplorationRequest
    wallet: BudgetWallet
    policy: ExplorationPolicy


class VALOExplorationBudgetGate:
    """
    Allows bounded exploration without requiring hard ROI proof.

    This gate should run before ROI Gate for spend classes that are explicitly
    exploratory. If it returns ALLOW, the work may proceed inside the wallet.
    If it returns STEP_UP, a human can decide whether the creative bet is worth
    extra budget.
    """

    def evaluate(
        self,
        request: ExplorationRequest,
        wallet: BudgetWallet,
        policy: Optional[ExplorationPolicy] = None,
    ) -> ExplorationResult:
        policy = policy or ExplorationPolicy()

        if request.estimated_cost_usd < 0:
            return self._result(BudgetDecision.HALT, "negative cost estimate", request, wallet, policy)

        if request.estimated_local_tokens < 0 or request.estimated_remote_tokens < 0:
            return self._result(BudgetDecision.HALT, "negative token estimate", request, wallet, policy)

        if request.spend_class not in policy.allow_classes:
            return self._result(
                BudgetDecision.DEFER,
                "spend class is not exploration; route through ROI Gate",
                request,
                wallet,
                policy,
            )

        if request.risk_level not in policy.allowed_risk_levels:
            return self._result(BudgetDecision.STEP_UP, "risk level exceeds exploration policy", request, wallet, policy)

        if request.data_class in policy.blocked_data_classes:
            return self._result(BudgetDecision.DENY, "data class is blocked for exploration budget", request, wallet, policy)

        if request.data_class in policy.step_up_data_classes:
            return self._result(BudgetDecision.STEP_UP, "personal data requires approval for exploration", request, wallet, policy)

        if policy.require_learning_capture and not request.capture_learning:
            return self._result(BudgetDecision.DEFER, "exploration must capture learning", request, wallet, policy)

        if policy.require_learning_capture and not request.expected_learning.strip():
            return self._result(BudgetDecision.DEFER, "expected learning must be stated", request, wallet, policy)

        if request.estimated_cost_usd > policy.max_single_exploration_cost_usd:
            return self._result(BudgetDecision.STEP_UP, "single exploration cost exceeds policy", request, wallet, policy)

        if request.estimated_remote_tokens > policy.max_single_remote_tokens:
            return self._result(BudgetDecision.STEP_UP, "single remote token estimate exceeds policy", request, wallet, policy)

        if request.estimated_local_tokens > policy.max_single_local_tokens:
            return self._result(BudgetDecision.STEP_UP, "single local token estimate exceeds policy", request, wallet, policy)

        if request.estimated_cost_usd > wallet.remaining_budget_usd:
            return self._result(BudgetDecision.STEP_UP, "wallet budget exhausted", request, wallet, policy)

        if request.estimated_local_tokens > wallet.remaining_local_tokens:
            return self._result(BudgetDecision.STEP_UP, "local token budget exhausted", request, wallet, policy)

        if request.estimated_remote_tokens > wallet.remaining_remote_tokens:
            return self._result(BudgetDecision.STEP_UP, "remote token budget exhausted", request, wallet, policy)

        if request.uses_frontier_model and policy.frontier_requires_step_up:
            if wallet.remaining_frontier_calls <= 0:
                return self._result(BudgetDecision.STEP_UP, "frontier exploration budget exhausted", request, wallet, policy)
            return self._result(BudgetDecision.STEP_UP, "frontier model use requires approval", request, wallet, policy)

        if request.external_action and policy.external_action_requires_step_up:
            return self._result(BudgetDecision.STEP_UP, "external action requires approval", request, wallet, policy)

        if request.irreversible and policy.irreversible_requires_step_up:
            return self._result(BudgetDecision.STEP_UP, "irreversible exploration requires approval", request, wallet, policy)

        return self._result(BudgetDecision.ALLOW, "allowed under bounded exploration budget", request, wallet, policy)

    def receipt(self, result: ExplorationResult) -> Dict[str, Any]:
        payload = {
            "request": self._enum_safe_asdict(result.request),
            "wallet": asdict(result.wallet),
            "policy": self._enum_safe_asdict(result.policy),
            "decision": result.decision.value,
            "reason": result.reason,
        }
        payload_hash = self._hash(payload)
        return {
            "receipt_id": str(uuid.uuid4()),
            "type": "valo.exploration_budget.receipt.v1",
            "request_id": result.request.request_id,
            "wallet_id": result.wallet.wallet_id,
            "owner_id": result.wallet.owner_id,
            "spend_class": result.request.spend_class.value,
            "decision": result.decision.value,
            "reason": result.reason,
            "estimated_cost_usd": result.request.estimated_cost_usd,
            "estimated_local_tokens": result.request.estimated_local_tokens,
            "estimated_remote_tokens": result.request.estimated_remote_tokens,
            "payload_hash": payload_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": f"ed25519:{payload_hash.removeprefix('sha256:')[:64]}",
        }

    def _result(
        self,
        decision: BudgetDecision,
        reason: str,
        request: ExplorationRequest,
        wallet: BudgetWallet,
        policy: ExplorationPolicy,
    ) -> ExplorationResult:
        return ExplorationResult(decision, reason, request, wallet, policy)

    def _enum_safe_asdict(self, value: Any) -> Dict[str, Any]:
        def convert(item: Any) -> Any:
            if isinstance(item, Enum):
                return item.value
            if isinstance(item, tuple):
                return tuple(convert(x) for x in item)
            if isinstance(item, list):
                return [convert(x) for x in item]
            if isinstance(item, dict):
                return {k: convert(v) for k, v in item.items()}
            return item

        return convert(asdict(value))

    def _hash(self, data: Dict[str, Any]) -> str:
        normalized = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"
