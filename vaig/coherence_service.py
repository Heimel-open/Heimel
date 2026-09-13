"""Transport-safe service for canonical VAIG Coherence Live-Fire evaluation.

The service accepts only the canonical evaluation contract, evaluates it inside
VAIG, and returns the existing digest-bound handoff binding. The output remains
evaluation evidence only: it cannot grant authority, clearance, or execution.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .coherence_evaluation import (
    CoherenceEvaluationGateV1,
    CoherenceEvaluationInputV1,
    DutyV1,
    EvidenceClaimV1,
    EvidenceGrade,
    EvidenceSourceV1,
    EvaluationBoundaryV1,
    EvaluationStatus,
    FeedbackLoopV1,
    HistoryEntryV1,
    InverseTestV1,
    MetricComparison,
    MetricV1,
    NextGateV1,
    ObserverV1,
    ReplayOperator,
    ReplayV1,
    ResidualV1,
    SourceAccess,
    SourceClass,
)
from .reht_handoff import CoherenceHandoffBindingV1


class CoherenceTransportError(ValueError):
    """The wire payload does not satisfy the canonical coherence contract."""


def evaluate_and_bind(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Parse, evaluate and bind one canonical coherence evaluation packet."""
    evaluation = parse_evaluation_input(payload)
    result = CoherenceEvaluationGateV1().evaluate(evaluation)
    binding = CoherenceHandoffBindingV1.from_result(result)
    return binding.canonical_payload()


def parse_evaluation_input(payload: Mapping[str, Any]) -> CoherenceEvaluationInputV1:
    root = _mapping(payload, "evaluation")
    try:
        return CoherenceEvaluationInputV1(
            boundary=_boundary(_mapping(root.get("boundary"), "boundary")),
            claims=tuple(_claim(item) for item in _mappings(root.get("claims"), "claims")),
            metrics=tuple(_metric(item) for item in _mappings(root.get("metrics"), "metrics")),
            observers=tuple(_observer(item) for item in _mappings(root.get("observers"), "observers")),
            continuation_dependencies=_strings(root.get("continuation_dependencies"), "continuation_dependencies"),
            feedback_loops=tuple(_feedback(item) for item in _mappings(root.get("feedback_loops", ()), "feedback_loops")),
            residuals=tuple(_residual(item) for item in _mappings(root.get("residuals"), "residuals")),
            falsifier=_required_text(root, "falsifier"),
            next_gate=_next_gate(_mapping(root.get("next_gate"), "next_gate")),
            replay=_replay(_mapping(root.get("replay"), "replay")),
            claims_correction=_bool(root, "claims_correction", False),
            high_stakes=_bool(root, "high_stakes", False),
            counter_source_refs=_strings(root.get("counter_source_refs", ()), "counter_source_refs"),
            sources=tuple(_source(item) for item in _mappings(root.get("sources", ()), "sources")),
            duties=tuple(_duty(item) for item in _mappings(root.get("duties", ()), "duties")),
            inverse=(
                _inverse(_mapping(root.get("inverse"), "inverse"))
                if root.get("inverse") is not None
                else None
            ),
            history=tuple(_history(item) for item in _mappings(root.get("history", ()), "history")),
            run_version=_int(root, "run_version", 1),
        )
    except (TypeError, ValueError, KeyError) as exc:
        if isinstance(exc, CoherenceTransportError):
            raise
        raise CoherenceTransportError(str(exc)) from exc


def _boundary(raw: Mapping[str, Any]) -> EvaluationBoundaryV1:
    return EvaluationBoundaryV1(
        object_id=_required_text(raw, "object_id"),
        scope=_required_text(raw, "scope"),
        time_window=_required_text(raw, "time_window"),
        decision_question=_required_text(raw, "decision_question"),
        geography=_optional_text(raw.get("geography")),
        exclusions=_strings(raw.get("exclusions", ()), "boundary.exclusions"),
        authority_refs=_strings(raw.get("authority_refs", ()), "boundary.authority_refs"),
        native_standard_refs=_strings(raw.get("native_standard_refs", ()), "boundary.native_standard_refs"),
        interfaces=_strings(raw.get("interfaces", ()), "boundary.interfaces"),
    )


