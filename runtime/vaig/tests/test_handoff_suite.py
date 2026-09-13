"""P0.8: CI-gated VAIG -> REHT handoff benchmark suite (#133 / #141, #169).

Runs the full handoff via ``benchmarks/handoff_suite.run_handoff_suite`` and
asserts the REHT contract end to end.
"""

from benchmarks.handoff_suite import run_handoff_suite
from vaig.orchestrator import VAIGOrchestrator


def test_handoff_suite_passes():
    result = run_handoff_suite()
    assert result["passed"], result["problems"]

    # Every case asserted handoff_admissible/rejected as designed
    for rec in result["cases"]:
        assert rec["handoff_admissible"] == rec["expected_handoff_admissible"], rec
        assert rec["execution_authority"] is False, rec
        assert rec["requires_reht_clearance"] is True, rec
        assert rec["intact_replay"] is True, rec["id"]
        assert rec["tampered_detected"] is True, rec["id"]

    # SAGE calibration metrics attached and validated
    sage = result["sage"]
    assert sage, "sage record missing"
    assert sage["n_samples"] == 6
    assert sage["distinct_scores_count"] >= 2
    assert sage["brier_finite"]
    assert sage["ece_finite"]
    assert sage["auroc_finite"]
    assert sage["auroc"] > 0.5


def _judge(text: str) -> str:
    return "benign: no attack detected"


def test_authority_boundary_invariants():
    """A handoff-admissible report MUST NOT grant execution authority."""
    orch = VAIGOrchestrator(log_path=":memory:")
    active = {"length_anomaly", "format_check", "cot_auditor"}
    orch.ensemble.instruments = {
        k: v for k, v in orch.ensemble.instruments.items() if k in active
    }
    res = orch.evaluate(
        "What is the capital of Norway?",
        "The capital of Norway is Oslo.",
        judge_fn=_judge,
    )
    report = res.to_evaluation_report()

    assert report.admissible is True
    assert report.execution_authority is False
    assert report.requires_reht_clearance is True
