"""Regression dataset/suite + orchestrator judge provenance (learning loop)."""


from vaig.aarm import AARMVerdict
from vaig.judge import JudgeSpec
from vaig.orchestrator import VAIGOrchestrator
from vaig.regression import RegressionDataset, RegressionSuite

EVIDENCE_HIGH = {
    "risk_class": "critical",
    "uncertainty": 0.9,
    "reversibility": "irreversible",
    "tool_authority": "delete",
    "task_authority": "read",
    "drift_score": 0.9,
    "observation_trust": 0.2,
    "claims_substantiated": False,
    "evidence_valid": False,
}

EVIDENCE_LOW = {
    "risk_class": "low",
    "uncertainty": 0.1,
    "reversibility": "reversible",
    "tool_authority": "read",
    "task_authority": "read",
    "drift_score": 0.0,
    "observation_trust": 0.9,
    "claims_substantiated": True,
    "evidence_valid": True,
}


def test_dataset_records_with_judge_provenance(tmp_path):
    spec = JudgeSpec(provider="ollama", model_id="judge-7b", model_version="v1")
    ds = RegressionDataset(tmp_path / "reg.jsonl")
    ds.record(
        case_id="c1",
        evidence=dict(EVIDENCE_HIGH),
        predicted_verdict="ALLOW",
        judge_spec=spec.to_audit_dict(),
    )
    loaded = RegressionDataset(tmp_path / "reg.jsonl")
    assert len(loaded) == 1
    case = loaded.find("c1")
    assert case.judge_spec["model_id"] == "judge-7b"
    assert case.corrected_verdict is None


def test_suite_detects_regression_on_known_failure(tmp_path):
    ds = RegressionDataset(tmp_path / "reg.jsonl")
    ds.record(
        case_id="f1",
        evidence=dict(EVIDENCE_HIGH),
        predicted_verdict="ALLOW",
        corrected_verdict="HALT",
    )
    suite = RegressionSuite(ds)

    def good(evidence):
        return "HALT"

    report = suite.evaluate(good)
    assert report.passed is True
    assert report.regression_rate == 0.0

    def regressed(evidence):
        return "ALLOW"

    bad = suite.evaluate(regressed)
    assert bad.passed is False
    assert bad.regression_rate == 1.0
    assert "f1" in bad.regressions[0]


def test_orchestrator_records_decision_with_judge_spec(tmp_path):
    spec = JudgeSpec(provider="ollama", model_id="judge-7b", model_version="v1")
    orch = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        regression_path=str(tmp_path / "reg.jsonl"),
        with_cakm=False,
        judge_spec=spec,
    )
    orch.ensemble.instruments = {}
    orch.dirigent.conduct = lambda terrain: _empty_plan()
    orch.evaluate(prompt="p", response="r")
    assert len(orch.regression) == 1
    case = orch.regression.cases()[0]
    assert case.judge_spec["model_id"] == "judge-7b"
    assert case.predicted_verdict in {v.value for v in AARMVerdict}


def _empty_plan():
    from types import SimpleNamespace

    return SimpleNamespace(
        internal=[],
        external=[],
        bench=[],
        thresholds={},
        context_health=1.0,
        context_warning=None,
        context_warning_detail=None,
    )
