"""Evidence-bounded AI transition and resistance risk evaluation.

This module implements the runtime evaluator specified in Index for:

- Human/Institutional AI Transition Risk (HITR)
- Political Realignment Risk (PRR)

The evaluator is evidence-only. It does not grant execution authority, infer
job loss from technical exposure, or predict partisan outcomes. Composite
scores are fail-closed: they are emitted only under an explicitly calibrated
policy with provenance-bearing evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from math import prod
from typing import Dict, Mapping, Optional, Tuple


class TransitionRiskInputError(ValueError):
    """Raised for malformed signals or invalid composite policies."""


class AssessmentStatus(str, Enum):
    """Bounded evaluator outcomes; none imply authority or clearance."""

    SCORED = "SCORED"
    COMPONENTS_ONLY = "COMPONENTS_ONLY"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class EvidenceSignal:
    """One normalized, provenance-bearing transition-risk signal.

    ``value`` is risk-aligned on [0, 1]: 0 means the factor contributes
    minimal measured risk, 1 means maximal measured risk. ``None`` represents
    an explicitly unknown value rather than an inferred zero.
    """

    value: Optional[float]
    source: str
    provenance_digest: str
    observed_at: datetime
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.value is not None and not 0.0 <= self.value <= 1.0:
            raise TransitionRiskInputError("signal value must be within [0, 1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise TransitionRiskInputError("signal confidence must be within [0, 1]")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise TransitionRiskInputError("observed_at must be timezone-aware")


@dataclass(frozen=True)
class EvidencePolicy:
    """Minimum evidence requirements for decision-grade evaluation."""

    max_age_days: int = 365
    min_confidence: float = 0.60
    require_source: bool = True
    require_provenance_digest: bool = True

    def __post_init__(self) -> None:
        if self.max_age_days < 0:
            raise TransitionRiskInputError("max_age_days must be non-negative")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise TransitionRiskInputError("min_confidence must be within [0, 1]")


@dataclass(frozen=True)
class CompositePolicy:
    """Explicit calibration contract for a non-linear composite score.

    No default weights are provided. A caller must supply a complete set of
    weights, mark the policy calibrated, and identify the calibration basis.
    """

    weights: Mapping[str, float]
    calibrated: bool = False
    calibration_ref: str = ""
    method: str = "weighted_geometric"


@dataclass(frozen=True)
class RiskAssessment:
    """Evaluator output preserving both component evidence and limitations."""

    status: AssessmentStatus
    dimensions: Mapping[str, float]
    composite_score: Optional[float]
    evidence_confidence: Optional[float]
    reasons: Tuple[str, ...]
    calibration_ref: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        """Return a stable serialization surface without predictive claims."""

        return {
            "status": self.status.value,
            "dimensions": dict(self.dimensions),
            "composite_score": self.composite_score,
            "evidence_confidence": self.evidence_confidence,
            "reasons": list(self.reasons),
            "calibration_ref": self.calibration_ref,
        }


class AITransitionRiskEvaluator:
    """Deterministic HITR/PRR evaluator over bounded external evidence."""

    HITR_DIMENSIONS = (
        "ai_exposure",
        "adoption_velocity",
        "role_redesign",
        "economic_fragility",
        "human_resistance",
        "institutional_transition_risk",
    )
    PRR_DIMENSIONS = (
        "hitr",
        "geographic_concentration",
        "political_sensitivity",
    )

    def __init__(self, evidence_policy: Optional[EvidencePolicy] = None) -> None:
        self.evidence_policy = evidence_policy or EvidencePolicy()

    def evaluate_hitr(
        self,
        signals: Mapping[str, EvidenceSignal],
        *,
        as_of: datetime,
        composite_policy: Optional[CompositePolicy] = None,
    ) -> RiskAssessment:
        """Evaluate Human/Institutional AI Transition Risk.

        Technical exposure is only one dimension. Absence of adoption, role
        redesign, fragility, resistance, or institutional evidence is not
        silently inferred from exposure.
        """

        return self._evaluate_dimensions(
            self.HITR_DIMENSIONS,
            signals,
            as_of=as_of,
            composite_policy=composite_policy,
        )

    def evaluate_prr(
        self,
        hitr: RiskAssessment,
        signals: Mapping[str, EvidenceSignal],
        *,
        as_of: datetime,
        composite_policy: Optional[CompositePolicy] = None,
    ) -> RiskAssessment:
        """Evaluate Political Realignment Risk without partisan prediction.

        PRR requires a scored HITR composite. A components-only HITR result is
        preserved as such instead of being converted into a political score.
        """

        if hitr.status in (
            AssessmentStatus.UNKNOWN,
            AssessmentStatus.INSUFFICIENT_EVIDENCE,
        ):
            return RiskAssessment(
                status=hitr.status,
                dimensions={},
                composite_score=None,
                evidence_confidence=hitr.evidence_confidence,
                reasons=("hitr_not_decision_grade",) + hitr.reasons,
            )
        if hitr.status != AssessmentStatus.SCORED or hitr.composite_score is None:
            return RiskAssessment(
                status=AssessmentStatus.COMPONENTS_ONLY,
                dimensions={},
                composite_score=None,
                evidence_confidence=hitr.evidence_confidence,
                reasons=("hitr_composite_required_for_prr",),
            )

        prr_signals = dict(signals)
        prr_signals["hitr"] = EvidenceSignal(
            value=hitr.composite_score,
            source="VAIG:HITR",
            provenance_digest=hitr.calibration_ref or "hitr-assessment",
            observed_at=as_of,
            confidence=hitr.evidence_confidence or 0.0,
        )
        return self._evaluate_dimensions(
            self.PRR_DIMENSIONS,
            prr_signals,
            as_of=as_of,
            composite_policy=composite_policy,
        )

    def _evaluate_dimensions(
        self,
        required_dimensions: Tuple[str, ...],
        signals: Mapping[str, EvidenceSignal],
        *,
        as_of: datetime,
        composite_policy: Optional[CompositePolicy],
    ) -> RiskAssessment:
        self._validate_as_of(as_of)

        missing = tuple(name for name in required_dimensions if name not in signals)
        unknown = tuple(
            name
            for name in required_dimensions
            if name in signals and signals[name].value is None
        )
        if missing or unknown:
            reasons = tuple("missing:" + name for name in missing) + tuple(
                "unknown:" + name for name in unknown
            )
            return RiskAssessment(
                status=AssessmentStatus.UNKNOWN,
                dimensions=self._known_dimensions(required_dimensions, signals),
                composite_score=None,
                evidence_confidence=self._minimum_confidence(required_dimensions, signals),
                reasons=reasons,
            )

        evidence_failures = self._evidence_failures(required_dimensions, signals, as_of)
        dimensions = {
            name: float(signals[name].value)  # guarded above against None
            for name in required_dimensions
        }
        confidence = min(signals[name].confidence for name in required_dimensions)
        if evidence_failures:
            return RiskAssessment(
                status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
                dimensions=dimensions,
                composite_score=None,
                evidence_confidence=confidence,
                reasons=evidence_failures,
            )

        if composite_policy is None or not composite_policy.calibrated:
            reason = (
                "no_calibrated_composite_policy"
                if composite_policy is None
                else "composite_policy_not_calibrated"
            )
            return RiskAssessment(
                status=AssessmentStatus.COMPONENTS_ONLY,
                dimensions=dimensions,
                composite_score=None,
                evidence_confidence=confidence,
                reasons=(reason,),
            )

        self._validate_composite_policy(required_dimensions, composite_policy)
        score = self._weighted_geometric(dimensions, composite_policy.weights)
        return RiskAssessment(
            status=AssessmentStatus.SCORED,
            dimensions=dimensions,
            composite_score=score,
            evidence_confidence=confidence,
            reasons=(),
            calibration_ref=composite_policy.calibration_ref,
        )

    def _evidence_failures(
        self,
        required_dimensions: Tuple[str, ...],
        signals: Mapping[str, EvidenceSignal],
        as_of: datetime,
    ) -> Tuple[str, ...]:
        failures = []
        max_age = timedelta(days=self.evidence_policy.max_age_days)
        for name in required_dimensions:
            signal = signals[name]
            if signal.observed_at > as_of:
                failures.append("future_observation:" + name)
            elif as_of - signal.observed_at > max_age:
                failures.append("stale:" + name)
            if self.evidence_policy.require_source and not signal.source.strip():
                failures.append("missing_source:" + name)
            if (
                self.evidence_policy.require_provenance_digest
                and not signal.provenance_digest.strip()
            ):
                failures.append("missing_provenance:" + name)
            if signal.confidence < self.evidence_policy.min_confidence:
                failures.append("low_confidence:" + name)
        return tuple(failures)

    @staticmethod
    def _validate_as_of(as_of: datetime) -> None:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise TransitionRiskInputError("as_of must be timezone-aware")

    @staticmethod
    def _known_dimensions(
        required_dimensions: Tuple[str, ...],
        signals: Mapping[str, EvidenceSignal],
    ) -> Dict[str, float]:
        return {
            name: float(signals[name].value)
            for name in required_dimensions
            if name in signals and signals[name].value is not None
        }

    @staticmethod
    def _minimum_confidence(
        required_dimensions: Tuple[str, ...],
        signals: Mapping[str, EvidenceSignal],
    ) -> Optional[float]:
        confidences = [
            signals[name].confidence
            for name in required_dimensions
            if name in signals and signals[name].value is not None
        ]
        return min(confidences) if confidences else None

    @staticmethod
    def _validate_composite_policy(
        required_dimensions: Tuple[str, ...],
        policy: CompositePolicy,
    ) -> None:
        if policy.method != "weighted_geometric":
            raise TransitionRiskInputError("unsupported composite method")
        if not policy.calibration_ref.strip():
            raise TransitionRiskInputError(
                "calibration_ref is required for calibrated composite policy"
            )
        if set(policy.weights) != set(required_dimensions):
            raise TransitionRiskInputError(
                "composite weights must cover exactly the required dimensions"
            )
        if any(weight <= 0.0 for weight in policy.weights.values()):
            raise TransitionRiskInputError("composite weights must be positive")
        if abs(sum(policy.weights.values()) - 1.0) > 1e-9:
            raise TransitionRiskInputError("composite weights must sum to 1.0")

    @staticmethod
    def _weighted_geometric(
        dimensions: Mapping[str, float],
        weights: Mapping[str, float],
    ) -> float:
        """Non-linear interaction preserving weak dimensions without offsets."""

        return float(prod(dimensions[name] ** weights[name] for name in dimensions))


__all__ = [
    "AITransitionRiskEvaluator",
    "AssessmentStatus",
    "CompositePolicy",
    "EvidencePolicy",
    "EvidenceSignal",
    "RiskAssessment",
    "TransitionRiskInputError",
]
