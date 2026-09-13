from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.valo_platform.action_envelope.outcome_attestation import CommitChainError
from src.valo_platform.action_envelope import verified_workflow_commit_bridge as bridge
from src.valo_platform.workflow_contracts.binding import (
    VerifiedWorkflowStateRef,
    WorkflowStateValidity,
)


NOW = datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc)
DIGEST = "sha256:" + "c" * 64
CURRENT = {
    "authority": "sha256:authority",
    "policy": "sha256:policy",
    "context": "sha256:context",
    "state": "sha256:state",
    "evidence": "sha256:evidence",
}


def workflow_state() -> VerifiedWorkflowStateRef:
    return VerifiedWorkflowStateRef(
        workflow_id="wf-1",
        workflow_version="1",
        workflow_fingerprint=DIGEST,
        workflow_state_fingerprint=DIGEST,
        verification_bundle_fingerprint=DIGEST,
        accepted=True,
        validity=WorkflowStateValidity.CURRENT,
        verified_at=NOW,
    )


def action_case(current: VerifiedWorkflowStateRef):
    return SimpleNamespace(evidence_refs=("evidence:other", current.evidence_ref))


def call(monkeypatch, *, continuity_required=False, request=None, assessment=None, result=None):
    current = workflow_state()
    calls = {"legacy": [], "continuity": []}

    def legacy(*args, **kwargs):
        calls["legacy"].append((args, kwargs))
        return "legacy-binding"

    def continuity(*args, **kwargs):
        calls["continuity"].append((args, kwargs))
        return "continuity-binding"

    monkeypatch.setattr(bridge, "authorize_action_case_commit", legacy)
    monkeypatch.setattr(
        bridge,
        "authorize_revalidated_action_case_commit",
        continuity,
    )

    value = bridge.authorize_verified_workflow_action_case_commit(
        object(),
        action_case(current),
        object(),
        object(),
        object(),
        object(),
        current_fingerprints=CURRENT,
        current_workflow_states={"wf-1": current},
        adapter="workflow-adapter",
        target_system_ref="target-1",
        now=NOW,
        continuity_required=continuity_required,
        revalidation_request=request,
        continuity_assessment=assessment,
        revalidation_result=result,
    )
    return value, calls, current


def test_legacy_workflow_commit_remains_on_existing_canonical_bridge(monkeypatch):
    value, calls, current = call(monkeypatch)

    assert value == "legacy-binding"
    assert len(calls["legacy"]) == 1
    assert calls["continuity"] == []
    assert current.evidence_ref in calls["legacy"][0][1]["revalidation_refs"]


def test_continuity_required_commit_cannot_fall_back_without_proof(monkeypatch):
    with pytest.raises(CommitChainError, match="PROOF_REQUIRED"):
        call(monkeypatch, continuity_required=True)


def test_partial_continuity_proof_fails_closed(monkeypatch):
    with pytest.raises(CommitChainError, match="PROOF_INCOMPLETE"):
        call(
            monkeypatch,
            request=SimpleNamespace(request_id="request-1"),
        )


def test_complete_proof_uses_full_chain_commit_wrapper(monkeypatch):
    request = SimpleNamespace(request_id="request-1")
    assessment = SimpleNamespace(assessment_id="assessment-1")
    result = SimpleNamespace(result_id="result-1")

    value, calls, current = call(
        monkeypatch,
        continuity_required=True,
        request=request,
        assessment=assessment,
        result=result,
    )

    assert value == "continuity-binding"
    assert calls["legacy"] == []
    assert len(calls["continuity"]) == 1
    kwargs = calls["continuity"][0][1]
    assert kwargs["revalidation_request"] is request
    assert kwargs["assessment"] is assessment
    assert kwargs["revalidation_result"] is result
    assert kwargs["checked_at"] == NOW
    assert current.evidence_ref in kwargs["revalidation_refs"]


def test_complete_proof_is_never_ignored_even_without_required_flag(monkeypatch):
    value, calls, _ = call(
        monkeypatch,
        request=SimpleNamespace(request_id="request-1"),
        assessment=SimpleNamespace(assessment_id="assessment-1"),
        result=SimpleNamespace(result_id="result-1"),
    )

    assert value == "continuity-binding"
    assert calls["legacy"] == []
    assert len(calls["continuity"]) == 1
