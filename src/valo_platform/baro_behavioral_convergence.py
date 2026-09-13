"""
BARO Behavioral Convergence Monitor (valo-platform #131)

First-class systemic-risk observation layer. Detects when individually-admissible
AI actions collectively converge into systemic risk via three mutually reinforcing
channels (per the systemic-risk paper cited in the issue):

  - performative prediction : AI output changes the reality it predicts
  - algorithmic herding     : many AIs converge on the same signal/action
  - cognitive dependency     : humans lose independent judgment over time

This is OBSERVATIONAL ONLY (BARO principle). It never decides. It emits a
RealityPackage fragment with convergence/diversity/dependency signals for VAIG
(risk/context evaluation) and REHT (admissibility decision).

Distinct from baro_convergence.py (Phase 46c) which measures *policy* coherence.
This monitors *behavioral* convergence across agents, models, sources, workflows
and human-override frequency.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class ConvergenceRisk(str, Enum):
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BehavioralConvergenceSignal:
    """Observed systemic-behavior signal (BARO emits, does not decide)."""
    convergence_score: float = 0.0       # 0 (diverse) .. 1 (monoculture)
    diversity_score: float = 1.0         # 0 (monoculture) .. 1 (diverse)
    source_concentration: float = 0.0    # HHI over sources/models/vendors
    model_correlation: float = 0.0       # avg pairwise action correlation
    consensus_velocity: float = 0.0      # rate of agreement tightening
    feedback_loop_risk: float = 0.0      # AI output altering observed reality
    cognitive_dependency_index: float = 0.0  # 1 - (human overrides / decisions)
    herding_risk: float = 0.0            # action monoculture pressure
    monoculture_index: float = 0.0       # dominant actor/model share
    risk: ConvergenceRisk = ConvergenceRisk.LOW
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_reality_package(self) -> Dict[str, Any]:
        """Fragment appended to BARO RealityPackage for VAIG/REHT."""
        return {
            "observer": "baro_behavioral_convergence",
            "convergence_score": self.convergence_score,
            "diversity_score": self.diversity_score,
            "source_concentration": self.source_concentration,
            "model_correlation": self.model_correlation,
            "consensus_velocity": self.consensus_velocity,
            "feedback_loop_risk": self.feedback_loop_risk,
            "cognitive_dependency_index": self.cognitive_dependency_index,
            "herding_risk": self.herding_risk,
            "monoculture_index": self.monoculture_index,
            "risk": self.risk.value,
            "timestamp": self.timestamp.isoformat(),
        }


def _hhi(shares: List[float]) -> float:
    """Herfindahl-Hirschman index over a distribution of shares (0..1)."""
    return round(sum(s * s for s in shares), 4)


class BehavioralConvergenceMonitor:
    """
    Observes emergent behavioral patterns across agents/models/sources and emits
    systemic-risk signals. Stateless accumulation is callers' responsibility;
    this class computes signals from a window of observed decisions.
    """

    def __init__(self, herding_threshold: float = 0.7,
                 dependency_threshold: float = 0.8) -> None:
        self.herding_threshold = herding_threshold
        self.dependency_threshold = dependency_threshold

    def observe_window(self, decisions: List[Dict[str, Any]]) -> BehavioralConvergenceSignal:
        """
        decisions: list of observed decision records, each with optional keys:
          action, actor, model, source, overridden (bool; human overrode AI),
          predicted_reality_before, observed_reality_after
        Returns a BehavioralConvergenceSignal (observation only).
        """
        n = len(decisions)
        if n == 0:
            return BehavioralConvergenceSignal(risk=ConvergenceRisk.LOW)

        # --- action monoculture / herding ---
        actions = Counter(d.get("action", "unknown") for d in decisions)
        action_shares = [c / n for c in actions.values()]
        monoculture_index = max(action_shares)
        herding_risk = min(1.0, monoculture_index / self.herding_threshold) \
            if self.herding_threshold > 0 else 0.0

        # --- source / model concentration (HHI) ---
        model_shares = [c / n for c in Counter(
            d.get("model", "unknown") for d in decisions).values()]
        source_shares = [c / n for c in Counter(
            d.get("source", "unknown") for d in decisions).values()]
        source_concentration = max(_hhi(model_shares), _hhi(source_shares))

        # --- model correlation (mean pairwise action agreement) ---
        model_correlation = self._mean_action_agreement(decisions)

        # --- cognitive dependency (1 - override rate) ---
        overrides = sum(1 for d in decisions if d.get("overridden"))
        override_rate = overrides / n
        cognitive_dependency_index = round(1.0 - override_rate, 4)

        # --- feedback loop risk (AI output changed observed reality) ---
        fb = [1 for d in decisions
              if d.get("predicted_reality_before") is not None
              and d.get("observed_reality_after") is not None
              and d["predicted_reality_before"] != d["observed_reality_after"]]
        feedback_loop_risk = round(len(fb) / n, 4)

        # --- derived ---
        diversity_score = round(1.0 - monoculture_index, 4)
        convergence_score = round(
            (monoculture_index + source_concentration + model_correlation) / 3.0, 4)
        consensus_velocity = 0.0  # requires history; set by caller across windows

        risk = self._classify(convergence_score, herding_risk,
                              cognitive_dependency_index)
        return BehavioralConvergenceSignal(
            convergence_score=convergence_score,
            diversity_score=diversity_score,
            source_concentration=source_concentration,
            model_correlation=model_correlation,
            consensus_velocity=consensus_velocity,
            feedback_loop_risk=feedback_loop_risk,
            cognitive_dependency_index=cognitive_dependency_index,
            herding_risk=round(herding_risk, 4),
            monoculture_index=round(monoculture_index, 4),
            risk=risk,
        )

    def _mean_action_agreement(self, decisions: List[Dict[str, Any]]) -> float:
        """Mean pairwise fraction of identical actions within same model group."""
        by_model: Dict[str, List[str]] = {}
        for d in decisions:
            by_model.setdefault(d.get("model", "unknown"), []).append(
                d.get("action", "unknown"))
        agreements = []
        for acts in by_model.values():
            if len(acts) >= 2:
                dom = max(set(acts), key=acts.count)
                agreements.append(acts.count(dom) / len(acts))
        return round(sum(agreements) / len(agreements), 4) if agreements else 0.0

    def _classify(self, convergence: float, herding: float,
                  dependency: float) -> ConvergenceRisk:
        score = max(convergence, herding, dependency)
        if score >= 0.85:
            return ConvergenceRisk.CRITICAL
        if score >= 0.7:
            return ConvergenceRisk.HIGH
        if score >= 0.5:
            return ConvergenceRisk.ELEVATED
        return ConvergenceRisk.LOW
