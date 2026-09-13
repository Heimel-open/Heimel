"""Bounded hostile evidence/evaluation grammar for VAIG.

The contract is deliberately evaluation-only. It preserves source lineage,
unknowns, contradictions, residual duty, reversible next gates and adversarial
replay without creating execution authority. REHT remains the sole downstream
execution-authorization boundary.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable


class EvidenceGrade(str, Enum):
    OBSERVATION = "O"
    INFERENCE = "I"
    HYPOTHESIS = "H"
    PROTOCOL = "P"
    SPECULATION = "S"
    UNKNOWN = "U"


class EvaluationStatus(str, Enum):
    PASS = "PASS"
    OPEN = "OPEN"
    FAIL = "FAIL"


class MetricComparison(str, Enum):
    """Declared direction for a preregistered numeric threshold."""

    GTE = "GTE"
    LTE = "LTE"


class ReplayOperator(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    ADVERSARIAL = "ADVERSARIAL"
    UNKNOWN = "UNKNOWN"


class SourceClass(str, Enum):
    PRIMARY = "PRIMARY"
    INDEPENDENT_AUDIT = "INDEPENDENT_AUDIT"
    SECONDARY = "SECONDARY"
    COMMENTARY = "COMMENTARY"
    PROTECTED = "PROTECTED"
    UNKNOWN = "UNKNOWN"


class SourceAccess(str, Enum):
    PUBLIC = "PUBLIC"
    PROTECTED = "PROTECTED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class EvidenceSourceV1:
    source_id: str
    title: str
    source_class: SourceClass
    access: SourceAccess = SourceAccess.PUBLIC
    owner: str | None = None
    date: str | None = None
    locator: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.title.strip():
            raise ValueError("source title must not be empty")
        object.__setattr__(self, "limitations", _clean_tuple(self.limitations))


@dataclass(frozen=True)
class EvaluationBoundaryV1:
    object_id: str
    scope: str
    time_window: str
    decision_question: str
    geography: str | None = None
    exclusions: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    native_standard_refs: tuple[str, ...] = ()
    interfaces: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("object_id", "scope", "time_window", "decision_question"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        object.__setattr__(self, "exclusions", _clean_tuple(self.exclusions))
        object.__setattr__(self, "authority_refs", _clean_tuple(self.authority_refs))
        object.__setattr__(self, "native_standard_refs", _clean_tuple(self.native_standard_refs))
        object.__setattr__(self, "interfaces", _clean_tuple(self.interfaces))


@dataclass(frozen=True)
class EvidenceClaimV1:
    text: str
    grade: EvidenceGrade
    source_ref: str | None = None
    as_of: str | None = None
    assumptions: tuple[str, ...] = ()
    claim_id: str | None = None
    confidence: float | None = None
    contradiction_refs: tuple[str, ...] = ()
    counter_source_search_performed: bool = False
    material: bool = True

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("claim text must not be empty")
        object.__setattr__(self, "assumptions", _clean_tuple(self.assumptions))
        object.__setattr__(self, "contradiction_refs", _clean_tuple(self.contradiction_refs))
        if self.confidence is not None and not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("claim confidence must be within [0, 1]")
        if self.grade is EvidenceGrade.OBSERVATION:
            if not self.source_ref or not self.source_ref.strip():
                raise ValueError("observations require source_ref")
            if not self.as_of or not self.as_of.strip():
                raise ValueError("observations require as_of")
        if self.grade is EvidenceGrade.INFERENCE and not self.assumptions:
            raise ValueError("inferences require explicit assumptions")
        if self.grade is EvidenceGrade.HYPOTHESIS and not self.assumptions:
            raise ValueError("hypotheses require explicit assumptions")


@dataclass(frozen=True)
class MetricV1:
    name: str
    unit: str
    threshold: float | None
    source_ref: str | None
    observed_value: float | None = None
    comparison: MetricComparison | None = None
    locked_before_outcome: bool = True
    metric_id: str | None = None
    baseline: float | None = None
    window: str | None = None
    gaming_risk: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("metric name must not be empty")
        if not self.unit.strip():
            raise ValueError("metric unit must not be empty")
        if self.comparison is not None and not isinstance(self.comparison, MetricComparison):
            object.__setattr__(self, "comparison", MetricComparison(str(self.comparison)))
        for field in ("threshold", "observed_value", "baseline"):
            value = getattr(self, field)
            if value is None:
                continue
            if isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError(f"metric {field} must be a finite number")


@dataclass(frozen=True)
class ObserverV1:
    actor: str
    role: str
    incentives: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.actor.strip():
            raise ValueError("observer actor must not be empty")
        if not self.role.strip():
            raise ValueError("observer role must not be empty")
        object.__setattr__(self, "incentives", _clean_tuple(self.incentives))
        object.__setattr__(self, "conflicts", _clean_tuple(self.conflicts))


@dataclass(frozen=True)
class FeedbackLoopV1:
    sensor: str
    threshold_ref: str
    action: str
    observed_effect: str | None = None
    verifier: str | None = None
    latency: str | None = None

    def __post_init__(self) -> None:
        for name in ("sensor", "threshold_ref", "action"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"feedback {name} must not be empty")


@dataclass(frozen=True)
class ResidualV1:
    risk: str
    status: str
    owner: str | None = None
    due: str | None = None
    residual_id: str | None = None
    bearer: str | None = None
    magnitude: float | None = None
    unit: str | None = None
    uncertainty: str | None = None
    evidence_refs: tuple[str, ...] = ()
    escalation_path: str | None = None

    def __post_init__(self) -> None:
        if not self.risk.strip():
            raise ValueError("residual risk must not be empty")
        normalized = self.status.strip().upper()
        if normalized not in {"OPEN", "CLOSED", "ESCALATED"}:
            raise ValueError("residual status must be OPEN, CLOSED or ESCALATED")
        object.__setattr__(self, "status", normalized)
        object.__setattr__(self, "evidence_refs", _clean_tuple(self.evidence_refs))


@dataclass(frozen=True)
class DutyV1:
    residual_risk: str
    accountable_role: str
    cadence: str | None = None
    escalation_path: str | None = None

    def __post_init__(self) -> None:
        if not self.residual_risk.strip():
            raise ValueError("duty residual_risk must not be empty")
        if not self.accountable_role.strip():
            raise ValueError("duty accountable_role must not be empty")


@dataclass(frozen=True)
class InverseTestV1:
    baseline: str
    counterfactual: str
    inverse_of_inverse: str
    metric_ref: str | None
    prediction: str | None
    falsifier: str
    horizon: str | None = None
    confounders: tuple[str, ...] = ()
    stop_rule: str | None = None
    affected_actors: tuple[str, ...] = ()
    residual_transfer: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("baseline", "counterfactual", "inverse_of_inverse", "falsifier"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"inverse {name} must not be empty")
        object.__setattr__(self, "confounders", _clean_tuple(self.confounders))
        object.__setattr__(self, "affected_actors", _clean_tuple(self.affected_actors))
        object.__setattr__(self, "residual_transfer", _clean_tuple(self.residual_transfer))


@dataclass(frozen=True)
class NextGateV1:
    action: str
    reversible: bool
    stop_rule: str
    deadline: str | None = None
    owner: str | None = None
    verifier: str | None = None
    rollback: str | None = None
    expected_evidence: tuple[str, ...] = ()
    falsifier: str | None = None

    def __post_init__(self) -> None:
        if not self.action.strip():
            raise ValueError("next gate action must not be empty")
        if not self.reversible:
            raise ValueError("VAIG next gates must be reversible")
        if not self.stop_rule.strip():
            raise ValueError("next gate requires a stop rule")
        object.__setattr__(self, "expected_evidence", _clean_tuple(self.expected_evidence))


@dataclass(frozen=True)
class ReplayV1:
    operator: ReplayOperator
    result: EvaluationStatus
    operator_ref: str | None = None
    packet_digest: str | None = None
    packet_version: str | None = None
    blind: bool | None = None
    deltas: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.operator is not ReplayOperator.UNKNOWN:
            if not self.operator_ref or not self.operator_ref.strip():
                raise ValueError("independent/adversarial replay requires operator_ref")
        if self.packet_digest is not None and not _is_sha256(self.packet_digest):
            raise ValueError("replay packet_digest must be a sha256 binding")
        object.__setattr__(self, "deltas", _clean_tuple(self.deltas))
        object.__setattr__(self, "unresolved", _clean_tuple(self.unresolved))


@dataclass(frozen=True)
class HistoryEntryV1:
    timestamp: str
    field: str
    old: str
    new: str
    reason: str
    actor: str

    def __post_init__(self) -> None:
        for name in ("timestamp", "field", "reason", "actor"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"history {name} must not be empty")


@dataclass(frozen=True)
class CoherenceEvaluationInputV1:
    boundary: EvaluationBoundaryV1
    claims: tuple[EvidenceClaimV1, ...]
    metrics: tuple[MetricV1, ...]
    observers: tuple[ObserverV1, ...]
    continuation_dependencies: tuple[str, ...]
    feedback_loops: tuple[FeedbackLoopV1, ...]
    residuals: tuple[ResidualV1, ...]
    falsifier: str
    next_gate: NextGateV1
    replay: ReplayV1
    claims_correction: bool = False
    high_stakes: bool = False
    counter_source_refs: tuple[str, ...] = ()
    sources: tuple[EvidenceSourceV1, ...] = ()
    duties: tuple[DutyV1, ...] = ()
    inverse: InverseTestV1 | None = None
    history: tuple[HistoryEntryV1, ...] = ()
    run_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "claims", tuple(self.claims))
        object.__setattr__(self, "metrics", tuple(self.metrics))
        object.__setattr__(self, "observers", tuple(self.observers))
        object.__setattr__(
            self,
            "continuation_dependencies",
            _clean_tuple(self.continuation_dependencies),
        )
        object.__setattr__(self, "feedback_loops", tuple(self.feedback_loops))
        object.__setattr__(self, "residuals", tuple(self.residuals))
        object.__setattr__(self, "counter_source_refs", _clean_tuple(self.counter_source_refs))
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "duties", tuple(self.duties))
        object.__setattr__(self, "history", tuple(self.history))
        if not self.claims:
            raise ValueError("at least one claim is required")
        if not self.metrics:
            raise ValueError("at least one metric is required")
        if not self.observers:
            raise ValueError("at least one observer is required")
        if not self.residuals:
            raise ValueError("at least one residual row is required")
        if not self.continuation_dependencies:
            raise ValueError("at least one continuation dependency is required")
        if not self.falsifier.strip():
            raise ValueError("falsifier must not be empty")
        if self.run_version < 1:
            raise ValueError("run_version must be >= 1")
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source_id values must be unique")


@dataclass(frozen=True)
class CoherenceEvaluationResultV1:
    status: EvaluationStatus
    reason_codes: tuple[str, ...]
    input_digest: str
    schema_version: str = "1.0.0"
    execution_authority: bool = False
    requires_reht_clearance: bool = True
    replay_packet_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", _clean_tuple(self.reason_codes))
        if self.schema_version != "1.0.0":
            raise ValueError("unsupported coherence evaluation schema_version")
        if self.execution_authority:
            raise ValueError("VAIG coherence evaluation cannot grant execution authority")
        if not self.requires_reht_clearance:
            raise ValueError("VAIG coherence evaluation must require REHT clearance")
        if self.status is EvaluationStatus.PASS and self.reason_codes:
            raise ValueError("PASS cannot carry blocking reason codes")
        if self.status is not EvaluationStatus.PASS and not self.reason_codes:
            raise ValueError("OPEN/FAIL require reason codes")

    @property
    def can_execute(self) -> bool:
        return False

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason_codes": list(self.reason_codes),
            "input_digest": self.input_digest,
            "replay_packet_digest": self.replay_packet_digest,
            "schema_version": self.schema_version,
            "execution_authority": False,
            "requires_reht_clearance": True,
            "can_execute": False,
        }


class CoherenceEvaluationGateV1:
    """Deterministic evaluator for the bounded hostile evaluation contract."""

    def evaluate(self, evaluation: CoherenceEvaluationInputV1) -> CoherenceEvaluationResultV1:
        fail_reasons = self._fail_reasons(evaluation)
        if fail_reasons:
            return self._result(EvaluationStatus.FAIL, fail_reasons, evaluation)

        open_reasons = self._open_reasons(evaluation)
        if open_reasons:
            return self._result(EvaluationStatus.OPEN, open_reasons, evaluation)

        return self._result(EvaluationStatus.PASS, (), evaluation)

    @staticmethod
    def _fail_reasons(evaluation: CoherenceEvaluationInputV1) -> tuple[str, ...]:
        reasons: list[str] = []
        if evaluation.replay.result is EvaluationStatus.FAIL:
            reasons.append("ADVERSARIAL_REPLAY_FAILED")
        if (
            evaluation.replay.packet_digest is not None
            and evaluation.replay.packet_digest != replay_packet_digest(evaluation)
        ):
            reasons.append("REPLAY_PACKET_BINDING_MISMATCH")
        for metric in evaluation.metrics:
            if (
                metric.threshold is None
                or metric.observed_value is None
                or metric.comparison is None
            ):
                continue
            if metric.comparison is MetricComparison.GTE and metric.observed_value < metric.threshold:
                reasons.append("METRIC_THRESHOLD_BREACH")
            elif metric.comparison is MetricComparison.LTE and metric.observed_value > metric.threshold:
                reasons.append("METRIC_THRESHOLD_BREACH")
        return _clean_tuple(reasons)

    @staticmethod
    def _open_reasons(evaluation: CoherenceEvaluationInputV1) -> tuple[str, ...]:
        reasons: list[str] = []
        source_by_id = {source.source_id: source for source in evaluation.sources}

        for metric in evaluation.metrics:
            if metric.threshold is None:
                reasons.append("METRIC_THRESHOLD_UNKNOWN")
            if metric.observed_value is None:
                reasons.append("METRIC_OBSERVATION_MISSING")
            if metric.comparison is None:
                reasons.append("METRIC_COMPARISON_UNKNOWN")
            if not metric.source_ref or not metric.source_ref.strip():
                reasons.append("METRIC_THRESHOLD_SOURCE_MISSING")
            elif metric.source_ref in source_by_id:
                if source_by_id[metric.source_ref].access is SourceAccess.UNAVAILABLE:
                    reasons.append("METRIC_SOURCE_UNAVAILABLE")
            if not metric.locked_before_outcome:
                reasons.append("METRIC_NOT_PREREGISTERED")

        if any(claim.grade is EvidenceGrade.UNKNOWN for claim in evaluation.claims):
            reasons.append("MATERIAL_EVIDENCE_UNKNOWN")

        for claim in evaluation.claims:
            if claim.source_ref and claim.source_ref in source_by_id:
                if source_by_id[claim.source_ref].access is SourceAccess.UNAVAILABLE:
                    reasons.append("SOURCE_UNAVAILABLE")

        if not evaluation.feedback_loops:
            reasons.append("FEEDBACK_LOOP_MISSING")

        if evaluation.claims_correction:
            if not evaluation.feedback_loops:
                reasons.append("CORRECTION_FEEDBACK_LOOP_MISSING")
            elif any(not loop.observed_effect for loop in evaluation.feedback_loops):
                reasons.append("CORRECTION_EFFECT_UNVERIFIED")

        duty_risks = {duty.residual_risk for duty in evaluation.duties}
        for residual in evaluation.residuals:
            if residual.status in {"OPEN", "ESCALATED"}:
                if not residual.owner or not residual.owner.strip():
                    reasons.append("OPEN_RESIDUAL_OWNER_UNKNOWN")
                if evaluation.high_stakes:
                    if not residual.bearer or not residual.bearer.strip():
                        reasons.append("OPEN_RESIDUAL_BEARER_UNKNOWN")
                    if not residual.evidence_refs:
                        reasons.append("OPEN_RESIDUAL_EVIDENCE_MISSING")
                    if residual.risk not in duty_risks:
                        reasons.append("RESIDUAL_DUTY_MISSING")

        if evaluation.run_version > 1 and not evaluation.history:
            reasons.append("REVISION_HISTORY_MISSING")

        if evaluation.high_stakes:
            for claim in evaluation.claims:
                if claim.material and not claim.counter_source_search_performed:
                    reasons.append("COUNTER_SOURCE_SEARCH_MISSING")
            if not evaluation.sources:
                reasons.append("SOURCE_REGISTER_MISSING")
            else:
                for claim in evaluation.claims:
                    if claim.source_ref and claim.source_ref not in source_by_id:
                        reasons.append("CLAIM_SOURCE_LINEAGE_MISSING")
                    if any(ref not in source_by_id for ref in claim.contradiction_refs):
                        reasons.append("CONTRADICTION_SOURCE_LINEAGE_MISSING")
                for metric in evaluation.metrics:
                    if metric.source_ref and metric.source_ref not in source_by_id:
                        reasons.append("METRIC_SOURCE_LINEAGE_MISSING")
                for ref in evaluation.counter_source_refs:
                    if ref not in source_by_id:
                        reasons.append("COUNTER_SOURCE_LINEAGE_MISSING")
            if not evaluation.counter_source_refs:
                reasons.append("COUNTER_SOURCE_MISSING")
            if not evaluation.boundary.authority_refs:
                reasons.append("AUTHORITY_SOURCE_MISSING")
            if not evaluation.boundary.native_standard_refs:
                reasons.append("NATIVE_STANDARD_CROSSWALK_MISSING")
            if evaluation.inverse is None:
                reasons.append("INVERSE_TEST_MISSING")
            else:
                if not evaluation.inverse.metric_ref:
                    reasons.append("INVERSE_METRIC_MISSING")
                if not evaluation.inverse.prediction:
                    reasons.append("INVERSE_PREDICTION_MISSING")
            if not evaluation.next_gate.owner:
                reasons.append("NEXT_GATE_OWNER_MISSING")
            if not evaluation.next_gate.verifier:
                reasons.append("NEXT_GATE_VERIFIER_MISSING")
            if not evaluation.next_gate.rollback:
                reasons.append("NEXT_GATE_ROLLBACK_MISSING")
            if not evaluation.next_gate.expected_evidence:
                reasons.append("NEXT_GATE_EXPECTED_EVIDENCE_MISSING")
            if not evaluation.next_gate.falsifier:
                reasons.append("NEXT_GATE_FALSIFIER_MISSING")
            if evaluation.replay.packet_digest is None:
                reasons.append("REPLAY_PACKET_BINDING_MISSING")
            if not evaluation.replay.packet_version:
                reasons.append("REPLAY_PACKET_VERSION_MISSING")

        if evaluation.replay.result is EvaluationStatus.OPEN:
            reasons.append("REPLAY_OPEN")
        if evaluation.replay.operator is ReplayOperator.UNKNOWN:
            reasons.append("INDEPENDENT_REPLAY_OPERATOR_UNKNOWN")
        if evaluation.replay.result is EvaluationStatus.PASS and evaluation.replay.operator not in {
            ReplayOperator.INDEPENDENT,
            ReplayOperator.ADVERSARIAL,
        }:
            reasons.append("REPLAY_NOT_INDEPENDENT")
        if evaluation.replay.unresolved:
            reasons.append("REPLAY_UNRESOLVED")

        return _clean_tuple(reasons)

    @staticmethod
    def _result(
        status: EvaluationStatus,
        reasons: Iterable[str],
        evaluation: CoherenceEvaluationInputV1,
    ) -> CoherenceEvaluationResultV1:
        return CoherenceEvaluationResultV1(
            status=status,
            reason_codes=tuple(reasons),
            input_digest=_input_digest(evaluation),
            replay_packet_digest=replay_packet_digest(evaluation),
        )


def replay_packet_digest(evaluation: CoherenceEvaluationInputV1) -> str:
    """Digest the frozen pre-replay packet, excluding replay outcome metadata."""
    payload = _jsonable(asdict(evaluation))
    payload.pop("replay", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _input_digest(evaluation: CoherenceEvaluationInputV1) -> str:
    payload = _jsonable(asdict(evaluation))
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _is_sha256(value: str) -> bool:
    if not value.startswith("sha256:") or len(value) != 71:
        return False
    try:
        int(value[7:], 16)
    except ValueError:
        return False
    return True


def _clean_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
