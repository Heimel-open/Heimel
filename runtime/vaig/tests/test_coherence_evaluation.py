from dataclasses import replace

import pytest

from vaig.coherence_evaluation import (
    CoherenceEvaluationGateV1,
    CoherenceEvaluationInputV1,
    CoherenceEvaluationResultV1,
    DutyV1,
    EvaluationBoundaryV1,
    EvaluationStatus,
    EvidenceClaimV1,
    EvidenceGrade,
    EvidenceSourceV1,
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
    replay_packet_digest,
)


def _sources():
    return (
        EvidenceSourceV1("telemetry://latency", "Latency telemetry", SourceClass.PRIMARY, date="2026-08-24"),
        EvidenceSourceV1("slo://latency", "Latency SLO", SourceClass.PRIMARY, date="2026-08-24"),
        EvidenceSourceV1("incident://prior-failure", "Prior latency incident", SourceClass.INDEPENDENT_AUDIT, date="2026-08-20"),
    )


def _evaluation(bind_replay=True, **overrides):
    payload = dict(
        boundary=EvaluationBoundaryV1(
            object_id="svc-1",
            scope="production service",
            time_window="2026-08-24",
            decision_question="is the evaluation sufficiently supported?",
            authority_refs=("authority://service-owner",),
            native_standard_refs=("slo://latency",),
            interfaces=("service->database",),
        ),
        claims=(
            EvidenceClaimV1(
                text="latency is inside the declared bound",
                grade=EvidenceGrade.OBSERVATION,
                source_ref="telemetry://latency",
                as_of="2026-08-24T05:00:00Z",
                claim_id="claim-1",
                confidence=0.97,
                contradiction_refs=("incident://prior-failure",),
                counter_source_search_performed=True,
            ),
        ),
        metrics=(
            MetricV1(
                name="p95_latency",
                unit="ms",
                threshold=200.0,
                source_ref="slo://latency",
                observed_value=120.0,
                comparison=MetricComparison.LTE,
                locked_before_outcome=True,
                metric_id="metric-p95",
            ),
        ),
        observers=(ObserverV1(actor="sre", role="operator", incentives=("availability",), conflicts=("service-owner",)),),
        continuation_dependencies=("network", "database"),
        feedback_loops=(FeedbackLoopV1(sensor="latency telemetry", threshold_ref="slo://latency", action="rollback", observed_effect="p95 returned below 200 ms", verifier="reviewer-2"),),
        residuals=(ResidualV1(risk="regional outage", status="OPEN", owner="sre-oncall", bearer="customers", uncertainty="tail unknown", evidence_refs=("incident://prior-failure",), escalation_path="incident commander"),),
        duties=(DutyV1(residual_risk="regional outage", accountable_role="sre-oncall", cadence="per canary", escalation_path="incident commander"),),
        falsifier="p95 >= 200 ms for two consecutive windows",
        inverse=InverseTestV1(
            baseline="run current configuration",
            counterfactual="reduce rollout concurrency",
            inverse_of_inverse="reduced concurrency increases queue saturation",
            metric_ref="metric-p95",
            prediction="p95 decreases under reduced concurrency",
            falsifier="p95 does not decrease",
            stop_rule="stop if queue depth doubles",
        ),
        next_gate=NextGateV1(action="run one bounded canary", reversible=True, stop_rule="rollback if p95 >= 200 ms", owner="sre-oncall", verifier="reviewer-2", rollback="restore previous deployment", expected_evidence=("telemetry://latency",), falsifier="p95 >= 200 ms"),
        replay=ReplayV1(operator=ReplayOperator.ADVERSARIAL, result=EvaluationStatus.PASS, operator_ref="reviewer-2", packet_version="run-packet-v1", blind=True),
        claims_correction=True,
        high_stakes=True,
        counter_source_refs=("incident://prior-failure",),
        sources=_sources(),
    )
    payload.update(overrides)
    evaluation = CoherenceEvaluationInputV1(**payload)
    if bind_replay and evaluation.replay.result is EvaluationStatus.PASS:
        evaluation = replace(evaluation, replay=replace(evaluation.replay, packet_digest=replay_packet_digest(evaluation)))
    return evaluation


