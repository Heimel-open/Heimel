"""
VΛLΦ Model Router v0.1

Execution-stage model selection: "Which model should execute this action?"
Routes to cheapest-good-enough model, defaulting to local execution first.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List
from decimal import Decimal
import hashlib
from datetime import datetime, timezone


def _utcnow() -> datetime:
    """Return naive UTC for compatibility with persisted legacy timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RouterDecision(str, Enum):
    """Standard decision vocabulary (shared with ACS/VACS)."""
    ALLOW = "ALLOW"
    STEP_UP = "STEP_UP"  # Requires human model selection
    DEFER = "DEFER"  # Wait for better model availability
    DENY = "DENY"  # No suitable model available
    HALT = "HALT"  # Model system failure


class ModelTier(str, Enum):
    """Model capability tiers."""
    LOCAL = "LOCAL"  # Local/open models (cheapest, slowest)
    LIGHTWEIGHT = "LIGHTWEIGHT"  # llama.cpp, Ollama, vLLM (fast, efficient)
    STANDARD = "STANDARD"  # OpenRouter, Together (balanced)
    ADVANCED = "ADVANCED"  # OpenAI/Claude API (most capable, expensive)
    SPECIALIZED = "SPECIALIZED"  # Domain-specific models (medical, legal, code)


@dataclass
class ModelProfile:
    """Available model metadata."""
    name: str
    tier: ModelTier
    cost_per_1k_tokens: Decimal  # USD per 1000 tokens
    latency_ms: float  # Expected response time
    context_window: int  # Max tokens supported
    quality_score: float  # 0.0-1.0, estimated accuracy
    supports_functions: bool = True
    local: bool = False  # If True, runs locally
    endpoint: Optional[str] = None  # API endpoint if not local
    max_concurrent: int = 10  # Concurrent request limit

    def cost_estimate(self, tokens: int) -> Decimal:
        """Estimate cost for token count."""
        return Decimal(str(tokens)) * self.cost_per_1k_tokens / Decimal("1000")


@dataclass
class TaskRequirements:
    """Requirements for model selection."""
    prompt_tokens: int
    expected_completion_tokens: int = 500
    min_quality: float = 0.7  # Minimum quality threshold (0.0-1.0)
    max_cost: Optional[Decimal] = None  # Max cost budget
    max_latency_ms: Optional[float] = None  # Max acceptable latency
    requires_functions: bool = True
    domain: str = "general"  # general, medical, legal, code, finance
    prefer_local: bool = True  # If True, default to local models first
    requires_context: int = 2000  # Min context window needed


@dataclass
class ModelCandidate:
    """Scored model option."""
    model: ModelProfile
    quality_ok: bool  # Meets min quality threshold
    cost_ok: bool  # Within cost budget
    latency_ok: bool  # Within latency budget
    score: float  # 0.0-1.0, composite score (quality × efficiency)
    estimated_cost: Decimal
    estimated_latency_ms: float
    rationale: str


@dataclass
class RoutingPolicy:
    """Policy for model selection."""
    prefer_local: bool = True  # Default to local first
    cost_efficiency_weight: float = 0.6  # 60% optimize for cost
    quality_weight: float = 0.3  # 30% optimize for quality
    latency_weight: float = 0.1  # 10% optimize for speed

    min_quality_threshold: float = 0.5  # Reject models below this
    quality_margin: float = 0.1  # Accept models within 10% of best quality

    local_cost_bonus: Decimal = Decimal("0.02")  # Bonus for local models

    allow_tier_upgrade: bool = True  # Can upgrade from local→standard if needed


