"""Tests for EvaluationReport (P0.9): signed, replayable VAIG -> REHT handoff.

A missing/failed measurement must never appear as 0.0 risk. The report must be
hash-bound and replayable so REHT can reject stale/mismatched/incomplete output,
and it must never claim execution authority.
"""

from types import SimpleNamespace

from vaig.aggregation import AggregationMode, AggregationResult
from vaig.evidence_intake import EvidenceIntakeAssessment, EvidenceIntakeState
from vaig.ensemble import DistrustLevel, ValidationResult
from vaig.instruments.result import InstrumentResult, InstrumentStatus
from vaig.orchestrator import OrchestratorResult

from vaig.evaluation_report import (
    EvaluationReport,
    ReportDisposition,
    build_evaluation_report,
)


def _validation(
    *,
    level=DistrustLevel.TRUSTED,
    combined_score=0.05,
    instrument_results=None,
    instrument_errors=None,
    required_unmeasured=(),
    aggregation=None,
    veto_reasons=(),
    entry_id="validation-1",
):
    return ValidationResult(
        entry_id=entry_id,
        level=level,
        combined_score=combined_score,
        scores={},
        worm_hash="0" * 64,
        latency_ms=0.1,
        instrument_results=instrument_results or {},
        instrument_errors=instrument_errors or {},
        required_unmeasured=tuple(required_unmeasured),
        aggregation=aggregation,
        veto_reasons=tuple(veto_reasons),
    )


def _result(validation, *, evidence_intake=None, requires_human_review=False):
    return OrchestratorResult(
        validation=validation,
        terrain=SimpleNamespace(),  # type: ignore[arg-type]  # test stub, not read by build_evaluation_report
        activated_internal=[],
        activated_external=[],
        skipped=[],
        context_health=1.0,
        context_warning=None,
        context_warning_detail=None,
        cakm_alert=None,
        evidence_intake=evidence_intake,
        underdetermination=None,
        tradecraft=None,
        _prompt="",
        _response="",
    )


def test_clean_evaluation_is_admissible_and_authority_free():
    vr = _validation()
    report = build_evaluation_report(_result(vr))

    assert report.execution_authority is False
    assert report.requires_reht_clearance is True
    assert report.disposition is ReportDisposition.ADMISSIBLE
    assert report.admissible is True
    assert report.rejection_reasons == ()

    intact, problems = report.verify()
    assert intact is True
    assert problems == []
    assert report.report_digest.startswith("sha256:")


def test_unknown_measurement_is_recorded_as_status_not_zero_risk():
    results = {
        "risk": InstrumentResult(
            slot="risk", status=InstrumentStatus.ERROR, failure_reason="boom"
        ),
        "calm": InstrumentResult(
            slot="calm", status=InstrumentStatus.MEASURED, raw_score=0.1
        ),
    }
    vr = _validation(instrument_results=results)
    report = build_evaluation_report(_result(vr))

    by_slot = {s.slot: s for s in report.slots}
    assert by_slot["risk"].status == "ERROR"
    assert by_slot["risk"].risk is None  # not coerced to 0.0
    assert by_slot["calm"].status == "MEASURED"
    assert by_slot["calm"].risk == 0.1


def test_instrument_error_rejects_report():
    results = {
        "risk": InstrumentResult(
            slot="risk", status=InstrumentStatus.ERROR, failure_reason="boom"
        ),
    }
    vr = _validation(
        instrument_results=results,
        instrument_errors={"risk": "boom"},
    )
    report = build_evaluation_report(_result(vr))

    assert report.disposition is ReportDisposition.REJECTED
    assert any("instrument errors" in r for r in report.rejection_reasons)
    # Internally consistent yet not admissible: verify reports admissible=False
    # via problems, but the report is still tamper-intact (intact is True).
    intact, problems = report.verify()
    assert intact is True
    assert any("not admissible" in p for p in problems)


def test_required_unmeasured_rejects_report():
    vr = _validation(required_unmeasured=("sentiment", "tone"))
    report = build_evaluation_report(_result(vr))

    assert report.disposition is ReportDisposition.REJECTED
    assert any("required slots unmeasured" in r for r in report.rejection_reasons)


def test_evidence_intake_blocked_rejects_report():
    blocked = EvidenceIntakeAssessment(
        state=EvidenceIntakeState.MISMATCHED,
        policy_version="evidence-intake-v1",
        blocking_reasons=("Required EvidencePackage is missing.",),
    )
    vr = _validation()
    report = build_evaluation_report(_result(vr, evidence_intake=blocked))

    assert report.disposition is ReportDisposition.REJECTED
    assert any("evidence intake blocked" in r for r in report.rejection_reasons)
    assert report.evidence_blocked is True


def test_aggregation_abstention_rejects_report():
    agg = AggregationResult(
        mode=AggregationMode.RISK_WEIGHTED_MAX,
        policy_version="risk-weighted-max-v1",
        score=0.0,
        abstained=True,
        abstention_reason="One or more instruments failed.",
        halt_requested=True,
    )
    vr = _validation(aggregation=agg)
    report = build_evaluation_report(_result(vr))

    assert report.disposition is ReportDisposition.REJECTED
    assert any("aggregation abstained" in r for r in report.rejection_reasons)


