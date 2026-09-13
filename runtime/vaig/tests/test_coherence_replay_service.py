import hashlib

import rfc8785
from fastapi.testclient import TestClient
import pytest

from vaig.coherence_evaluation import replay_packet_digest
from vaig.coherence_replay import CoherenceReplayError, replay_frozen_packet
from vaig.coherence_replay_api import app
from vaig.coherence_service import parse_evaluation_input

OPERATOR = "operator:replay-2"
PRODUCER = "domain-evidence:producer-1"
PACKET_VERSION = "coherence-evaluation-input-v1"
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64


def _frozen_packet(threshold=1.0, observed=1.0):
    return {
        "boundary": {
            "object_id": "action:1",
            "scope": "single governed effect",
            "time_window": "2026-08-24T11:40:00Z/2026-08-24T12:00:00Z",
            "decision_question": "is the packet coherent enough to proceed to REHT?",
        },
        "claims": [
            {
                "text": "the proposed action matches the observed runtime packet",
                "grade": "O",
                "source_ref": "runtime:packet",
                "as_of": "2026-08-24T11:40:00Z",
                "material": True,
            }
        ],
        "metrics": [
            {
                "name": "packet completeness",
                "unit": "ratio",
                "threshold": threshold,
                "source_ref": "metric-contract:v1",
                "observed_value": observed,
                "comparison": "GTE",
                "locked_before_outcome": True,
            }
        ],
        "observers": [{"actor": "domain-reviewer", "role": "reviewer"}],
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
                "risk": "execution authority remains downstream",
                "status": "CLOSED",
                "owner": "reht",
            }
        ],
        "falsifier": "material bound state changes before clearance",
        "next_gate": {
            "action": "submit exact action to REHT",
            "reversible": True,
            "stop_rule": "stop if a bound digest changes",
        },
        "claims_correction": False,
        "high_stakes": False,
        "counter_source_refs": [],
        "sources": [],
        "duties": [],
        "inverse": None,
        "history": [],
        "run_version": 1,
    }


def _packet_digest(frozen):
    candidate = dict(frozen)
    candidate["replay"] = {
        "operator": "INDEPENDENT",
        "result": "PASS",
        "operator_ref": OPERATOR,
        "packet_digest": "sha256:" + "0" * 64,
        "packet_version": PACKET_VERSION,
        "blind": True,
        "deltas": [],
        "unresolved": [],
    }
    return replay_packet_digest(parse_evaluation_input(candidate))


def _request(frozen=None, digest=None, producer=PRODUCER):
    frozen = frozen or _frozen_packet()
    return {
        "action_ref": "action:1",
        "packet_digest": digest or _packet_digest(frozen),
        "packet_version": PACKET_VERSION,
        "evidence_bundle_digest": D1,
        "evidence_producer_ref": producer,
        "frozen_packet": frozen,
    }


def _artifact_digest(artifact):
    payload = dict(artifact)
    actual = payload.pop("artifact_digest")
    expected = "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()
    return actual, expected


def test_second_operator_replay_passes_only_canonical_packet():
    artifact = replay_frozen_packet(_request(), operator_ref=OPERATOR)
    assert artifact["result"] == "PASS"
    assert artifact["operator_kind"] == "INDEPENDENT"
    assert artifact["operator_ref"] == OPERATOR
    assert artifact["evidence_producer_ref"] == PRODUCER
    assert artifact["blind"] is True
    assert artifact["unresolved"] == []
    assert "execution_authority" not in artifact
    assert artifact["can_issue_clearance"] is False
    assert artifact["authority_effect"] == "NO_AUTHORITY_CREATION"
    actual, expected = _artifact_digest(artifact)
    assert actual == expected


def test_non_replay_blocker_remains_open_not_laundered_to_pass():
    frozen = _frozen_packet(threshold=None)
    artifact = replay_frozen_packet(_request(frozen=frozen), operator_ref=OPERATOR)
    assert artifact["result"] == "OPEN"
    assert "METRIC_THRESHOLD_UNKNOWN" in artifact["unresolved"]


def test_threshold_breach_remains_fail_not_laundered_to_pass():
    frozen = _frozen_packet(threshold=1.0, observed=0.5)
    artifact = replay_frozen_packet(_request(frozen=frozen), operator_ref=OPERATOR)
    assert artifact["result"] == "FAIL"
    assert "METRIC_THRESHOLD_BREACH" in artifact["unresolved"]


def test_packet_digest_mismatch_fails_replay():
    with pytest.raises(CoherenceReplayError, match="digest mismatch"):
        replay_frozen_packet(_request(digest=D2), operator_ref=OPERATOR)


def test_operator_must_differ_from_evidence_producer():
    with pytest.raises(CoherenceReplayError, match="must differ"):
        replay_frozen_packet(_request(producer=OPERATOR), operator_ref=OPERATOR)


def test_prior_replay_outcome_is_rejected_from_frozen_packet():
    frozen = _frozen_packet()
    digest = _packet_digest(frozen)
    frozen["replay"] = {"result": "PASS"}
    with pytest.raises(CoherenceReplayError, match="must not contain prior replay"):
        replay_frozen_packet(_request(frozen=frozen, digest=digest), operator_ref=OPERATOR)


def test_action_retargeting_is_rejected():
    frozen = _frozen_packet()
    frozen["boundary"]["object_id"] = "action:other"
    with pytest.raises(CoherenceReplayError, match="action boundary mismatch"):
        replay_frozen_packet(_request(frozen=frozen, digest=_packet_digest(frozen)), operator_ref=OPERATOR)


def test_http_service_requires_dedicated_configuration(monkeypatch):
    monkeypatch.delenv("VAIG_COHERENCE_REPLAY_OPERATOR_REF", raising=False)
    monkeypatch.delenv("VAIG_COHERENCE_REPLAY_TOKEN", raising=False)
    response = TestClient(app).post("/api/v1/coherence/replay", json=_request())
    assert response.status_code == 503


def test_http_service_requires_replay_token(monkeypatch):
    monkeypatch.setenv("VAIG_COHERENCE_REPLAY_OPERATOR_REF", OPERATOR)
    monkeypatch.setenv("VAIG_COHERENCE_REPLAY_TOKEN", "replay-secret")
    client = TestClient(app)
    unauthorized = client.post("/api/v1/coherence/replay", json=_request())
    assert unauthorized.status_code == 401
    authorized = client.post(
        "/api/v1/coherence/replay",
        json=_request(),
        headers={"Authorization": "Bearer replay-secret"},
    )
    assert authorized.status_code == 200
    assert authorized.json()["result"] == "PASS"
    assert authorized.json()["operator_ref"] == OPERATOR


def test_health_exposes_no_execution_authority(monkeypatch):
    monkeypatch.setenv("VAIG_COHERENCE_REPLAY_OPERATOR_REF", OPERATOR)
    monkeypatch.setenv("VAIG_COHERENCE_REPLAY_TOKEN", "replay-secret")
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "vaig-coherence-second-operator-replay",
        "operator_ref": OPERATOR,
        "operator_kind": "INDEPENDENT",
        "blind_to_prior_replay_outcome": True,
        "execution_authority": False,
        "requires_reht_clearance": True,
    }