@dataclass
class RoutingDecision:
    """Model routing result."""
    decision: RouterDecision
    selected_model: Optional[ModelProfile] = None
    alternatives: List[ModelCandidate] = field(default_factory=list)
    estimated_cost: Decimal = Decimal("0")
    estimated_latency_ms: float = 0.0
    quality_score: float = 0.0
    rationale: str = ""
    requires_escalation: bool = False
    hash: str = ""
    timestamp: datetime = field(default_factory=_utcnow)

    def compute_hash(self) -> str:
        """Compute SHA256 for audit trail."""
        model_name = self.selected_model.name if self.selected_model else "none"
        data = f"{self.decision.value}{model_name}{self.estimated_cost}{self.timestamp.isoformat()}".encode()
        return hashlib.sha256(data).hexdigest()

    def __post_init__(self):
        if not self.hash:
            self.hash = self.compute_hash()

    def to_dict(self) -> Dict:
        return {
            "decision": self.decision.value,
            "selected_model": self.selected_model.name if self.selected_model else None,
            "alternatives_count": len(self.alternatives),
            "estimated_cost_usd": float(self.estimated_cost),
            "estimated_latency_ms": self.estimated_latency_ms,
            "quality_score": self.quality_score,
            "rationale": self.rationale,
            "requires_escalation": self.requires_escalation,
            "hash": self.hash,
            "timestamp": self.timestamp.isoformat(),
        }