def test_halt_rejects_report():
    vr = _validation(level=DistrustLevel.HALT, combined_score=0.9)
    report = build_evaluation_report(_result(vr))

    assert report.should_halt is True
    assert report.disposition is ReportDisposition.REJECTED
    assert any(r == "evaluation halted" for r in report.rejection_reasons)


def test_tampered_report_fails_replay_verification():
    vr = _validation()
    report = build_evaluation_report(_result(vr))

    # Simulate a silently altered combined_score after the fact.
    tampered = EvaluationReport(
        **{**report.to_dict(), "combined_score": 0.99}
    )
    intact, problems = tampered.verify()
    assert intact is False
    assert any("report_digest mismatch" in p for p in problems)


def test_report_is_deterministic_for_same_evaluation():
    vr = _validation(combined_score=0.2)
    a = build_evaluation_report(_result(vr))
    b = build_evaluation_report(_result(vr))
    assert a.report_digest == b.report_digest


def test_orchestrator_result_helper_exists():
    vr = _validation()
    helper = getattr(_result(vr), "to_evaluation_report", None)
    assert callable(helper)
    report = helper()
    assert isinstance(report, EvaluationReport)
    assert report.execution_authority is False


def test_underdetermination_and_tradecraft_are_bound_into_report():
    # #141.8: the assessment outputs must be carried into the EvaluationReport.
    from vaig.epistemic_underdetermination import (
        AlternativeHypothesis,
        EpistemicState,
        UnderdeterminationAssessment,
        UnderdeterminationKind,
    )

    underdet = UnderdeterminationAssessment(
        epistemic_state=EpistemicState.DETERMINED,
        kind=UnderdeterminationKind.NONE,
        surviving_alternatives=(),
        shared_evidence_refs=(),
        revision_targets=(),
        discriminating_tests=(),
        unconceived_alternative_risk=False,
        consequence_divergence=False,
        rationale=("Single viable explanation.",),
    )
    # Stub for AnalyticTradecraftAssessment: build_evaluation_report only calls
    # .to_dict(); a real assessment would be produced by AnalyticTradecraftGate.
    # OrchestratorResult also reads .blocks_consequential_action / .requires_human_review.
    tradecraft = SimpleNamespace(
        to_dict=lambda: {
            "state": "CONSTRAINED",
            "least_contradicted_hypotheses": ["h1"],
        },
        blocks_consequential_action=False,
        requires_human_review=False,
    )

    vr = _validation()
    report = build_evaluation_report(
        _result_with_assessments(vr, underdet, tradecraft)
    )

    assert report.underdetermination is not None
    assert report.underdetermination["epistemic_state"] == "DETERMINED"
    assert report.tradecraft is not None
    assert report.tradecraft["state"] == "CONSTRAINED"
    # Both are part of the canonical payload, so they affect the digest.
    intact, _ = report.verify()
    assert intact is True


def test_tampered_tradecraft_fails_replay_verification():
    from vaig.epistemic_underdetermination import (
        AlternativeHypothesis,
        EpistemicState,
        UnderdeterminationAssessment,
        UnderdeterminationKind,
    )

    underdet = UnderdeterminationAssessment(
        epistemic_state=EpistemicState.DETERMINED,
        kind=UnderdeterminationKind.NONE,
        surviving_alternatives=(),
        shared_evidence_refs=(),
        revision_targets=(),
        discriminating_tests=(),
        unconceived_alternative_risk=False,
        consequence_divergence=False,
        rationale=(),
    )
    tradecraft = SimpleNamespace(
        to_dict=lambda: {"state": "SUFFICIENT", "disposition": "ok"},
        blocks_consequential_action=False,
        requires_human_review=False,
    )
    vr = _validation()
    report = build_evaluation_report(
        _result_with_assessments(vr, underdet, tradecraft)
    )

    # Silently alter the tradecraft assessment after the fact.
    tc = report.tradecraft
    assert tc is not None
    tampered_tradecraft = dict(tc)
    tampered_tradecraft["state"] = "INSUFFICIENT"
    tampered = EvaluationReport(
        **{
            **report.to_dict(),
            "tradecraft": tampered_tradecraft,
        }
    )
    intact, problems = tampered.verify()
    assert intact is False
    assert any("report_digest mismatch" in p for p in problems)


def test_self_judging_instrument_is_flagged_in_report_and_tamper_detected():
    # P0.5: a self-judging slot (e.g. CoT self-audit reusing the same model)
    # must be recorded as self_judging in the report so REHT can see the
    # limited independence. Tampering the flag must break replay verification.
    sj = InstrumentResult(
        slot="cot_auditor",
        status=InstrumentStatus.MEASURED,
        raw_score=0.2,
        implementation="SelfAuditCoTAuditor",
        self_judging=True,
    )
    vr = _validation(instrument_results={"cot_auditor": sj})
    report = build_evaluation_report(_result_with_assessments(vr, None, None))
    slot = next(s for s in report.slots if s.slot == "cot_auditor")
    assert slot.self_judging is True
    assert slot.to_dict()["self_judging"] is True

    tampered = EvaluationReport(**{**report.to_dict(), "slots": tuple(
        dict(s.to_dict()) | {"self_judging": False} if s.slot == "cot_auditor" else s.to_dict()
        for s in report.slots
    )})
    intact, problems = tampered.verify()
    assert intact is False
    assert any("report_digest mismatch" in p for p in problems)