def _claim(raw: Mapping[str, Any]) -> EvidenceClaimV1:
    return EvidenceClaimV1(
        text=_required_text(raw, "text"),
        grade=EvidenceGrade(_required_text(raw, "grade")),
        source_ref=_optional_text(raw.get("source_ref")),
        as_of=_optional_text(raw.get("as_of")),
        assumptions=_strings(raw.get("assumptions", ()), "claim.assumptions"),
        claim_id=_optional_text(raw.get("claim_id")),
        confidence=_optional_float(raw.get("confidence"), "claim.confidence"),
        contradiction_refs=_strings(raw.get("contradiction_refs", ()), "claim.contradiction_refs"),
        counter_source_search_performed=_bool(raw, "counter_source_search_performed", False),
        material=_bool(raw, "material", True),
    )


def _metric(raw: Mapping[str, Any]) -> MetricV1:
    comparison_raw = raw.get("comparison")
    return MetricV1(
        name=_required_text(raw, "name"),
        unit=_required_text(raw, "unit"),
        threshold=_optional_float(raw.get("threshold"), "metric.threshold"),
        source_ref=_optional_text(raw.get("source_ref")),
        observed_value=_optional_float(raw.get("observed_value"), "metric.observed_value"),
        comparison=(
            MetricComparison(_required_text(raw, "comparison"))
            if comparison_raw is not None
            else None
        ),
        locked_before_outcome=_bool(raw, "locked_before_outcome", True),
        metric_id=_optional_text(raw.get("metric_id")),
        baseline=_optional_float(raw.get("baseline"), "metric.baseline"),
        window=_optional_text(raw.get("window")),
        gaming_risk=_optional_text(raw.get("gaming_risk")),
    )


def _observer(raw: Mapping[str, Any]) -> ObserverV1:
    return ObserverV1(
        actor=_required_text(raw, "actor"),
        role=_required_text(raw, "role"),
        incentives=_strings(raw.get("incentives", ()), "observer.incentives"),
        conflicts=_strings(raw.get("conflicts", ()), "observer.conflicts"),
    )


def _feedback(raw: Mapping[str, Any]) -> FeedbackLoopV1:
    return FeedbackLoopV1(
        sensor=_required_text(raw, "sensor"),
        threshold_ref=_required_text(raw, "threshold_ref"),
        action=_required_text(raw, "action"),
        observed_effect=_optional_text(raw.get("observed_effect")),
        verifier=_optional_text(raw.get("verifier")),
        latency=_optional_text(raw.get("latency")),
    )


def _residual(raw: Mapping[str, Any]) -> ResidualV1:
    return ResidualV1(
        risk=_required_text(raw, "risk"),
        status=_required_text(raw, "status"),
        owner=_optional_text(raw.get("owner")),
        due=_optional_text(raw.get("due")),
        residual_id=_optional_text(raw.get("residual_id")),
        bearer=_optional_text(raw.get("bearer")),
        magnitude=_optional_float(raw.get("magnitude"), "residual.magnitude"),
        unit=_optional_text(raw.get("unit")),
        uncertainty=_optional_text(raw.get("uncertainty")),
        evidence_refs=_strings(raw.get("evidence_refs", ()), "residual.evidence_refs"),
        escalation_path=_optional_text(raw.get("escalation_path")),
    )


def _duty(raw: Mapping[str, Any]) -> DutyV1:
    return DutyV1(
        residual_risk=_required_text(raw, "residual_risk"),
        accountable_role=_required_text(raw, "accountable_role"),
        cadence=_optional_text(raw.get("cadence")),
        escalation_path=_optional_text(raw.get("escalation_path")),
    )


def _inverse(raw: Mapping[str, Any]) -> InverseTestV1:
    return InverseTestV1(
        baseline=_required_text(raw, "baseline"),
        counterfactual=_required_text(raw, "counterfactual"),
        inverse_of_inverse=_required_text(raw, "inverse_of_inverse"),
        metric_ref=_optional_text(raw.get("metric_ref")),
        prediction=_optional_text(raw.get("prediction")),
        falsifier=_required_text(raw, "falsifier"),
        horizon=_optional_text(raw.get("horizon")),
        confounders=_strings(raw.get("confounders", ()), "inverse.confounders"),
        stop_rule=_optional_text(raw.get("stop_rule")),
        affected_actors=_strings(raw.get("affected_actors", ()), "inverse.affected_actors"),
        residual_transfer=_strings(raw.get("residual_transfer", ()), "inverse.residual_transfer"),
    )