def test_complete_hostile_evaluation_passes_but_cannot_execute():
    result = CoherenceEvaluationGateV1().evaluate(_evaluation())
    assert result.status is EvaluationStatus.PASS
    assert result.reason_codes == ()
    assert result.execution_authority is False
    assert result.requires_reht_clearance is True
    assert result.can_execute is False


def test_digest_is_deterministic():
    gate = CoherenceEvaluationGateV1()
    assert gate.evaluate(_evaluation()).input_digest == gate.evaluate(_evaluation()).input_digest


def test_unknown_threshold_keeps_run_open():
    metric = MetricV1("p95_latency", "ms", None, "slo://latency")
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(metrics=(metric,)))
    assert result.status is EvaluationStatus.OPEN
    assert "METRIC_THRESHOLD_UNKNOWN" in result.reason_codes


def test_metric_must_be_locked_before_outcome():
    metric = MetricV1("p95_latency", "ms", 200.0, "slo://latency", locked_before_outcome=False)
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(metrics=(metric,)))
    assert "METRIC_NOT_PREREGISTERED" in result.reason_codes


def test_correction_claim_without_observed_effect_stays_open():
    loop = FeedbackLoopV1("latency", "slo://latency", "rollback")
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(feedback_loops=(loop,)))
    assert result.status is EvaluationStatus.OPEN
    assert "CORRECTION_EFFECT_UNVERIFIED" in result.reason_codes


def test_open_residual_requires_owner():
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(residuals=(ResidualV1("regional outage", "OPEN", bearer="customers", evidence_refs=("incident://prior-failure",)),)))
    assert "OPEN_RESIDUAL_OWNER_UNKNOWN" in result.reason_codes


def test_high_stakes_run_requires_counter_source():
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(counter_source_refs=()))
    assert "COUNTER_SOURCE_MISSING" in result.reason_codes


def test_failed_adversarial_replay_fails_run():
    replay = ReplayV1(ReplayOperator.ADVERSARIAL, EvaluationStatus.FAIL, "red-team")
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(replay=replay))
    assert result.status is EvaluationStatus.FAIL
    assert "ADVERSARIAL_REPLAY_FAILED" in result.reason_codes


def test_unknown_replay_operator_stays_open():
    replay = ReplayV1(ReplayOperator.UNKNOWN, EvaluationStatus.OPEN)
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(replay=replay))
    assert result.status is EvaluationStatus.OPEN
    assert "INDEPENDENT_REPLAY_OPERATOR_UNKNOWN" in result.reason_codes


def test_observation_requires_source_and_date():
    with pytest.raises(ValueError, match="source_ref"):
        EvidenceClaimV1("claim", EvidenceGrade.OBSERVATION)


def test_next_gate_must_be_reversible():
    with pytest.raises(ValueError, match="reversible"):
        NextGateV1("deploy globally", False, "stop")


def test_result_cannot_create_execution_authority():
    with pytest.raises(ValueError, match="cannot grant execution authority"):
        CoherenceEvaluationResultV1(status=EvaluationStatus.PASS, reason_codes=(), input_digest="sha256:" + "a" * 64, execution_authority=True)


def test_high_confidence_unknown_is_still_unknown():
    claim = EvidenceClaimV1("cause is unknown", EvidenceGrade.UNKNOWN, confidence=0.999, counter_source_search_performed=True)
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(claims=(claim,)))
    assert result.status is EvaluationStatus.OPEN
    assert "MATERIAL_EVIDENCE_UNKNOWN" in result.reason_codes


def test_high_stakes_requires_source_lineage_and_counter_search():
    claim = replace(_evaluation().claims[0], counter_source_search_performed=False)
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(claims=(claim,), sources=()))
    assert "SOURCE_REGISTER_MISSING" in result.reason_codes
    assert "COUNTER_SOURCE_SEARCH_MISSING" in result.reason_codes


