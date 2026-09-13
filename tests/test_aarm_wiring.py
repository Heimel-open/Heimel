"""Tests that the canonical AARM engine is wired into the API and orchestrator.

The REST layer and the orchestration layer must produce verdicts from the same
canonical `aarm_decide` engine, not from divergent ad-hoc thresholds.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from vaig.aarm import (
    AARMSignal,
    AARMVerdict,
    aarm_decide,
    verdict_from_evidence,
)
from vaig.api import app
from vaig.ensemble import DistrustLevel, ValidationResult
from vaig.evidence_intake import (
    EvidenceIntakeRequest,
    EvidenceIntakeState,
)
from vaig.orchestrator import (
    OrchestratorResult,
    VAIGOrchestrator,
    aarm_signal_from_result,
)

NOW = datetime(2026, 7, 29, 16, 30, tzinfo=timezone.utc)

GOOD_EVIDENCE = {
    "risk_score": 0.1,
    "uncertainty": 0.1,
    "drift_score": 0.0,
    "observation_trust": 0.9,
    "reversibility": "reversible",
    "claims_substantiated": True,
    "evidence_valid": True,
}


def test_verdict_from_evidence_allows_with_good_evidence():
    verdict, signal = verdict_from_evidence(GOOD_EVIDENCE)
    assert verdict is AARMVerdict.ALLOW
    assert signal.risk_class == "low"


def test_verdict_from_evidence_fails_closed_without_evidence_valid():
    evidence = dict(GOOD_EVIDENCE)
    evidence.pop("evidence_valid")
    verdict, _ = verdict_from_evidence(evidence)
    assert verdict is AARMVerdict.HALT


def test_verdict_from_evidence_fails_closed_on_empty_evidence():
    verdict, _ = verdict_from_evidence({})
    assert verdict is not AARMVerdict.ALLOW


def test_verdict_from_evidence_denies_authority_overreach():
    evidence = {
        **GOOD_EVIDENCE,
        "tool_authority": "delete",
        "task_authority": "read",
    }
    verdict, _ = verdict_from_evidence(evidence)
    assert verdict is AARMVerdict.DENY


def test_verdict_from_evidence_risk_score_maps_to_risk_class():
    verdict, _ = verdict_from_evidence({"risk_score": 0.9, "evidence_valid": True})
    assert verdict is AARMVerdict.HALT


def test_authorize_endpoint_returns_canonical_verdicts():
    client = TestClient(app)
    response = client.post(
        "/api/v1/authorize",
        json={"intent": "user:maria:write:secrets", "evidence": GOOD_EVIDENCE},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "ALLOW"
    assert payload["reason"]
    assert payload["receipt"]["worm_hash"].startswith("sha256:")
    assert len(payload["receipt"]["worm_hash"]) == 64 + len("sha256:")

    blocked = client.post(
        "/api/v1/authorize",
        json={"intent": "user:maria:write:secrets", "evidence": {"risk_score": 0.9}},
    )
    assert blocked.json()["decision"] == "HALT"


def _empty_plan(orchestrator):
    orchestrator.ensemble.instruments = {}
    orchestrator.dirigent.conduct = lambda _terrain: SimpleNamespace(
        internal=[],
        external=[],
        bench=[],
        thresholds={},
        context_health=1.0,
        context_warning=None,
        context_warning_detail=None,
    )


def test_orchestrator_result_carries_aarm_verdict(tmp_path):
    orchestrator = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        with_cakm=False,
    )
    _empty_plan(orchestrator)
    result = orchestrator.evaluate(
        prompt="Summarize this email",
        response="Done.",
    )
    assert result.aarm_verdict in set(AARMVerdict)
    assert result.evidence_intake is not None


def test_orchestrator_halts_when_required_evidence_is_missing(tmp_path):
    orchestrator = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        with_cakm=False,
    )
    _empty_plan(orchestrator)
    request = EvidenceIntakeRequest(
        required=True,
        intended_use="approve_payment",
        expected_case_id="case-1",
        expected_package_id="package-1",
        expected_package_version="v1",
        expected_package_digest="sha256:" + "e" * 64,
        max_package_age_seconds=3600,
    )
    result = orchestrator.evaluate(
        prompt="Approve payment",
        response="Approved",
        evidence_request=request,
        evidence_now=NOW,
    )
    assert result.evidence_intake.state is EvidenceIntakeState.MISSING
    assert result.aarm_verdict is AARMVerdict.HALT
    assert result.should_halt is True


def _manual_result(**overrides) -> OrchestratorResult:
    validation = ValidationResult(
        entry_id="validation-1",
        level=DistrustLevel.TRUSTED,
        combined_score=0.05,
        scores={},
        worm_hash="0" * 64,
        latency_ms=0.1,
    )
    terrain = SimpleNamespace(
        domain=SimpleNamespace(value="research"),
        risk_type="structure",
        confidence=0.8,
        uncertainty=0.2,
    )
    defaults = {
        "validation": validation,
        "terrain": terrain,
        "activated_internal": [],
        "activated_external": [],
        "skipped": [],
    }
    defaults.update(overrides)
    return OrchestratorResult(**defaults)


def test_aarm_signal_from_result_uses_drift_slot():
    validation = ValidationResult(
        entry_id="validation-1",
        level=DistrustLevel.TRUSTED,
        combined_score=0.05,
        scores={"goal_drift_detector": 0.9},
        worm_hash="0" * 64,
        latency_ms=0.1,
    )
    result = _manual_result(validation=validation)
    signal = aarm_signal_from_result(result)
    assert signal.drift_score == 0.9
    assert aarm_decide(signal) is AARMVerdict.HALT


def test_aarm_signal_from_result_fails_closed_without_evidence():
    signal = aarm_signal_from_result(_manual_result(evidence_intake=None))
    assert signal.evidence_valid is False
    assert aarm_decide(signal) is AARMVerdict.HALT


def test_should_halt_includes_aarm_halt():
    result = _manual_result(aarm_verdict=AARMVerdict.HALT)
    assert result.should_halt is True
