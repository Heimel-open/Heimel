import pytest

from vaig.coherence_service import CoherenceTransportError, parse_evaluation_input


def test_invalid_metric_comparison_is_rejected():
    payload = {
        "boundary": {
            "object_id": "action:1",
            "scope": "metric comparison validation",
            "time_window": "2026-08-24T12:00:00Z/2026-08-24T12:05:00Z",
            "decision_question": "is the metric rule valid?",
        },
        "claims": [{
            "text": "observation exists",
            "grade": "O",
            "source_ref": "source:obs",
            "as_of": "2026-08-24T12:00:00Z",
        }],
        "metrics": [{
            "name": "coverage",
            "unit": "ratio",
            "threshold": 0.9,
            "source_ref": "source:metric",
            "observed_value": 0.95,
            "comparison": "BETTER_THAN",
        }],
        "observers": [{"actor": "operator", "role": "reviewer"}],
        "continuation_dependencies": ["state current"],
        "feedback_loops": [{"sensor": "sensor", "threshold_ref": "source:metric", "action": "re-evaluate"}],
        "residuals": [{"risk": "none", "status": "CLOSED", "owner": "owner"}],
        "falsifier": "state changes",
        "next_gate": {"action": "re-evaluate", "reversible": True, "stop_rule": "stop"},
        "replay": {"operator": "UNKNOWN", "result": "OPEN"},
    }
    with pytest.raises(CoherenceTransportError):
        parse_evaluation_input(payload)
