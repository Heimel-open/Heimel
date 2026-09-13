"""
P0.5 (full): independent judge panel via injected judge_fn.

Verifies that a judge-requiring instrument (cot_auditor) is:
  - judged by an independent judge_fn when supplied (self_judging=False),
  - falls back to self-judging via generate_fn when no judge is supplied
    (self_judging=True), and
  - fails closed (UNCALIBRATED) when neither judge_fn nor generate_fn is
    available at evaluation time.
"""

import os


from vaig.ensemble import VAIGEnsemble
from vaig.instruments.cot_auditor import SelfAuditCoTAuditor


def _independent_judge(prompt: str) -> str:
    # A SEPARATE model: always returns a fixed, non-self verdict.
    return "CONSISTENT"


def _self_model(prompt: str) -> str:
    # The same model that produced the response (self-judging).
    return "UNSUPPORTED"


def _make_ensemble(tmp_path):
    log_path = os.path.join(str(tmp_path), "vaig_audit.jsonl")
    ensemble = VAIGEnsemble(log_path=log_path)
    # Isolate the single judge-requiring instrument for deterministic tests.
    ensemble.instruments = {"cot_auditor": SelfAuditCoTAuditor()}
    return ensemble


def test_independent_judge_is_used_and_flagged_not_self_judging(tmp_path):
    ensemble = _make_ensemble(tmp_path)
    result = ensemble.evaluate(
        prompt="Why?",
        response="Because.",
        judge_fn=_independent_judge,
        active_slots={"cot_auditor"},
    )
    slot = result.instrument_results["cot_auditor"]
    assert slot.status.value == "MEASURED"
    # Independent judge -> not self-judging.
    assert slot.self_judging is False
    # Independent judge returned CONSISTENT -> 0.0 risk.
    assert result.scores.get("cot_auditor") == 0.0


def test_self_judge_fallback_abstains_without_declared_confidence(tmp_path):
    ensemble = _make_ensemble(tmp_path)
    result = ensemble.evaluate(
        prompt="Why?",
        response="Because.",
        generate_fn=_self_model,
        active_slots={"cot_auditor"},
    )
    slot = result.instrument_results["cot_auditor"]
    # No independent judge supplied -> self-judging, but a self-judged
    # measurement without a declared confidence must not drive the verdict
    # as if it were measured certainty: the BlindspotGuard abstains it.
    assert slot.self_judging is True
    assert slot.status.value == "UNCALIBRATED"
    assert result.guard_report is not None
    assert result.guard_report.abstained_slots.get("cot_auditor") == (
        "self_judged_without_independent_judge"
    )
    # The abstained slot is excluded from the aggregate (fail-closed), while
    # the raw score is still recorded for the audit trail.
    assert result.combined_score == 0.0
    assert result.scores.get("cot_auditor") == 0.7


def test_judge_requiring_instrument_fails_closed_without_any_judge(tmp_path):
    ensemble = _make_ensemble(tmp_path)
    result = ensemble.evaluate(
        prompt="Why?",
        response="Because.",
        active_slots={"cot_auditor"},
    )
    slot = result.instrument_results["cot_auditor"]
    # Neither judge_fn nor generate_fn supplied -> fail closed.
    assert slot.status.value == "UNCALIBRATED"
    assert "judge_fn" in (slot.failure_reason or "")
    assert slot.self_judging is False
    # The slot is uncalibrated; the report layer (P0.6 block) rejects the
    # evaluation. Verified separately in test_evaluation_report.


def test_orchestrator_can_inject_judge_fn():
    from vaig.orchestrator import VAIGOrchestrator

    orch = VAIGOrchestrator(generate_fn=None, judge_fn=_independent_judge)
    result = orch.evaluate("Why?", "Because.")
    # cot_auditor must have been judged independently (not self-judged).
    slot = result.validation.instrument_results.get("cot_auditor")
    assert slot is not None
    assert slot.self_judging is False
