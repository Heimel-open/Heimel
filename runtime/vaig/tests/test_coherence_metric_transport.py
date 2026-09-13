from vaig.coherence_evaluation import EvaluationStatus
from vaig.coherence_service import evaluate_and_bind


def _payload(*, comparison="GTE", observed=0.95, threshold=0.9):
    return {
        "boundary": {
            "object_id": "action:metric-transport",
            "scope": "metric transport",
            "time_window": "2026-08-24T12:00:00Z/2026-08-24T12:10:00Z",
            "decision_question": "does the metric satisfy its preregistered bound?",
        },
        "claims": [{
            "text": "metric observation captured",
            "grade": "O",
            "source_ref": "source:observation",
            "as_of": "2026-08-24T12:01:00Z",
        }],
        "metrics": [{
            "name": "coverage",
            "unit": "ratio",
            "threshold": threshold,
            "source_ref": "source:metric-contract",
            "observed_value": observed,
            "comparison": comparison,
            "locked_before_outcome": True,
        }],
        "observers": [{"actor": "operator:test", "role": "metric verifier"}],
        "continuation_dependencies": ["metric evidence remains current"],
        "feedback_loops": [{
            "sensor": "metric sensor",
            "threshold_ref": "source:metric-contract",
            "action": "re-evaluate",
        }],
        "residuals": [{"risk": "no remaining metric residual", "status": "CLOSED", "owner": "owner:test"}],
        "falsifier": "metric evidence changes",
        "next_gate": {
            "action": "submit exact packet downstream",
            "reversible": True,
            "stop_rule": "stop on bound-state change",
        },
        "replay": {
            "operator": "INDEPENDENT",
            "result": "PASS",
            "operator_ref": "operator:replay",
        },
    }


def test_gte_comparison_survives_transport_and_passes():
    binding = evaluate_and_bind(_payload())
    assert binding["result"]["status"] == EvaluationStatus.PASS.value


def test_threshold_breach_survives_transport_and_fails():
    binding = evaluate_and_bind(_payload(observed=0.5))
    assert binding["result"]["status"] == EvaluationStatus.FAIL.value
    assert "METRIC_THRESHOLD_BREACH" in binding["result"]["reason_codes"]


def test_missing_comparison_is_open_not_inferred():
    payload = _payload()
    payload["metrics"][0].pop("comparison")
    binding = evaluate_and_bind(payload)
    assert binding["result"]["status"] == EvaluationStatus.OPEN.value
    assert "METRIC_COMPARISON_UNKNOWN" in binding["result"]["reason_codes"]
