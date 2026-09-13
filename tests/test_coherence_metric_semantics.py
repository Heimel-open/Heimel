from dataclasses import replace

import pytest

from vaig.coherence_evaluation import (
    CoherenceEvaluationGateV1,
    CoherenceEvaluationInputV1,
    EvaluationBoundaryV1,
    EvaluationStatus,
    EvidenceClaimV1,
    EvidenceGrade,
    EvidenceSourceV1,
    FeedbackLoopV1,
    InverseTestV1,
    MetricComparison,
    MetricV1,
    NextGateV1,
    ObserverV1,
    ReplayOperator,
    ReplayV1,
    ResidualV1,
    SourceClass,
    replay_packet_digest,
)


def _evaluation(metric: MetricV1, *, high_stakes: bool = False, metric_source: str = "source:metric"):
    boundary = EvaluationBoundaryV1(
        object_id="action:metric-test",
        scope="metric semantics",
        time_window="2026-08-24T12:00:00Z/2026-08-24T12:10:00Z",
        decision_question="does the preregistered metric satisfy its declared bound?",
        authority_refs=(("authority:test",) if high_stakes else ()),
        native_standard_refs=(("standard:test",) if high_stakes else ()),
    )
    claim = EvidenceClaimV1(
        text="the metric observation was captured",
        grade=EvidenceGrade.OBSERVATION,
        source_ref="source:observation",
        as_of="2026-08-24T12:01:00Z",
        counter_source_search_performed=high_stakes,
        material=True,
    )
    sources = (
        EvidenceSourceV1("source:observation", "Observation", SourceClass.PRIMARY),
        EvidenceSourceV1("source:metric", "Metric contract", SourceClass.PRIMARY),
        EvidenceSourceV1("source:counter", "Counter source", SourceClass.INDEPENDENT_AUDIT),
    ) if high_stakes else ()
    inverse = (
        InverseTestV1(
            baseline="keep baseline",
            counterfactual="change candidate",
            inverse_of_inverse="restraint can create opposite harm",
            metric_ref=metric.metric_id or metric.name,
            prediction="metric changes in declared direction",
            falsifier="metric does not change",
        )
        if high_stakes
        else None
    )
    next_gate = NextGateV1(
        action="submit exact packet to downstream authorization",
        reversible=True,
        stop_rule="stop on any bound-state change",
        owner=("owner:test" if high_stakes else None),
        verifier=("verifier:test" if high_stakes else None),
        rollback=("discard packet" if high_stakes else None),
        expected_evidence=(("source:observation",) if high_stakes else ()),
        falsifier=("metric binding changes" if high_stakes else None),
    )
    evaluation = CoherenceEvaluationInputV1(
        boundary=boundary,
        claims=(claim,),
        metrics=(metric,),
        observers=(ObserverV1("operator:test", "metric verifier"),),
        continuation_dependencies=("bound metric state remains current",),
        feedback_loops=(FeedbackLoopV1("metric sensor", metric_source, "re-evaluate"),),
        residuals=(ResidualV1("no remaining metric residual", "CLOSED", owner="owner:test"),),
        falsifier="metric observation or contract changes",
        next_gate=next_gate,
        replay=ReplayV1(
            ReplayOperator.INDEPENDENT,
            EvaluationStatus.PASS,
            operator_ref="replay:test",
            packet_version=("run-packet-v1" if high_stakes else None),
        ),
        high_stakes=high_stakes,
        counter_source_refs=(("source:counter",) if high_stakes else ()),
        sources=sources,
        inverse=inverse,
    )
    return replace(
        evaluation,
        replay=replace(evaluation.replay, packet_digest=replay_packet_digest(evaluation)),
    )


def _metric(**overrides):
    values = dict(
        name="coverage",
        unit="ratio",
        threshold=0.9,
        source_ref="source:metric",
        observed_value=0.95,
        comparison=MetricComparison.GTE,
        metric_id="metric:coverage",
    )
    values.update(overrides)
    return MetricV1(**values)


def test_missing_observation_stays_open():
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(_metric(observed_value=None)))
    assert result.status is EvaluationStatus.OPEN
    assert "METRIC_OBSERVATION_MISSING" in result.reason_codes


def test_missing_comparison_stays_open():
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(_metric(comparison=None)))
    assert result.status is EvaluationStatus.OPEN
    assert "METRIC_COMPARISON_UNKNOWN" in result.reason_codes


def test_gte_threshold_breach_fails():
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(_metric(observed_value=0.5)))
    assert result.status is EvaluationStatus.FAIL
    assert "METRIC_THRESHOLD_BREACH" in result.reason_codes


def test_lte_threshold_breach_fails():
    result = CoherenceEvaluationGateV1().evaluate(
        _evaluation(_metric(threshold=200.0, observed_value=250.0, comparison=MetricComparison.LTE))
    )
    assert result.status is EvaluationStatus.FAIL
    assert "METRIC_THRESHOLD_BREACH" in result.reason_codes


def test_nonfinite_metric_value_is_rejected():
    with pytest.raises(ValueError, match="finite number"):
        _metric(threshold=float("nan"))


def test_high_stakes_metric_source_lineage_is_required():
    metric = _metric(source_ref="source:missing")
    result = CoherenceEvaluationGateV1().evaluate(
        _evaluation(metric, high_stakes=True, metric_source="source:missing")
    )
    assert result.status is EvaluationStatus.OPEN
    assert "METRIC_SOURCE_LINEAGE_MISSING" in result.reason_codes
