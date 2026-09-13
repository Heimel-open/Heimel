from __future__ import annotations

from valo_reht import RealReht

CTX = {
    "actor": "agent-1",
    "identity": "id-agent-1",
    "time": {"now": "2026-08-19T09:30:00+00:00"},
    "authority": [
        {
            "authority_id": "auth-step-up",
            "principal": "agent-1",
            "capability": "DO_EFFECT",
            "scope": ["target-1"],
            "constraints": {"purpose_id": "PURPOSE_A"},
            "validity": {
                "valid_from": "2026-01-01T00:00:00+00:00",
                "valid_until": "2030-01-01T00:00:00+00:00",
            },
            "status": "ACTIVE",
        }
    ],
}


def _action(**updates):
    action = {
        "capability": "DO_EFFECT",
        "target": "target-1",
        "purpose_id": "PURPOSE_A",
        "action_type": "DO_EFFECT",
    }
    action.update(updates)
    return action


def test_step_up_after_authority_match_emits_no_execution_artifacts() -> None:
    result = RealReht().authorize(
        CTX,
        _action(step_up={"required": True, "reason": "material ambiguity requires human approval"}),
    )
    assert result.decision == "STEP_UP"
    assert result.reason == "material ambiguity requires human approval"
    assert result.clearance_ref is None
    assert result.permit_ref is None
    assert result.execution_context_hash


def test_step_up_true_uses_deterministic_default_reason() -> None:
    result = RealReht().authorize(CTX, _action(step_up=True))
    assert result.decision == "STEP_UP"
    assert result.reason == "higher-assurance authorization required before execution"


def test_step_up_cannot_widen_capability() -> None:
    result = RealReht().authorize(CTX, _action(capability="UNAUTHORIZED", step_up=True))
    assert result.decision == "DENY"


def test_step_up_cannot_widen_scope() -> None:
    result = RealReht().authorize(CTX, _action(target="target-2", step_up=True))
    assert result.decision == "DENY"


def test_step_up_cannot_override_revocation() -> None:
    ctx = {
        **CTX,
        "authority": [{**CTX["authority"][0], "status": "REVOKED"}],
    }
    result = RealReht().authorize(ctx, _action(step_up=True))
    assert result.decision == "DENY"
