"""BARO Convergence Layer — Phase 46c

Monitors systemic behavior convergence — detects if multiple policies
are aligned or diverging in their decisions. Ensures policy coherence
across the governance system.

Usage:
    convergence = BaroConvergenceLayer()
    score = convergence.measure_convergence(
        policies=active_policies,
        context=execution_context
    )
    drift = convergence.detect_policy_drift(policy_history)
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import logging

from src.valo_platform.policy_compiler import CompiledPolicy
from src.valo_platform.models import ExecutionDecision

logger = logging.getLogger(__name__)


class ConvergenceLevel(str, Enum):
    """Policy convergence level."""
    HIGHLY_ALIGNED = "highly_aligned"
    """Policies converge toward same decisions (>0.8)"""
    ALIGNED = "aligned"
    """Policies mostly agree (0.6-0.8)"""
    NEUTRAL = "neutral"
    """Policies diverge slightly (0.4-0.6)"""
    DIVERGENT = "divergent"
    """Policies pull in different directions (0.2-0.4)"""
    HIGHLY_DIVERGENT = "highly_divergent"
    """Policies directly contradict (<0.2)"""


class DriftDirection(str, Enum):
    """Direction of policy drift over time."""
    CONVERGING = "converging"
    """Policies becoming more aligned"""
    STABLE = "stable"
    """Policies maintaining alignment"""
    DIVERGING = "diverging"
    """Policies becoming less aligned"""


@dataclass
class ConvergenceScore:
    """Policy convergence measurement."""
    convergence_score: float
    """0.0-1.0, how aligned are policies"""
    convergence_level: ConvergenceLevel
    """Qualitative assessment"""
    aligned_policies: List[str] = field(default_factory=list)
    """Policy IDs that agree"""
    divergent_policies: List[str] = field(default_factory=list)
    """Policy IDs that disagree"""
    risk_level: str = "low"
    """low, medium, or high divergence risk"""
    agreement_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    """Pairwise agreement scores between policies"""
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "convergence_score": self.convergence_score,
            "convergence_level": self.convergence_level.value,
            "aligned_policies": self.aligned_policies,
            "divergent_policies": self.divergent_policies,
            "risk_level": self.risk_level,
            "agreement_matrix": self.agreement_matrix,
            "measured_at": self.measured_at.isoformat(),
        }


@dataclass
class DriftAnalysis:
    """Policy drift over time."""
    drift_detected: bool = False
    drift_direction: DriftDirection = DriftDirection.STABLE
    drift_magnitude: float = 0.0
    """0.0-1.0, how much drift"""
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    affected_policies: List[str] = field(default_factory=list)
    convergence_trend: List[float] = field(default_factory=list)
    """Historical convergence scores over time"""
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "drift_detected": self.drift_detected,
            "drift_direction": self.drift_direction.value,
            "drift_magnitude": self.drift_magnitude,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "affected_policies": self.affected_policies,
            "convergence_trend": self.convergence_trend,
            "recommendation": self.recommendation,
        }


class BaroConvergenceLayer:
    """Monitor systemic policy convergence and detect divergence trends.

    Ensures multiple policies remain aligned and detects when they
    begin pulling in conflicting directions.
    """

    def __init__(self, history_window_days: int = 30):
        """Initialize convergence layer.

        Args:
            history_window_days: Days of history to track for drift detection.
        """
        self.history_window_days = history_window_days
        self._convergence_history: List[Tuple[datetime, float]] = []
        self._policy_decision_cache: Dict[str, List[ExecutionDecision]] = {}

    def measure_convergence(
        self,
        policies: List[CompiledPolicy],
        context: Dict[str, Any],
    ) -> ConvergenceScore:
        """Measure how aligned policies are in their decisions.

        Evaluates all policies against the same context and measures
        agreement on decisions.

        Args:
            policies: List of active compiled policies.
            context: Decision context to evaluate against.

        Returns:
            ConvergenceScore with alignment metrics.
        """
        if not policies:
            return ConvergenceScore(
                convergence_score=1.0,
                convergence_level=ConvergenceLevel.HIGHLY_ALIGNED,
            )

        if len(policies) == 1:
            return ConvergenceScore(
                convergence_score=1.0,
                convergence_level=ConvergenceLevel.HIGHLY_ALIGNED,
                aligned_policies=[policies[0].policy_id],
            )

        # Evaluate all policies against context
        policy_decisions: Dict[str, bool] = {}
        for policy in policies:
            passed, _ = policy.evaluate(context)
            policy_decisions[policy.policy_id] = passed

        # Calculate pairwise agreement
        agreement_matrix: Dict[str, Dict[str, float]] = {}
        total_agreement = 0.0
        pair_count = 0

        for i, policy_a in enumerate(policies):
            agreement_matrix[policy_a.policy_id] = {}
            for j, policy_b in enumerate(policies):
                if i >= j:
                    continue

                # Agreement: both pass or both fail
                a_passed = policy_decisions[policy_a.policy_id]
                b_passed = policy_decisions[policy_b.policy_id]
                agreement = 1.0 if a_passed == b_passed else 0.0

                agreement_matrix[policy_a.policy_id][policy_b.policy_id] = agreement
                total_agreement += agreement
                pair_count += 1

        # Overall convergence score
        convergence_score = (
            total_agreement / pair_count if pair_count > 0 else 1.0
        )

        # Classify convergence level
        convergence_level = self._classify_convergence(convergence_score)

        # Identify aligned vs divergent policies
        aligned, divergent = self._classify_policies(
            policies,
            policy_decisions,
        )

        # Risk assessment
        risk_level = self._assess_convergence_risk(convergence_score)

        # Record in history
        self._convergence_history.append(
            (datetime.now(timezone.utc), convergence_score)
        )

        return ConvergenceScore(
            convergence_score=convergence_score,
            convergence_level=convergence_level,
            aligned_policies=aligned,
            divergent_policies=divergent,
            risk_level=risk_level,
            agreement_matrix=agreement_matrix,
        )

    def detect_policy_drift(
        self,
        policy_history: List[CompiledPolicy],
    ) -> DriftAnalysis:
        """Detect if policies are diverging over time.

        Compares policy decisions across versions to detect drift.

        Args:
            policy_history: List of policies over time (versions).

        Returns:
            DriftAnalysis with trend information.
        """
        if len(policy_history) < 2:
            return DriftAnalysis()

        # For simplicity, check if policies are becoming more restrictive
        # (proxy for divergence)
        allows = 0
        denies = 0

        for policy in policy_history:
            for rule in policy.rules:
                if hasattr(rule, 'rule_type'):
                    if rule.rule_type.value == "require":
                        allows += 1
                    elif rule.rule_type.value == "deny":
                        denies += 1

        total = allows + denies
        if total == 0:
            return DriftAnalysis()

        allow_ratio = allows / total
        deny_ratio = denies / total

        # Drift detection: if deny ratio growing significantly
        drift_magnitude = abs(deny_ratio - 0.5) / 0.5
        drift_direction = (
            DriftDirection.DIVERGING
            if deny_ratio > 0.6
            else DriftDirection.CONVERGING
            if deny_ratio < 0.4
            else DriftDirection.STABLE
        )

        affected_policies = [
            p.policy_id for p in policy_history
        ]

        recommendation = ""
        if drift_direction == DriftDirection.DIVERGING:
            recommendation = "Policies becoming more restrictive; review for unintended tightening"
        elif drift_direction == DriftDirection.CONVERGING:
            recommendation = "Policies becoming more permissive; verify risk appetite alignment"

        return DriftAnalysis(
            drift_detected=(drift_magnitude > 0.3),
            drift_direction=drift_direction,
            drift_magnitude=drift_magnitude,
            period_start=policy_history[0].created_at,
            period_end=policy_history[-1].created_at,
            affected_policies=affected_policies,
            recommendation=recommendation,
        )

    def get_convergence_trend(
        self,
        periods: int = 10,
    ) -> List[float]:
        """Get historical convergence scores.

        Args:
            periods: Number of recent measurements to return.

        Returns:
            List of convergence scores over time.
        """
        recent = self._convergence_history[-periods:]
        return [score for _, score in recent]

    def _classify_convergence(
        self,
        score: float,
    ) -> ConvergenceLevel:
        """Classify convergence score to level."""
        if score > 0.8:
            return ConvergenceLevel.HIGHLY_ALIGNED
        elif score > 0.6:
            return ConvergenceLevel.ALIGNED
        elif score > 0.4:
            return ConvergenceLevel.NEUTRAL
        elif score > 0.2:
            return ConvergenceLevel.DIVERGENT
        else:
            return ConvergenceLevel.HIGHLY_DIVERGENT

    def _classify_policies(
        self,
        policies: List[CompiledPolicy],
        decisions: Dict[str, bool],
    ) -> Tuple[List[str], List[str]]:
        """Separate aligned from divergent policies.

        Returns:
            (aligned_policy_ids, divergent_policy_ids)
        """
        # Simple heuristic: majority rules
        passed_count = sum(1 for d in decisions.values() if d)
        majority_passes = passed_count > len(decisions) / 2

        aligned = []
        divergent = []

        for policy in policies:
            policy_decision = decisions[policy.policy_id]
            if policy_decision == majority_passes:
                aligned.append(policy.policy_id)
            else:
                divergent.append(policy.policy_id)

        return aligned, divergent

    def _assess_convergence_risk(self, score: float) -> str:
        """Assess risk level of convergence score."""
        if score > 0.7:
            return "low"
        elif score > 0.4:
            return "medium"
        else:
            return "high"


# Global instance
_layer: Optional[BaroConvergenceLayer] = None


def init_baro_convergence() -> BaroConvergenceLayer:
    """Initialize global BARO convergence layer."""
    global _layer
    _layer = BaroConvergenceLayer()
    return _layer


def get_baro_convergence() -> BaroConvergenceLayer:
    """Get global BARO convergence layer."""
    global _layer
    if _layer is None:
        _layer = init_baro_convergence()
    return _layer