def test_unavailable_source_keeps_run_open_but_protected_source_does_not():
    unavailable = replace(_sources()[0], access=SourceAccess.UNAVAILABLE)
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(sources=(unavailable,) + _sources()[1:]))
    assert "SOURCE_UNAVAILABLE" in result.reason_codes
    protected = replace(_sources()[0], source_class=SourceClass.PROTECTED, access=SourceAccess.PROTECTED)
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(sources=(protected,) + _sources()[1:]))
    assert "SOURCE_UNAVAILABLE" not in result.reason_codes


def test_high_stakes_requires_authority_and_native_standard_crosswalk():
    boundary = replace(_evaluation().boundary, authority_refs=(), native_standard_refs=())
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(boundary=boundary))
    assert "AUTHORITY_SOURCE_MISSING" in result.reason_codes
    assert "NATIVE_STANDARD_CROSSWALK_MISSING" in result.reason_codes


def test_high_stakes_residual_requires_bearer_evidence_and_duty():
    residual = ResidualV1("regional outage", "OPEN", owner="sre-oncall")
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(residuals=(residual,), duties=()))
    assert "OPEN_RESIDUAL_BEARER_UNKNOWN" in result.reason_codes
    assert "OPEN_RESIDUAL_EVIDENCE_MISSING" in result.reason_codes
    assert "RESIDUAL_DUTY_MISSING" in result.reason_codes


def test_high_stakes_next_gate_requires_owner_verifier_rollback_evidence_and_falsifier():
    gate = NextGateV1("run canary", True, "stop")
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(next_gate=gate))
    assert "NEXT_GATE_OWNER_MISSING" in result.reason_codes
    assert "NEXT_GATE_VERIFIER_MISSING" in result.reason_codes
    assert "NEXT_GATE_ROLLBACK_MISSING" in result.reason_codes
    assert "NEXT_GATE_EXPECTED_EVIDENCE_MISSING" in result.reason_codes
    assert "NEXT_GATE_FALSIFIER_MISSING" in result.reason_codes


def test_high_stakes_inverse_must_change_measurable_prediction():
    inverse = InverseTestV1("baseline", "counterfactual", "inverse of inverse", None, None, "falsifier")
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(inverse=inverse))
    assert "INVERSE_METRIC_MISSING" in result.reason_codes
    assert "INVERSE_PREDICTION_MISSING" in result.reason_codes


def test_replay_packet_must_match_frozen_pre_replay_packet():
    replay = replace(_evaluation().replay, packet_digest="sha256:" + "0" * 64)
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(bind_replay=False, replay=replay))
    assert result.status is EvaluationStatus.FAIL
    assert "REPLAY_PACKET_BINDING_MISMATCH" in result.reason_codes


def test_high_stakes_replay_requires_packet_binding_and_version():
    replay = ReplayV1(ReplayOperator.ADVERSARIAL, EvaluationStatus.PASS, "reviewer-2")
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(bind_replay=False, replay=replay))
    assert result.status is EvaluationStatus.OPEN
    assert "REPLAY_PACKET_BINDING_MISSING" in result.reason_codes
    assert "REPLAY_PACKET_VERSION_MISSING" in result.reason_codes


def test_revised_run_requires_history():
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(run_version=2, history=()))
    assert "REVISION_HISTORY_MISSING" in result.reason_codes
    history = (HistoryEntryV1("2026-08-24T06:00:00Z", "metric.threshold", "250", "200", "new SLO", "sre-owner"),)
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(run_version=2, history=history))
    assert "REVISION_HISTORY_MISSING" not in result.reason_codes


def test_unresolved_replay_cannot_silently_pass():
    replay = replace(_evaluation().replay, unresolved=("threshold dispute",))
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(bind_replay=False, replay=replay))
    assert result.status is EvaluationStatus.OPEN
    assert "REPLAY_UNRESOLVED" in result.reason_codes


def test_contradiction_refs_preserve_source_lineage():
    claim = replace(_evaluation().claims[0], contradiction_refs=("missing://counter",))
    result = CoherenceEvaluationGateV1().evaluate(_evaluation(claims=(claim,)))
    assert "CONTRADICTION_SOURCE_LINEAGE_MISSING" in result.reason_codes