def test_uncalibrated_instrument_blocks_handoff_p0_6():
    # P0.6: a required instrument without a bound calibration profile must not
    # pass clearance silently. The report must be rejected so REHT refuses.
    unc = InstrumentResult(
        slot="activation_probe",
        status=InstrumentStatus.UNCALIBRATED,
        implementation="ActivationProbe",
        failure_reason="Versioned calibration artifact is not bound.",
    )
    vr = _validation(instrument_results={"activation_probe": unc})
    report = build_evaluation_report(_result_with_assessments(vr, None, None))
    assert any("uncalibrated" in r for r in report.rejection_reasons)
    assert report.admissible is False
    assert report.disposition is ReportDisposition.REJECTED


def test_calibrated_instrument_does_not_block_handoff():
    cal = InstrumentResult(
        slot="activation_probe",
        status=InstrumentStatus.MEASURED,
        raw_score=0.1,
        implementation="ActivationProbe",
        calibration_profile="sage-v1@2026-08-01",
    )
    vr = _validation(instrument_results={"activation_probe": cal})
    report = build_evaluation_report(_result_with_assessments(vr, None, None))
    assert not any("uncalibrated" in r for r in report.rejection_reasons)


def test_verify_intact_means_tamper_integrity_not_admissibility():
    # `intact` from verify() reflects tamper-integrity (digest + authority
    # fields), NOT admissibility. An honestly-rejected report (e.g. uncalibrated
    # instrument) is intact=True but admissible=False; a tampered report is
    # intact=False regardless of admissibility.
    unc = InstrumentResult(
        slot="activation_probe",
        status=InstrumentStatus.UNCALIBRATED,
        implementation="ActivationProbe",
        failure_reason="Versioned calibration artifact is not bound.",
    )
    vr = _validation(instrument_results={"activation_probe": unc})
    report = build_evaluation_report(_result_with_assessments(vr, None, None))
    intact, problems = report.verify()
    assert intact is True  # not tampered
    assert report.admissible is False  # but not admissible
    assert any("not admissible" in p for p in problems)

    tampered = EvaluationReport(**{**report.to_dict(), "rejection_reasons": ()})
    t_intact, _ = tampered.verify()
    assert t_intact is False  # digest mismatch from dropping rejection_reasons


def test_calibration_metrics_propagate_through_handoff_p0_6():
    # P0.6 (full): a calibrated instrument should surface its SAGE metrics in
    # the handoff so REHT can judge calibration quality, not just presence.
    from vaig.calibration import CalibrationProfile

    metrics = CalibrationProfile(
        profile_id="sage-v1@2026-08-01",
        brier=0.12,
        ece=0.05,
        auroc=0.93,
        n_samples=548,
        benchmark_id="vaig-bench-48x500",
    )
    cal = InstrumentResult(
        slot="activation_probe",
        status=InstrumentStatus.MEASURED,
        raw_score=0.1,
        implementation="ActivationProbe",
        calibration_profile="sage-v1@2026-08-01",
        calibration_metrics=metrics,
    )
    vr = _validation(instrument_results={"activation_probe": cal})
    report = build_evaluation_report(_result_with_assessments(vr, None, None))
    slot = next(s for s in report.slots if s.slot == "activation_probe")
    assert slot.calibration_metrics is not None
    assert slot.calibration_metrics.auroc == 0.93
    d = slot.to_dict()
    assert d["calibration_metrics"]["auroc"] == 0.93

    # tampering the metrics must break replay verification
    from dataclasses import asdict as _asdict

    probe = next(s for s in report.slots if s.slot == "activation_probe")
    assert probe.calibration_metrics is not None
    metrics_dict = _asdict(probe.calibration_metrics)
    tampered = EvaluationReport(**{**report.to_dict(), "slots": tuple(
        {**s.to_dict(), "calibration_metrics": {**metrics_dict, "auroc": 0.5}}
        if s.slot == "activation_probe" else s.to_dict()
        for s in report.slots
    )})
    intact, problems = tampered.verify()
    assert intact is False
    assert any("report_digest mismatch" in p for p in problems)


def _result_with_assessments(validation, underdetermination, tradecraft):
    return OrchestratorResult(
        validation=validation,
        terrain=SimpleNamespace(),  # type: ignore[arg-type]
        activated_internal=[],
        activated_external=[],
        skipped=[],
        context_health=1.0,
        context_warning=None,
        context_warning_detail=None,
        cakm_alert=None,
        evidence_intake=None,
        underdetermination=underdetermination,
        tradecraft=tradecraft,
        _prompt="",
        _response="",
    )
