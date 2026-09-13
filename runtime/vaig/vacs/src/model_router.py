"""
VALO Model Router v0.1

Cost-aware, local-first routing for governed AI agents.

Core rule:
    Do not ask the best model.
    Ask the cheapest approved model that is good enough.

Design assumption:
    Most organisations will have small local models close to their context
    through Ollama, LM Studio, llama.cpp, private endpoints, or embedded runtimes.
    Local context should be exhausted before expensive remote tokens are spent,
    unless the task requires stronger reasoning, regulated vendor guarantees,
    or external capability.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class RouteDecision(Enum):
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"
    HUMAN = "HUMAN"
    DEFER = "DEFER"
    DENY = "DENY"
    HALT = "HALT"


@dataclass(frozen=True)
class TaskProfile:
    task_id: str
    task_type: str
    input_tokens: int
    expected_output_tokens: int
    required_quality: float = 0.70
    required_reasoning: float = 0.50
    max_latency_ms: Optional[int] = None
    max_cost_usd: Optional[float] = None
    data_class: str = "internal"
    jurisdiction: str = "EU"
    requires_tools: bool = False
    requires_remote_knowledge: bool = False
    risk_level: str = "low"


@dataclass(frozen=True)
class ModelCard:
    model_id: str
    provider: str
    endpoint_type: str  # local, private, remote, human
    input_cost_per_1m_tokens_usd: float
    output_cost_per_1m_tokens_usd: float
    quality: float
    reasoning: float
    context_window_tokens: int
    typical_latency_ms: int
    allowed_data_classes: tuple[str, ...]
    jurisdictions: tuple[str, ...]
    supports_tools: bool = False
    supports_remote_knowledge: bool = False
    available: bool = True

    @property
    def is_local(self) -> bool:
        return self.endpoint_type == "local"


@dataclass(frozen=True)
class RoutePolicy:
    prefer_local: bool = True
    local_quality_tolerance: float = 0.10
    local_reasoning_tolerance: float = 0.10
    require_private_for_sensitive: bool = True
    sensitive_data_classes: tuple[str, ...] = ("restricted", "personal", "secret")
    step_up_risk_levels: tuple[str, ...] = ("high", "critical")
    deny_remote_for_secret: bool = True


@dataclass(frozen=True)
class RouteResult:
    decision: RouteDecision
    reason: str
    task: TaskProfile
    selected_model: Optional[ModelCard]
    evaluated_models: tuple[Dict[str, Any], ...]
    estimated_cost_usd: Optional[float]


class VALOModelRouter:
    """
    Deterministic model router.

    It does not call models. It selects the cheapest approved model that meets
    the task requirements and emits an auditable routing receipt.
    """

    RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    def route(
        self,
        task: TaskProfile,
        models: Iterable[ModelCard],
        policy: RoutePolicy | None = None,
    ) -> RouteResult:
        policy = policy or RoutePolicy()
        model_list = list(models)

        if task.input_tokens < 0 or task.expected_output_tokens < 0:
            return RouteResult(RouteDecision.HALT, "negative token estimate", task, None, tuple(), None)

        if task.risk_level == "critical":
            return RouteResult(RouteDecision.HUMAN, "critical-risk task requires human routing", task, None, tuple(), None)

        evaluated: List[Dict[str, Any]] = []
        candidates: List[tuple[float, ModelCard]] = []

        for model in model_list:
            ok, reason, cost = self._evaluate_model(task, model, policy)
            evaluated.append({
                "model_id": model.model_id,
                "provider": model.provider,
                "endpoint_type": model.endpoint_type,
                "eligible": ok,
                "reason": reason,
                "estimated_cost_usd": cost,
            })
            if ok:
                candidates.append((cost, model))

        if not candidates:
            if task.requires_remote_knowledge:
                return RouteResult(RouteDecision.DEFER, "no eligible model with required remote knowledge", task, None, tuple(evaluated), None)
            return RouteResult(RouteDecision.DENY, "no eligible approved model", task, None, tuple(evaluated), None)

        selected_cost, selected = self._select(task, candidates, policy)

        if task.max_cost_usd is not None and selected_cost > task.max_cost_usd:
            return RouteResult(
                RouteDecision.DENY,
                f"selected model cost {selected_cost:.6f} exceeds task max {task.max_cost_usd:.6f}",
                task,
                selected,
                tuple(evaluated),
                selected_cost,
            )

        if task.risk_level in policy.step_up_risk_levels:
            return RouteResult(
                RouteDecision.HUMAN,
                f"{task.risk_level}-risk task requires human approval after model selection",
                task,
                selected,
                tuple(evaluated),
                selected_cost,
            )

        decision = RouteDecision.LOCAL if selected.is_local else RouteDecision.REMOTE
        return RouteResult(
            decision,
            "cheapest approved model that satisfies task requirements",
            task,
            selected,
            tuple(evaluated),
            selected_cost,
        )

    def receipt(self, result: RouteResult) -> Dict[str, Any]:
        payload = {
            "task": asdict(result.task),
            "selected_model": asdict(result.selected_model) if result.selected_model else None,
            "decision": result.decision.value,
            "reason": result.reason,
            "estimated_cost_usd": result.estimated_cost_usd,
            "evaluated_models": result.evaluated_models,
        }
        payload_hash = self._hash(payload)
        return {
            "receipt_id": str(uuid.uuid4()),
            "type": "valo.model_router.receipt.v1",
            "task_id": result.task.task_id,
            "decision": result.decision.value,
            "selected_model_id": result.selected_model.model_id if result.selected_model else None,
            "selected_provider": result.selected_model.provider if result.selected_model else None,
            "endpoint_type": result.selected_model.endpoint_type if result.selected_model else None,
            "estimated_cost_usd": result.estimated_cost_usd,
            "reason": result.reason,
            "payload_hash": payload_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": f"ed25519:{payload_hash.removeprefix('sha256:')[:64]}",
        }

    def _evaluate_model(self, task: TaskProfile, model: ModelCard, policy: RoutePolicy) -> tuple[bool, str, float]:
        cost = self._estimate_cost(task, model)

        if not model.available:
            return False, "model unavailable", cost

        if task.input_tokens + task.expected_output_tokens > model.context_window_tokens:
            return False, "context window too small", cost

        if task.data_class not in model.allowed_data_classes:
            return False, "data class not allowed", cost

        if task.jurisdiction not in model.jurisdictions and "global" not in model.jurisdictions:
            return False, "jurisdiction not allowed", cost

        if task.requires_tools and not model.supports_tools:
            return False, "tools required but unsupported", cost

        if task.requires_remote_knowledge and not model.supports_remote_knowledge:
            return False, "remote knowledge required but unsupported", cost

        if task.max_latency_ms is not None and model.typical_latency_ms > task.max_latency_ms:
            return False, "latency exceeds maximum", cost

        if policy.require_private_for_sensitive and task.data_class in policy.sensitive_data_classes:
            if model.endpoint_type not in ("local", "private", "human"):
                return False, "sensitive data requires local/private endpoint", cost

        if policy.deny_remote_for_secret and task.data_class == "secret" and model.endpoint_type == "remote":
            return False, "secret data cannot route to remote endpoint", cost

        quality_requirement = task.required_quality
        reasoning_requirement = task.required_reasoning

        if policy.prefer_local and model.is_local:
            quality_requirement = max(0.0, quality_requirement - policy.local_quality_tolerance)
            reasoning_requirement = max(0.0, reasoning_requirement - policy.local_reasoning_tolerance)

        if model.quality < quality_requirement:
            return False, "quality below requirement", cost

        if model.reasoning < reasoning_requirement:
            return False, "reasoning below requirement", cost

        return True, "eligible", cost

    def _select(self, task: TaskProfile, candidates: List[tuple[float, ModelCard]], policy: RoutePolicy) -> tuple[float, ModelCard]:
        if not policy.prefer_local:
            return min(candidates, key=lambda item: item[0])

        local_candidates = [(cost, model) for cost, model in candidates if model.is_local]
        if local_candidates:
            return min(local_candidates, key=lambda item: item[0])

        return min(candidates, key=lambda item: item[0])

    def _estimate_cost(self, task: TaskProfile, model: ModelCard) -> float:
        return (
            task.input_tokens / 1_000_000 * model.input_cost_per_1m_tokens_usd
            + task.expected_output_tokens / 1_000_000 * model.output_cost_per_1m_tokens_usd
        )

    def _hash(self, data: Dict[str, Any]) -> str:
        normalized = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def default_model_registry() -> tuple[ModelCard, ...]:
    """
    Example registry. Prices are placeholders and must be replaced by
    deployment-specific cost tables before production use.
    """
    return (
        ModelCard(
            model_id="ollama-small-local",
            provider="ollama",
            endpoint_type="local",
            input_cost_per_1m_tokens_usd=0.0,
            output_cost_per_1m_tokens_usd=0.0,
            quality=0.68,
            reasoning=0.55,
            context_window_tokens=32_000,
            typical_latency_ms=1500,
            allowed_data_classes=("public", "internal", "personal", "restricted", "secret"),
            jurisdictions=("EU", "NO"),
            supports_tools=False,
            supports_remote_knowledge=False,
        ),
        ModelCard(
            model_id="private-mid",
            provider="private-endpoint",
            endpoint_type="private",
            input_cost_per_1m_tokens_usd=0.50,
            output_cost_per_1m_tokens_usd=1.50,
            quality=0.78,
            reasoning=0.70,
            context_window_tokens=128_000,
            typical_latency_ms=2500,
            allowed_data_classes=("public", "internal", "personal", "restricted"),
            jurisdictions=("EU", "NO"),
            supports_tools=True,
            supports_remote_knowledge=False,
        ),
        ModelCard(
            model_id="remote-strong",
            provider="remote-frontier",
            endpoint_type="remote",
            input_cost_per_1m_tokens_usd=3.00,
            output_cost_per_1m_tokens_usd=15.00,
            quality=0.92,
            reasoning=0.92,
            context_window_tokens=200_000,
            typical_latency_ms=4000,
            allowed_data_classes=("public", "internal"),
            jurisdictions=("global",),
            supports_tools=True,
            supports_remote_knowledge=True,
        ),
    )