def _next_gate(raw: Mapping[str, Any]) -> NextGateV1:
    return NextGateV1(
        action=_required_text(raw, "action"),
        reversible=_required_bool(raw, "reversible"),
        stop_rule=_required_text(raw, "stop_rule"),
        deadline=_optional_text(raw.get("deadline")),
        owner=_optional_text(raw.get("owner")),
        verifier=_optional_text(raw.get("verifier")),
        rollback=_optional_text(raw.get("rollback")),
        expected_evidence=_strings(raw.get("expected_evidence", ()), "next_gate.expected_evidence"),
        falsifier=_optional_text(raw.get("falsifier")),
    )


def _replay(raw: Mapping[str, Any]) -> ReplayV1:
    return ReplayV1(
        operator=ReplayOperator(_required_text(raw, "operator")),
        result=EvaluationStatus(_required_text(raw, "result")),
        operator_ref=_optional_text(raw.get("operator_ref")),
        packet_digest=_optional_text(raw.get("packet_digest")),
        packet_version=_optional_text(raw.get("packet_version")),
        blind=_optional_bool(raw.get("blind"), "replay.blind"),
        deltas=_strings(raw.get("deltas", ()), "replay.deltas"),
        unresolved=_strings(raw.get("unresolved", ()), "replay.unresolved"),
    )


def _source(raw: Mapping[str, Any]) -> EvidenceSourceV1:
    return EvidenceSourceV1(
        source_id=_required_text(raw, "source_id"),
        title=_required_text(raw, "title"),
        source_class=SourceClass(_required_text(raw, "source_class")),
        access=SourceAccess(str(raw.get("access", SourceAccess.PUBLIC.value))),
        owner=_optional_text(raw.get("owner")),
        date=_optional_text(raw.get("date")),
        locator=_optional_text(raw.get("locator")),
        limitations=_strings(raw.get("limitations", ()), "source.limitations"),
    )


def _history(raw: Mapping[str, Any]) -> HistoryEntryV1:
    return HistoryEntryV1(
        timestamp=_required_text(raw, "timestamp"),
        field=_required_text(raw, "field"),
        old=str(raw.get("old", "")),
        new=str(raw.get("new", "")),
        reason=_required_text(raw, "reason"),
        actor=_required_text(raw, "actor"),
    )


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CoherenceTransportError(f"{field} must be an object")
    return value


def _mappings(value: Any, field: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CoherenceTransportError(f"{field} must be an array")
    return tuple(_mapping(item, field) for item in value)


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CoherenceTransportError(f"{field} must be an array")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise CoherenceTransportError(f"{field} entries must be non-empty strings")
        result.append(item.strip())
    return tuple(result)


def _required_text(raw: Mapping[str, Any], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CoherenceTransportError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CoherenceTransportError("optional text values must be non-empty strings")
    return value.strip()


def _required_bool(raw: Mapping[str, Any], field: str) -> bool:
    if field not in raw or type(raw[field]) is not bool:
        raise CoherenceTransportError(f"{field} must be boolean")
    return raw[field]


def _bool(raw: Mapping[str, Any], field: str, default: bool) -> bool:
    value = raw.get(field, default)
    if type(value) is not bool:
        raise CoherenceTransportError(f"{field} must be boolean")
    return value


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if type(value) is not bool:
        raise CoherenceTransportError(f"{field} must be boolean")
    return value


def _optional_float(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CoherenceTransportError(f"{field} must be numeric or null")
    return float(value)


def _int(raw: Mapping[str, Any], field: str, default: int) -> int:
    value = raw.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CoherenceTransportError(f"{field} must be an integer")
    return value


__all__ = ["CoherenceTransportError", "evaluate_and_bind", "parse_evaluation_input"]
