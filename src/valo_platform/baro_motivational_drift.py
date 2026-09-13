"""
BARO Motivational Drift Observer — EXPERIMENTAL / SHADOW MODE (valo-platform #448)

Explores whether deVinery's Desire Signature framework can be represented as an
upstream observational signal for agentic and institutional behaviour.

===============================================================================
EXPERIMENTAL / SHADOW MODE — READ THIS BEFORE USE
===============================================================================
This module is an EXPERIMENTAL BARO OBSERVER. The Desire Signature framework is
conceptual and phenomenological, NOT a validated scientific model of agent
psychology. This module:

- Observes behavioural patterns and emits evidence (BARO layer only).
- NEVER decides whether an action is allowed. No "admissible", "allow", or
  "deny" field appears in any output.
- Is explicitly falsifiable: confidence < 1.0, all metrics carry uncertainty.
- Must remain experimental until independently validated against downstream
  decisions and failures (per issue #448 validation plan).

Architectural boundaries (#448):

    Observed behaviour
        ↓
    Motivational Drift signal  ←  THIS MODULE
        ↓
    BARO RealityPackage
        ↓
    VAIG contextual evaluation
        ↓
    REHT admissibility decision
        ↓
    ACS evidence + receipt

===============================================================================
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ESTIMATOR_VERSION = "0.1.0-experimental-shadow"

# ---------------------------------------------------------------------------
# Durable Tensions ontology (from #448)
# ---------------------------------------------------------------------------


class DurableTension(str, Enum):
    """Canonical durable tensions observed as repeated value trade-offs."""

    EFFICIENCY_VS_HUMAN_CONTROL = "efficiency_vs_human_control"
    SAFETY_VS_FREEDOM = "safety_vs_freedom"
    CONSENSUS_VS_TRUTH = "consensus_vs_truth"
    STABILITY_VS_ADAPTATION = "stability_vs_adaptation"
    AUTONOMY_VS_ACCOUNTABILITY = "autonomy_vs_accountability"
    GROWTH_VS_INTEGRITY = "growth_vs_integrity"
    MEMORY_VS_FORGETTING = "memory_vs_forgetting"
    RULE_COMPLIANCE_VS_JUDGMENT = "rule_compliance_vs_judgment"


class CollapsePattern(str, Enum):
    """Expected collapse patterns when a tension is repeatedly subordinated."""

    CONTROL_DISPLACEMENT = "control_displacement"
    """Efficiency repeatedly subordinates human control — system automates oversight away."""
    RECKLESS_SAFETY = "reckless_safety"
    """Safety repeatedly subordinates freedom — system becomes paralysed or brittle."""
    ECHO_CHAMBER = "echo_chamber"
    """Consensus repeatedly subordinates truth — system stops detecting error."""
    RIGIDITY_SPIRAL = "rigidity_spiral"
    """Stability repeatedly subordinates adaptation — system cannot respond to change."""
    ACCOUNTABILITY_VOID = "accountability_void"
    """Autonomy repeatedly subordinates accountability — system acts without oversight."""
    EROSION = "erosion"
    """Growth repeatedly subordinates integrity — system degrades its own foundations."""
    AMNESIA = "amnesia"
    """Forgetting repeatedly subordinates memory — system loses its history."""
    LEGALISM = "legalism"
    """Rule compliance repeatedly subordinates judgment — system cannot exercise discretion."""


@dataclass
class ValuePair:
    """A single value-tension observation: one value being subordinated to another."""

    dominant: str
    subordinated: str
    tension: str
    count: int = 1
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dominant": self.dominant,
            "subordinated": self.subordinated,
            "tension": self.tension,
            "count": self.count,
            "confidence": round(self.confidence, 4),
        }


# ---------------------------------------------------------------------------
# Observation output
# ---------------------------------------------------------------------------


@dataclass
class MotivationalDriftObservation:
    """Single BARO observation of motivational direction.

    This is an OBSERVATION — it carries evidence, not decisions.
    """

    # Signal identity
    signal_type: str = "motivational_drift"
    subject_id: str = ""
    model: str = "desire_signature_v0"
    mode: str = "experimental_shadow"
    estimator_version: str = ESTIMATOR_VERSION

    # Core metrics (#448 spec)
    dominant_value: Optional[str] = None
    subordinated_value: Optional[str] = None
    tension: Optional[str] = None
    drift_score: Optional[float] = None
    persistence: Optional[float] = None
    collapse_pattern: Optional[str] = None
    confidence: float = 0.0

    # Candidate metrics (#448)
    value_asymmetry_score: Optional[float] = None
    """Magnitude of asymmetry between dominant and subordinated."""
    tension_suppression_score: Optional[float] = None
    """How much the tension is being suppressed rather than resolved."""
    compensation_pattern_score: Optional[float] = None
    """Evidence of compensating strategies to mask the drift."""
    pattern_persistence: Optional[float] = None
    """How consistently the pattern appears over observed window."""
    collapse_proximity: Optional[float] = None
    """How close the system appears to the expected collapse pattern."""
    directional_stability: Optional[float] = None
    """How stable the drift direction is (low = oscillating)."""
    evidence_confidence: Optional[float] = None
    """Confidence in the evidence base, independent of the model."""

    # Evidence
    observations: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    value_history: List[ValuePair] = field(default_factory=list)
    uncertainty: Dict[str, float] = field(default_factory=dict)

    # Provenance
    observation_window: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Rejection
    rejected: bool = False
    rejection_reason: Optional[str] = None

    def as_reality_package(self) -> Dict[str, Any]:
        """Fragment appended to BARO RealityPackage for VAIG consumption.

        Per #448 architecture: BARO observes → RealityPackage → VAIG evaluates
        → REHT decides → ACS stores.
        """
        return {
            "observer": "baro_motivational_drift",
            "model": self.model,
            "mode": self.mode,
            "estimator_version": self.estimator_version,
            "signal_type": self.signal_type,
            "subject_id": self.subject_id,
            "dominant_value": self.dominant_value,
            "subordinated_value": self.subordinated_value,
            "tension": self.tension,
            "drift_score": self.drift_score,
            "persistence": self.persistence,
            "collapse_pattern": self.collapse_pattern,
            "confidence": round(self.confidence, 4),
            "value_asymmetry_score": self.value_asymmetry_score,
            "tension_suppression_score": self.tension_suppression_score,
            "compensation_pattern_score": self.compensation_pattern_score,
            "pattern_persistence": self.pattern_persistence,
            "collapse_proximity": self.collapse_proximity,
            "directional_stability": self.directional_stability,
            "evidence_confidence": self.evidence_confidence,
            "observations": self.observations,
            "evidence_refs": self.evidence_refs,
            "uncertainty": {k: round(v, 4) for k, v in self.uncertainty.items()},
            "value_history": [v.to_dict() for v in self.value_history],
            "observation_window": self.observation_window,
            "timestamp": self.timestamp.isoformat(),
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
            # NOTE: observation only — no decision/allow/deny.
        }

    def signature(self) -> str:
        """Deterministic replay signature independent of observation time."""
        replay_payload = self.as_reality_package()
        replay_payload.pop("timestamp", None)
        payload = json.dumps(replay_payload, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Observing behaviour → value-pair mapping
# ---------------------------------------------------------------------------

# Predefined tension → collapse pattern map
_TENSION_COLLAPSE_MAP: Dict[str, str] = {
    DurableTension.EFFICIENCY_VS_HUMAN_CONTROL.value: CollapsePattern.CONTROL_DISPLACEMENT.value,
    DurableTension.SAFETY_VS_FREEDOM.value: CollapsePattern.RECKLESS_SAFETY.value,
    DurableTension.CONSENSUS_VS_TRUTH.value: CollapsePattern.ECHO_CHAMBER.value,
    DurableTension.STABILITY_VS_ADAPTATION.value: CollapsePattern.RIGIDITY_SPIRAL.value,
    DurableTension.AUTONOMY_VS_ACCOUNTABILITY.value: CollapsePattern.ACCOUNTABILITY_VOID.value,
    DurableTension.GROWTH_VS_INTEGRITY.value: CollapsePattern.EROSION.value,
    DurableTension.MEMORY_VS_FORGETTING.value: CollapsePattern.AMNESIA.value,
    DurableTension.RULE_COMPLIANCE_VS_JUDGMENT.value: CollapsePattern.LEGALISM.value,
}


def _tension_from_values(dominant: str, subordinated: str) -> Optional[str]:
    """Match a (dominant, subordinated) pair to a canonical durable tension."""
    for tension in DurableTension:
        expected_dominant, expected_sub = tension.value.split("_vs_")
        if (dominant == expected_dominant and subordinated == expected_sub) or (
            dominant == expected_sub and subordinated == expected_dominant
        ):
            return tension.value
    return None


class MotivationalDriftObserver:
    """BARO observer that detects motivational direction from behaviour history.

    EXPERIMENTAL / SHADOW MODE. Observes repeated value trade-offs in a sequence
    of observed behaviours. Produces a MotivationalDriftObservation with all
    candidate metrics from #448.

    Usage::

        observer = MotivationalDriftObserver()
        obs = observer.observe(
            subject_id="agent-alpha",
            behaviour_pairs=[
                ValuePair("efficiency", "human_control", "efficiency_vs_human_control"),
                ...
            ],
        )
        # obs contains evidence only — no admissibility decision.
    """

    def __init__(self) -> None:
        self._replay: List[ValuePair] = []

    def observe(
        self,
        subject_id: str,
        behaviour_pairs: List[ValuePair],
        observation_window: Optional[float] = None,
    ) -> MotivationalDriftObservation:
        """Analyse a window of value-pair observations for motivational drift.

        Args:
            subject_id: The agent/system being observed.
            behaviour_pairs: Observed value trade-offs (BARO raw input).
            observation_window: Time window in seconds (if known).

        Returns:
            MotivationalDriftObservation — evidence only, no decision.
        """
        n = len(behaviour_pairs)
        total_count = sum(vp.count for vp in behaviour_pairs)
        if n == 0:
            return MotivationalDriftObservation(
                rejected=True,
                rejection_reason="no_behaviour_pairs",
                subject_id=subject_id,
            )

        self._replay = list(behaviour_pairs)

        # Aggregate: find the most frequent value tension
        tension_counts: Dict[str, int] = {}
        tension_pairs: Dict[str, List[ValuePair]] = {}
        for vp in behaviour_pairs:
            tension_counts[vp.tension] = tension_counts.get(vp.tension, 0) + vp.count
            if vp.tension not in tension_pairs:
                tension_pairs[vp.tension] = []
            tension_pairs[vp.tension].append(vp)

        if not tension_counts:
            return MotivationalDriftObservation(
                rejected=True,
                rejection_reason="no_identifiable_tension",
                subject_id=subject_id,
            )

        # Dominant tension (most frequently observed)
        dominant_tension = max(tension_counts, key=lambda t: tension_counts[t])
        dominant_count = tension_counts[dominant_tension]
        total_count = sum(tension_counts.values())

        # Determine the observed dominant direction within the winning tension.
        direction_counts: Dict[Tuple[str, str], int] = {}
        for pair in tension_pairs[dominant_tension]:
            direction = (pair.dominant, pair.subordinated)
            direction_counts[direction] = direction_counts.get(direction, 0) + pair.count
        dominant_val, subordinated_val = min(
            direction_counts,
            key=lambda direction: (-direction_counts[direction], direction),
        )

        # --- Core metrics ---

        # Drift score: proportion of total behaviour count that falls under
        # the dominant tension
        drift_score = dominant_count / total_count if total_count > 0 else 0.0

        # Persistence: how consistently the dominant tension appears
        # across the window (ratio of items it appears in)
        persistence = sum(
            1 for vp in behaviour_pairs if vp.tension == dominant_tension
        ) / max(n, 1)

        # Value asymmetry: how lopsided the value subordination is within
        # the dominant tension
        asymmetry_vals = [vp for vp in behaviour_pairs if vp.tension == dominant_tension]
        if asymmetry_vals:
            total_asym = sum(vp.count for vp in asymmetry_vals)
            dominant_asym = sum(
                vp.count for vp in asymmetry_vals if vp.dominant == dominant_val
            )
            value_asymmetry = (
                abs(dominant_asym / total_asym - 0.5) * 2.0 if total_asym > 0 else 0.0
            )
        else:
            value_asymmetry = 0.0

        # Tension suppression: ratio of tensions NOT being addressed (observed
        # but not dominant / never observed)
        observed_tensions = set(tension_counts.keys())
        all_tensions = {t.value for t in DurableTension}
        suppressed_count = len(all_tensions - observed_tensions)
        tension_suppression = suppressed_count / len(all_tensions) if all_tensions else 0.0

        # Compensation pattern: proxy — low-value-tension diversity alongside
        # high drift suggests compensating behaviour
        compensation = 0.0
        if len(observed_tensions) <= 2 and drift_score > 0.6:
            compensation = min(1.0, drift_score * (1.0 - len(observed_tensions) / len(all_tensions)))

        # Pattern persistence (same as persistence for single window)
        pattern_persistence = persistence

        # Collapse proximity: how close the drift is to a known collapse pattern
        canonical_dominant = dominant_tension.split("_vs_", maxsplit=1)[0]
        direction_has_strict_majority = (
            direction_counts[(dominant_val, subordinated_val)] * 2
            > sum(direction_counts.values())
        )
        expected_collapse = (
            _TENSION_COLLAPSE_MAP.get(dominant_tension)
            if dominant_val == canonical_dominant and direction_has_strict_majority
            else None
        )
        collapse_proximity = (
            min(1.0, drift_score * 1.2)
            if expected_collapse is not None
            else 0.0
        )

        # Directional stability: how consistently the same tension dominates
        # (maximally stable if same tension dominates all observations)
        directional_stability = drift_score

        # Evidence confidence: based on total observation count
        # Scales from 0.5 (1 total count) toward 1.0 (20+ total count)
        evidence_confidence = min(1.0, 0.5 + (total_count - 1) * 0.0254)

        # Model confidence (aggregate)
        raw_confidence = (
            drift_score * 0.3
            + value_asymmetry * 0.2
            + pattern_persistence * 0.2
            + evidence_confidence * 0.3
        )
        model_confidence = min(0.99, max(0.0, raw_confidence))

        uncertainty = {
            "drift_score_std": round(0.15 / (1.0 + n * 0.1), 4),
            "persistence_std": round(0.1 / (1.0 + n * 0.05), 4),
            "asymmetry_std": round(0.2 / (1.0 + n * 0.05), 4),
        }

        obs = MotivationalDriftObservation(
            subject_id=subject_id,
            dominant_value=dominant_val,
            subordinated_value=subordinated_val,
            tension=dominant_tension,
            drift_score=round(drift_score, 4),
            persistence=round(persistence, 4),
            collapse_pattern=expected_collapse,
            confidence=round(model_confidence, 4),
            value_asymmetry_score=round(value_asymmetry, 4),
            tension_suppression_score=round(tension_suppression, 4),
            compensation_pattern_score=round(compensation, 4),
            pattern_persistence=round(pattern_persistence, 4),
            collapse_proximity=round(collapse_proximity, 4),
            directional_stability=round(directional_stability, 4),
            evidence_confidence=round(evidence_confidence, 4),
            observations=[
                {
                    "dominant": vp.dominant,
                    "subordinated": vp.subordinated,
                    "tension": vp.tension,
                    "count": vp.count,
                    "confidence": round(vp.confidence, 4),
                }
                for vp in behaviour_pairs
            ],
            evidence_refs=[f"obs-{i}" for i in range(n)],
            value_history=list(behaviour_pairs),
            uncertainty=uncertainty,
            observation_window=observation_window,
        )

        return obs


# ---------------------------------------------------------------------------
# Convenience: global instance
# ---------------------------------------------------------------------------

_observer: Optional[MotivationalDriftObserver] = None


def init_motivational_drift_observer() -> MotivationalDriftObserver:
    """Initialise global Motivational Drift observer."""
    global _observer
    _observer = MotivationalDriftObserver()
    return _observer


def get_motivational_drift_observer() -> MotivationalDriftObserver:
    """Get global Motivational Drift observer."""
    global _observer
    if _observer is None:
        _observer = init_motivational_drift_observer()
    return _observer
