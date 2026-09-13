import copy

from fastapi.testclient import TestClient

from vaig.coherence_api import app
from vaig.coherence_service import evaluate_and_bind
from vaig.reht_handoff import CoherenceHandoffBindingV1


def _payload():
    return {
        "boundary": {
            "object_id": "action:1",
            "scope": "single governed effect",
            "time_window": "2026-08-24T10:00:00Z/2026-08-24T10:05:00Z",
            "decision_question": "is the evidence packet coherent enough to proceed to REHT?",
        },
        "claims": [
            {
                "text": "the proposed action matches the observed runtime packet",
                "grade": "O",
                "source_ref": "source:runtime",
                "as_of": "2026-08-24T10:00:00Z",
            }
        ],
        "metrics": [
            {
                "name": "packet completeness",
                "unit": "ratio",
                "threshold": 1.0,
                "source_ref": "metric-contract:v1",
                "observed_value": 1.0,
                "comparison": "GTE",
                "locked_before_outcome": True,
            }
        ],
        "observers": [
            {
                "actor": "vaig-runtime",
                "role": "independent evaluator",
                "incentives": ["fail closed"],
                "conflicts": [],
            }
        ],
        "continuation_dependencies": ["runtime evidence remains current"],
        "feedback_loops": [
            {
                "sensor": "runtime-state-monitor",
                "threshold_ref": "metric-contract:v1",
                "action": "force fresh evaluation on material change",
            }
        ],
        "residuals": [
            {
                "risk": "execution authority still unresolved",
                "status": "CLOSED",
                "owner": "reht",
            }
        ],
        "falsifier": "material evidence changes before clearance",
        "next_gate": {
            "action": "submit exact action to REHT",
            "reversible": True,
            "stop_rule": "stop if any bound digest changes",
        },
        "replay": {
            "operator": "INDEPENDENT",
            "result": "PASS",
            "operator_ref": "replay:operator:2",
        },
    }


def test_service_returns_exact_digest_bound_handoff_contract():
    binding = evaluate_and_bind(_payload())
    parsed = CoherenceHandoffBindingV1(
        result=binding["result"],
        result_digest=binding["result_digest"],
        schema_version=binding["schema_version"],
        execution_authority=binding["execution_authority"],
        requires_reht_clearance=binding["requires_reht_clearance"],
        can_execute=binding["can_execute"],
    )
    assert parsed.status.value == "PASS"
    assert parsed.execution_authority is False
    assert parsed.requires_reht_clearance is True
    assert parsed.can_execute is False


def test_unknown_threshold_remains_open_over_http():
    payload = _payload()
    payload["metrics"][0]["threshold"] = None
    response = TestClient(app).post("/api/v1/coherence/evaluate", json=payload)
    assert response.status_code == 200
    binding = response.json()
    assert binding["result"]["status"] == "OPEN"
    assert "METRIC_THRESHOLD_UNKNOWN" in binding["result"]["reason_codes"]
    assert binding["execution_authority"] is False


def test_transport_rejects_malformed_boolean_instead_of_coercing():
    payload = _payload()
    payload["next_gate"]["reversible"] = "true"
    response = TestClient(app).post("/api/v1/coherence/evaluate", json=payload)
    assert response.status_code == 422
    assert "reversible must be boolean" in response.json()["detail"]


def test_transport_rejects_invalid_observation_without_source():
    payload = copy.deepcopy(_payload())
    payload["claims"][0]["source_ref"] = None
    response = TestClient(app).post("/api/v1/coherence/evaluate", json=payload)
    assert response.status_code == 422
    assert "observations require source_ref" in response.json()["detail"]


def test_configured_service_token_is_required(monkeypatch):
    monkeypatch.setenv("VAIG_COHERENCE_TOKEN", "secret-token")
    client = TestClient(app)
    unauthorized = client.post("/api/v1/coherence/evaluate", json=_payload())
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/api/v1/coherence/evaluate",
        json=_payload(),
        headers={"Authorization": "Bearer secret-token"},
    )
    assert authorized.status_code == 200
    assert authorized.json()["result"]["status"] == "PASS"


def test_health_states_no_execution_authority():
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "vaig-coherence-evaluation",
        "execution_authority": False,
        "requires_reht_clearance": True,
    }
