from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import src.valo_platform.action_envelope.continuity_runtime_gateway as gateway_module
from src.valo_platform.action_envelope.continuity_runtime_gateway import (
    OperationalContinuityCommitGateway,
)
from src.valo_platform.action_envelope.models import ClearanceState
from src.valo_platform.operational_continuity.commit_integration import (
    RevalidatedActionCaseCommitBinding,
)


NOW = datetime(2026, 8, 1, 15, 30, tzinfo=timezone.utc)
CURRENT = {
    "authority": "sha256:authority",
    "policy": "sha256:policy",
    "context": "sha256:context",
    "state": "sha256:state",
    "evidence": "sha256:evidence",
}


class Fingerprints:
    def as_mapping(self):
        return dict(CURRENT)


class RecordingRuntime:
    def __init__(self, cycle):
        self.cycle = cycle
        self.calls = []

    def revalidate(self, *, request_id, clearance_state, now):
        self.calls.append(
            {
                "request_id": request_id,
                "clearance_state": clearance_state,
                "now": now,
            }
        )
        return self.cycle


def cycle():
    request = SimpleNamespace(
        current_fingerprints=Fingerprints(),
        request_id="request-1",
    )
    return SimpleNamespace(
        request=request,
        assessment=SimpleNamespace(assessment_id="assessment-1"),
        result=SimpleNamespace(result_digest="sha256:result"),
    )


def full_binding():
    return RevalidatedActionCaseCommitBinding.model_construct(
        commit_binding=SimpleNamespace(),
        request_ref="request-ref",
        request_digest="sha256:request",
        assessment_ref="assessment-ref",
        assessment_digest="sha256:assessment",
        result_ref="result-ref",
        result_digest="sha256:result",
        proof_digest="sha256:proof",
        content_hash="sha256:binding",
    )


def test_gateway_runs_live_runtime_and_supplies_complete_proof_to_commit_bridge(monkeypatch):
    live_cycle = cycle()
    runtime = RecordingRuntime(live_cycle)
    expected_binding = full_binding()
    calls = []

    def fake_authorize(*args, **kwargs):
        calls.append((args, kwargs))
        return expected_binding

    monkeypatch.setattr(
        gateway_module,
        "authorize_verified_workflow_action_case_commit",
        fake_authorize,
    )
    gateway = OperationalContinuityCommitGateway(runtime)
    clearance = SimpleNamespace(state=ClearanceState.ACTIVE)

    result = gateway.authorize_verified_workflow_commit(
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
        clearance,
        SimpleNamespace(),
        SimpleNamespace(),
        request_id="request-1",
        current_workflow_states={"wf-1": SimpleNamespace()},
        adapter="sanity-content",
        target_system_ref="sanity:project:dataset",
        now=NOW,
        checkpoint_refs=("checkpoint:1",),
        revalidation_refs=("existing:1",),
    )

    assert runtime.calls == [
        {
            "request_id": "request-1",
            "clearance_state": ClearanceState.ACTIVE,
            "now": NOW,
        }
    ]
    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs["current_fingerprints"] == CURRENT
    assert kwargs["continuity_required"] is True
    assert kwargs["revalidation_request"] is live_cycle.request
    assert kwargs["continuity_assessment"] is live_cycle.assessment
    assert kwargs["revalidation_result"] is live_cycle.result
    assert kwargs["now"] == NOW
    assert kwargs["checkpoint_refs"] == ("checkpoint:1",)
    assert kwargs["revalidation_refs"] == ("existing:1",)
    assert result.revalidation is live_cycle
    assert result.commit_binding is expected_binding


def test_gateway_rejects_any_legacy_commit_binding(monkeypatch):
    runtime = RecordingRuntime(cycle())
    monkeypatch.setattr(
        gateway_module,
        "authorize_verified_workflow_action_case_commit",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    gateway = OperationalContinuityCommitGateway(runtime)

    with pytest.raises(
        RuntimeError,
        match="did not return full proof binding",
    ):
        gateway.authorize_verified_workflow_commit(
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(state=ClearanceState.ACTIVE),
            SimpleNamespace(),
            SimpleNamespace(),
            request_id="request-2",
            current_workflow_states={},
            adapter="adapter",
            target_system_ref="target",
            now=NOW,
        )
