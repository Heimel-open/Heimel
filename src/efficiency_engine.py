"""
VΛLΦ Efficiency Engine v0.1

Post-execution outcome measurement: "Did the action create expected value?"
Measures Value = Value / Token Cost (VES), calculates gain, informs learning.
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


class EfficiencyGrade(str, Enum):
    """Efficiency assessment."""
    EXCELLENT = "EXCELLENT"  # VES > 2.0x expected
    GOOD = "GOOD"  # VES within expected range
    ACCEPTABLE = "ACCEPTABLE"  # VES slightly below expected
    POOR = "POOR"  # VES significantly below expected
    FAILURE = "FAILURE"  # No measurable value


class OutcomeStatus(str, Enum):
    """Action outcome assessment."""
    SUCCESS = "SUCCESS"  # Objective achieved
    PARTIAL = "PARTIAL"  # Partial objective achievement
    FAILED = "FAILED"  # Objective not achieved
    SIDE_EFFECTS = "SIDE_EFFECTS"  # Achieved but with negative consequences
    UNKNOWN = "UNKNOWN"  # Outcome not yet measurable


@dataclass
class ActionExecution:
    """Post-execution record."""
    action_id: str
    category: str
    initiated_by: str  # User, team, or agent
    initiated_at: datetime
    completed_at: datetime
    tokens_used: int
    cost_actual_usd: Decimal
    outcome: OutcomeStatus = OutcomeStatus.UNKNOWN
    metadata: Dict = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        delta = self.completed_at - self.initiated_at
        return delta.total_seconds()

    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "category": self.category,
            "initiated_by": self.initiated_by,
            "initiated_at": self.initiated_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "tokens_used": self.tokens_used,
            "cost_actual_usd": float(self.cost_actual_usd),
            "outcome": self.outcome.value,
            "metadata": self.metadata,
        }


@dataclass
class ValueMeasurement:
    """Measured outcome value."""
    revenue_generated: Decimal = Decimal("0")  # Direct revenue
    cost_avoided: Decimal = Decimal("0")  # Cost savings achieved
    labor_saved_hours: float = 0.0  # Human labor hours saved
    risk_mitigated: Decimal = Decimal("0")  # Risk reduction value
    strategic_value: Decimal = Decimal("0")  # Long-term strategic value
    negative_value: Decimal = Decimal("0")  # Negative consequences (harm, risk increase)

    @property
    def total_positive_value(self) -> Decimal:
        labor_value = Decimal(str(self.labor_saved_hours * 100))  # $100/hour
        return self.revenue_generated + self.cost_avoided + labor_value + self.risk_mitigated + self.strategic_value

    @property
    def net_value(self) -> Decimal:
        return self.total_positive_value - self.negative_value

    def to_dict(self) -> Dict:
        return {
            "revenue_generated": float(self.revenue_generated),
            "cost_avoided": float(self.cost_avoided),
            "labor_saved_hours": self.labor_saved_hours,
            "labor_value_usd": float(Decimal(str(self.labor_saved_hours * 100))),
            "risk_mitigated": float(self.risk_mitigated),
            "strategic_value": float(self.strategic_value),
            "negative_value": float(self.negative_value),
            "total_positive_value": float(self.total_positive_value),
            "net_value": float(self.net_value),
        }


@dataclass
class EfficiencyMetric:
    """Efficiency measurement result."""
    action_id: str
    execution: ActionExecution
    value: ValueMeasurement
    expected_value: Decimal
    actual_value: Decimal
    ves_ratio: Decimal  # Value / Token Cost ratio
    expected_ves: Decimal
    efficiency_grade: EfficiencyGrade
    confidence: str  # "claimed", "estimated", "measured"
    variance_pct: float  # Percentage deviation from expected
    rationale: str
    learning_signal: str  # Insight for model improvement
    hash: str = ""
    timestamp: datetime = field(default_factory=_utcnow)

    def compute_hash(self) -> str:
        """Compute SHA256 for audit trail."""
        data = f"{self.action_id}{self.ves_ratio}{self.efficiency_grade.value}{self.timestamp.isoformat()}".encode()
        return hashlib.sha256(data).hexdigest()

    def __post_init__(self):
        if not self.hash:
            self.hash = self.compute_hash()

    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "execution": self.execution.to_dict(),
            "value": self.value.to_dict(),
            "expected_value_usd": float(self.expected_value),
            "actual_value_usd": float(self.actual_value),
            "ves_ratio": float(self.ves_ratio),
            "expected_ves": float(self.expected_ves),
            "efficiency_grade": self.efficiency_grade.value,
            "confidence": self.confidence,
            "variance_pct": self.variance_pct,
            "rationale": self.rationale,
            "learning_signal": self.learning_signal,
            "hash": self.hash,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EfficiencyPolicy:
    """Policy for efficiency measurement."""
    expected_ves_baseline: Decimal = Decimal("0.5")  # Baseline value per token cost
    excellent_threshold: Decimal = Decimal("2.0")  # 2x or better
    good_threshold: Decimal = Decimal("1.0")  # 1x or better
    acceptable_threshold: Decimal = Decimal("0.7")  # 0.7x or better
    poor_threshold: Decimal = Decimal("0.3")  # Below 0.3x is poor

    confidence_threshold_measured: int = 10  # Measured if observed in N+ cases
    attribution_window_days: int = 30  # Window to measure outcomes


class EfficiencyEngine:
    """VΛLΦ Efficiency Engine: Post-execution outcome measurement."""

    def __init__(self, policy: EfficiencyPolicy = None):
        self.policy = policy or EfficiencyPolicy()
        self.executions: Dict[str, ActionExecution] = {}
        self.measurements: List[EfficiencyMetric] = []
        self.confidence_tracker: Dict[str, int] = {}  # Count observations per action type

    def record_execution(self, action_id: str, execution: ActionExecution):
        """Record that an action was executed."""
        self.executions[action_id] = execution

    def measure_outcome(self, action_id: str, value: ValueMeasurement,
                       expected_value: Decimal) -> EfficiencyMetric:
        """
        Measure actual outcome against expected value.

        Returns:
            EfficiencyMetric with calculated VES and efficiency grade
        """
        if action_id not in self.executions:
            raise ValueError(f"No execution record for {action_id}")

        execution = self.executions[action_id]

        # Calculate actual value
        actual_value = value.net_value
        cost_usd = execution.cost_actual_usd

        # Calculate VES (Value per Token Cost)
        if cost_usd == 0:
            ves = Decimal("999")  # Free actions get max VES
        else:
            ves = actual_value / cost_usd

        expected_ves = expected_value / cost_usd if cost_usd > 0 else Decimal("999")

        # Determine efficiency grade
        grade = self._grade_efficiency(ves)

        # Calculate variance
        if expected_value > 0:
            variance = ((actual_value - expected_value) / expected_value) * 100
        else:
            variance = 0.0

        # Update confidence tracker
        self._update_confidence(action_id)
        confidence = self._get_confidence(action_id)

        # Generate learning signal
        learning = self._generate_learning_signal(
            action_id=action_id,
            grade=grade,
            variance=variance,
            outcome=execution.outcome,
            value=value
        )

        metric = EfficiencyMetric(
            action_id=action_id,
            execution=execution,
            value=value,
            expected_value=expected_value,
            actual_value=actual_value,
            ves_ratio=ves,
            expected_ves=expected_ves,
            efficiency_grade=grade,
            confidence=confidence,
            variance_pct=variance,
            rationale=f"VES {ves:.2f}x (actual ${actual_value:.2f} / cost ${cost_usd:.2f})",
            learning_signal=learning,
        )

        self.measurements.append(metric)
        return metric

    def _grade_efficiency(self, ves: Decimal) -> EfficiencyGrade:
        """Assign efficiency grade based on VES."""
        if ves >= self.policy.excellent_threshold:
            return EfficiencyGrade.EXCELLENT
        elif ves >= self.policy.good_threshold:
            return EfficiencyGrade.GOOD
        elif ves >= self.policy.acceptable_threshold:
            return EfficiencyGrade.ACCEPTABLE
        elif ves >= self.policy.poor_threshold:
            return EfficiencyGrade.POOR
        else:
            return EfficiencyGrade.FAILURE

    def _update_confidence(self, action_id: str):
        """Track observation count for action type."""
        if action_id not in self.confidence_tracker:
            self.confidence_tracker[action_id] = 0
        self.confidence_tracker[action_id] += 1

    def _get_confidence(self, action_id: str) -> str:
        """Determine confidence level based on observation count."""
        count = self.confidence_tracker.get(action_id, 0)
        if count >= self.policy.confidence_threshold_measured:
            return "measured"
        elif count >= 3:
            return "estimated"
        else:
            return "claimed"

    def _generate_learning_signal(self, action_id: str, grade: EfficiencyGrade,
                                  variance: float, outcome: OutcomeStatus,
                                  value: ValueMeasurement) -> str:
        """Generate insight for model improvement."""
        if grade == EfficiencyGrade.EXCELLENT:
            return f"Excellent outcome: {outcome.value}. Prioritize this pattern."
        elif grade == EfficiencyGrade.FAILURE:
            if outcome == OutcomeStatus.FAILED:
                return "Action failed to achieve objective. Review approach."
            elif value.negative_value > 0:
                return f"Negative consequences: ${value.negative_value:.2f}. Avoid pattern."
            else:
                return f"Efficiency poor ({variance:.0f}% below expected). Revisit model."
        elif variance > 50:
            return f"Variance high (+{variance:.0f}%). Excellent execution: replicate."
        elif variance < -50:
            return f"Variance high ({variance:.0f}%). Poor execution: debug approach."
        else:
            return f"Within expected range. Outcome: {outcome.value}."

    def get_measurements_by_action(self, action_id: str) -> List[EfficiencyMetric]:
        """Get all measurements for specific action."""
        return [m for m in self.measurements if m.action_id == action_id]

    def get_category_efficiency(self, category: str) -> Dict:
        """Get aggregate efficiency by category."""
        category_measurements = [
            m for m in self.measurements
            if m.execution.category == category
        ]

        if not category_measurements:
            return {"category": category, "sample_size": 0}

        ves_scores = [float(m.ves_ratio) for m in category_measurements]
        avg_ves = sum(ves_scores) / len(ves_scores)
        grades = [m.efficiency_grade.value for m in category_measurements]
        excellent_pct = (grades.count(EfficiencyGrade.EXCELLENT.value) / len(grades)) * 100

        return {
            "category": category,
            "sample_size": len(category_measurements),
            "avg_ves": avg_ves,
            "excellent_pct": excellent_pct,
            "measurements": [m.to_dict() for m in category_measurements],
        }

    def get_measurement_log(self) -> List[Dict]:
        """Return all measurements as dicts."""
        return [m.to_dict() for m in self.measurements]

    @property
    def measurement_log(self) -> List[EfficiencyMetric]:
        """Property accessor for measurements (audit trail)."""
        return self.measurements
