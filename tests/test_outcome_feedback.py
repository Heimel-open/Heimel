from __future__ import annotations

from copy import deepcopy

import pytest

from valo_reht import (
    EAR_V1,
    VERITAS_WORM_OUTCOME_V1,
    RealReht,
    bind_verified_outcome_state,
)


def _ctx() -> dict:
    return {
        "actor": "system-1",
        "identity": "id-system-1",
        "time": {"now": "2026-08-10T10:00:00+00:00"},
        "sequence": 8,
        "execution_nonce": "nonce-8",
        "state_ref": "state-8",
        "authority_state": {
            "drift_detected": False,
            "attested_surface_hash": "surface-a",
            "current_surface_hash": "surface-a",
        },
        "causal": {
            "hop_depth": 1,
            "prior_permit_ref": "permit:prior",
            "reauthorized": True,
        },
        "gates": {},
        "authority": [
            {
                "authority_id": "auth-1",
                "principal": "system-1",
                "capability": "EXECUTE_ACTION",
                "scope": ["target-1"],
                "constraints": {},
                "validity": {
                    "valid_from": "2026-01-01T00:00:00+00:00",
                    "valid_until": "2030-01-01T00:00:00+00:00",
                },
                "status": "ACTIVE",
            }
        ],
    }


def _contract(**extra) -> dict:
    contract = {
        "execution_authorization_profile": EAR_V1,
        "capability": "EXECUTE_ACTION",
        "target": "target-1",
        "action_type": "EXECUTE_ACTION",
        "state_ref": "state-8",
        "side_effecting": True,
        "impact": "MEDIUM",
        "reversible": True,
        "requires_verified_prior_outcome": True,
    }
    contract.update(extra)
    return contract


def _outcome(**extra) -> dict:
    outcome = {
        "schema": VERITAS_WORM_OUTCOME_V1,
        "verified": True,
        "worm_chain_verified": True,
        "authority_granted": False,
        "execution_id": "exec-prior",
        "permit_ref": "permit:prior",
        "clearance_ref": "clearance:prior",
        "status": "succeeded",
        "observation_package_ref": "gateway-execution:exec-prior",
        "observation_package_digest": "sha256:" + "a" * 64,
        "worm_entry_ref": "worm:gateway-execution:exec-prior",
    }
    outcome.update(extra)
    return outcome


def test_verified_worm_outcome_is_explicit_input_to_next_reht_decision() -> None:
    ctx = bind_verified_outcome_state(_ctx(), _outcome())
    result = RealReht().authorize(ctx, _contract())

    assert result.decision == "ALLOW"
    projected = ctx["authority_state"]["verified_prior_execution"]
    assert projected["execution_id"] == "exec-prior"
    assert projected["status"] == "succeeded"
    assert projected["authority_granted"] is False


def test_missing_prior_outcome_fails_closed() -> None:
    result = RealReht().authorize(_ctx(), _contract())
    assert result.decision == "DENY"
    assert "EA-09" in (result.reason or "")


def test_tampered_worm_verification_fails_closed() -> None:
    ctx = deepcopy(_ctx())
    ctx["prior_execution_outcome"] = _outcome(worm_chain_verified=False)
    result = RealReht().authorize(ctx, _contract())
    assert result.decision == "DENY"
    assert "WORM" in (result.reason or "")


def test_veritas_cannot_smuggle_authority() -> None:
    with pytest.raises(ValueError, match="attempted to carry authority"):
        bind_verified_outcome_state(_ctx(), _outcome(authority_granted=True))


def test_prior_permit_must_match_causal_chain() -> None:
    ctx = bind_verified_outcome_state(_ctx(), _outcome(permit_ref="permit:other"))
    result = RealReht().authorize(ctx, _contract())
    assert result.decision == "DENY"
    assert "causal permit" in (result.reason or "")


def test_failed_prior_execution_is_denied_by_default() -> None:
    ctx = bind_verified_outcome_state(_ctx(), _outcome(status="failed"))
    result = RealReht().authorize(ctx, _contract())
    assert result.decision == "DENY"
    assert "not admissible" in (result.reason or "")


def test_action_may_explicitly_accept_verified_failed_outcome() -> None:
    ctx = bind_verified_outcome_state(_ctx(), _outcome(status="failed"))
    contract = _contract(acceptable_prior_outcomes=["succeeded", "failed"])
    assert RealReht().authorize(ctx, contract).decision == "ALLOW"


def test_outcome_feedback_never_restores_revoked_authority() -> None:
    ctx = bind_verified_outcome_state(_ctx(), _outcome())
    authority = deepcopy(ctx["authority"][0])
    authority["status"] = "REVOKED"
    ctx["authority"] = [authority]
    result = RealReht().authorize(ctx, _contract())
    assert result.decision == "DENY"