class ModelRouter:
    """VΛLΦ Model Router: Execution-stage model selection."""

    def __init__(self, models: List[ModelProfile] = None, policy: RoutingPolicy = None):
        self.models = models or self._default_models()
        self.policy = policy or RoutingPolicy()
        self.decision_log: List[RoutingDecision] = []

    def route(self, requirements: TaskRequirements) -> RoutingDecision:
        """
        Route task to appropriate model.

        Returns:
            RoutingDecision with selected model and alternatives
        """
        # Score all candidates
        candidates = self._score_candidates(requirements)

        if not candidates:
            return RoutingDecision(
                decision=RouterDecision.DENY,
                rationale="No models meet requirements",
            )

        # Separate by quality
        quality_ok = [c for c in candidates if c.quality_ok]
        if not quality_ok:
            return RoutingDecision(
                decision=RouterDecision.DENY,
                alternatives=candidates[:3],
                rationale=f"Best model quality {candidates[0].model.quality_score:.2f} below threshold {requirements.min_quality:.2f}",
            )

        # Select best candidate
        best = max(quality_ok, key=lambda c: c.score)

        # Check if local model meets requirements
        local_candidates = [c for c in quality_ok if c.model.local]
        if self.policy.prefer_local and local_candidates:
            best = max(local_candidates, key=lambda c: c.score)

        # Determine if escalation needed
        escalate = (
            best.model.tier == ModelTier.ADVANCED or
            not best.quality_ok or
            requirements.max_cost and best.estimated_cost > requirements.max_cost
        )

        decision = RoutingDecision(
            decision=RouterDecision.ALLOW if not escalate else RouterDecision.STEP_UP,
            selected_model=best.model,
            alternatives=sorted(quality_ok, key=lambda c: c.score, reverse=True)[:2],
            estimated_cost=best.estimated_cost,
            estimated_latency_ms=best.estimated_latency_ms,
            quality_score=best.model.quality_score,
            rationale=best.rationale,
            requires_escalation=escalate,
        )

        self.decision_log.append(decision)
        return decision

    def _score_candidates(self, requirements: TaskRequirements) -> List[ModelCandidate]:
        """Score all models against requirements."""
        candidates = []

        for model in self.models:
            # Check hard constraints
            quality_ok = model.quality_score >= requirements.min_quality
            cost_ok = requirements.max_cost is None or model.cost_estimate(requirements.prompt_tokens + requirements.expected_completion_tokens) <= requirements.max_cost
            latency_ok = requirements.max_latency_ms is None or model.latency_ms <= requirements.max_latency_ms
            context_ok = model.context_window >= requirements.requires_context
            functions_ok = (not requirements.requires_functions) or model.supports_functions

            if not context_ok or not functions_ok:
                continue

            # Calculate composite score
            cost = model.cost_estimate(requirements.prompt_tokens + requirements.expected_completion_tokens)
            cost_score = 1.0 / (1.0 + float(cost))  # Higher cost = lower score
            quality_score = model.quality_score
            latency_score = 1.0 / (1.0 + model.latency_ms / 100)  # Normalize to ~1.0 for 100ms

            # Apply weights
            composite = (
                self.policy.cost_efficiency_weight * cost_score +
                self.policy.quality_weight * quality_score +
                self.policy.latency_weight * latency_score
            )

            # Local bonus
            if model.local:
                composite += float(self.policy.local_cost_bonus)

            candidate = ModelCandidate(
                model=model,
                quality_ok=quality_ok,
                cost_ok=cost_ok,
                latency_ok=latency_ok,
                score=composite,
                estimated_cost=cost,
                estimated_latency_ms=model.latency_ms,
                rationale=f"Score {composite:.2f} (quality={quality_score:.2f}, cost={cost_score:.2f}, latency={latency_score:.2f})"
            )
            candidates.append(candidate)

        return sorted(candidates, key=lambda c: c.score, reverse=True)

    def _default_models(self) -> List[ModelProfile]:
        """Default model registry."""
        return [
            # Local models (cheapest)
            ModelProfile(
                name="llama-2-7b-local",
                tier=ModelTier.LOCAL,
                cost_per_1k_tokens=Decimal("0.0001"),
                latency_ms=150.0,
                context_window=4096,
                quality_score=0.65,
                local=True,
            ),
            ModelProfile(
                name="mistral-7b-local",
                tier=ModelTier.LOCAL,
                cost_per_1k_tokens=Decimal("0.0001"),
                latency_ms=120.0,
                context_window=8192,
                quality_score=0.72,
                local=True,
            ),
            # Lightweight models
            ModelProfile(
                name="llama-2-13b-openrouter",
                tier=ModelTier.LIGHTWEIGHT,
                cost_per_1k_tokens=Decimal("0.00075"),
                latency_ms=200.0,
                context_window=4096,
                quality_score=0.75,
                endpoint="https://openrouter.ai/api/v1/chat/completions",
            ),
            ModelProfile(
                name="mistral-medium",
                tier=ModelTier.LIGHTWEIGHT,
                cost_per_1k_tokens=Decimal("0.0015"),
                latency_ms=180.0,
                context_window=32768,
                quality_score=0.78,
                endpoint="https://api.mistral.ai/v1/chat/completions",
            ),
            # Standard models
            ModelProfile(
                name="gpt-3.5-turbo",
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=Decimal("0.003"),
                latency_ms=100.0,
                context_window=16384,
                quality_score=0.82,
                endpoint="https://api.openai.com/v1/chat/completions",
            ),
            ModelProfile(
                name="claude-3-haiku",
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=Decimal("0.00375"),
                latency_ms=80.0,
                context_window=200000,
                quality_score=0.85,
                endpoint="https://api.anthropic.com/v1/messages",
            ),
            # Advanced models
            ModelProfile(
                name="gpt-4",
                tier=ModelTier.ADVANCED,
                cost_per_1k_tokens=Decimal("0.03"),
                latency_ms=150.0,
                context_window=8192,
                quality_score=0.95,
                endpoint="https://api.openai.com/v1/chat/completions",
            ),
            ModelProfile(
                name="claude-3-opus",
                tier=ModelTier.ADVANCED,
                cost_per_1k_tokens=Decimal("0.015"),
                latency_ms=120.0,
                context_window=200000,
                quality_score=0.96,
                endpoint="https://api.anthropic.com/v1/messages",
            ),
        ]

    def add_model(self, model: ModelProfile):
        """Register new model."""
        self.models.append(model)

    def remove_model(self, model_name: str):
        """Unregister model."""
        self.models = [m for m in self.models if m.name != model_name]

    def get_decision_log(self) -> List[Dict]:
        """Return audit trail as dicts."""
        return [d.to_dict() for d in self.decision_log]
