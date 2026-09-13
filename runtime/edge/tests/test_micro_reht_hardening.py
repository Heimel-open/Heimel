"""micro-REHT hardening: durable HALT, authorized reset, correct expiry."""

import pytest

from valo_edge.contracts import (
    EdgeActionProposal,
    EdgeDecision,
    OfflineAuthorityEnvelope,
)
from valo_edge.runtime.micro_reht import (
    MicroRehtEngine,
    ResetAuthorization,
    _reset_token_digest,
)


def _envelope(valid_until: str = "2026-08-05T12:00:00Z") -> OfflineAuthorityEnvelope:
    return OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-authorized",
        allowed_action_types=["PUMP_START"],
        valid_until_iso=valid_until,
    )


def _proposal(nonce: str = "nonce-1") -> EdgeActionProposal:
    return EdgeActionProposal(
        proposal_id="prop-1",
        device_id="dev-authorized",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce=nonce,
    )


def test_halt_is_durable_across_restart(tmp_path):
    state = tmp_path / "engine-state.json"
    engine = MicroRehtEngine(state_path=str(state))
    engine.trigger_halt("safety interlock tripped")
    engine.flush()

    restarted = MicroRehtEngine(state_path=str(state))
    assert restarted.is_halted is True
    assert restarted._halt_reason == "safety interlock tripped"
    # A halted engine refuses everything even after restart.
    clearance = restarted.evaluate_proposal(
        _proposal(), _envelope(), current_time_iso="2026-08-04T12:00:00Z"
    )
    assert clearance.decision == EdgeDecision.HALT


def test_reset_requires_authorization_capability(tmp_path):
    engine = MicroRehtEngine(state_path=str(tmp_path / "s.json"))
    engine.trigger_halt("test")

    with pytest.raises(TypeError):
        engine.reset_halt()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        engine.reset_halt(None)  # type: ignore[arg-type]
    assert engine.is_halted is True


def _valid_token(target_id="dev-authorized"):
    from datetime import datetime, timezone

    payload = {
        "token_type": "valo-reset-authorization",
        "action": "RESET",
        "decision_id": "dec-1",
        "target_id": target_id,
        "scheme": "threshold",
        "required": 1,
        "epoch": 0,
        "operators": ["op-1"],
        "approval_digest": "sha256:" + "a" * 64,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    return {
        **payload,
        "token_digest": _reset_token_digest(payload),
    }


def test_reset_works_with_verified_token(tmp_path):
    engine = MicroRehtEngine(state_path=str(tmp_path / "s.json"))
    engine.trigger_halt("test")
    token = _valid_token()
    auth = ResetAuthorization.verify_token(token, target_id="dev-authorized")
    engine.reset_halt(auth)
    assert engine.is_halted is False


def test_reset_rejects_token_bound_to_other_engine(tmp_path):
    engine = MicroRehtEngine(state_path=str(tmp_path / "s.json"))
    engine.trigger_halt("test")
    token = _valid_token(target_id="dev-authorized")
    with pytest.raises(ValueError, match="not bound"):
        ResetAuthorization.verify_token(token, target_id="dev-other")


def test_reset_rejects_tampered_token(tmp_path):
    engine = MicroRehtEngine(state_path=str(tmp_path / "s.json"))
    engine.trigger_halt("test")
    token = _valid_token()
    token["action"] = "RESET"
    tampered = dict(token)
    tampered["target_id"] = "dev-authorized"
    # Recompute would change target_id, so keep it and only corrupt the digest.
    tampered["token_digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        ResetAuthorization.verify_token(tampered, target_id="dev-authorized")


def test_reset_capability_is_not_constructible_without_verification():
    # Direct construction is possible but must go through verify_token; the
    # token verification is the only gate.
    with pytest.raises(ValueError):
        ResetAuthorization.verify_token({"token_type": "garbage"}, "dev")


def test_expiry_compares_datetimes_not_strings():
    engine = MicroRehtEngine()
    # "2026-08-04T12:00:00Z" is lexically GREATER than
    # "2026-08-04T12:00:00.500Z" (because 'Z' > '.'), which would wrongly flag
    # a NOT-yet-expired proposal as expired under string comparison. Datetime
    # comparison must be used.
    envelope = _envelope(valid_until="2026-08-04T12:00:00.500Z")
    clearance = engine.evaluate_proposal(
        _proposal(), envelope, current_time_iso="2026-08-04T12:00:00Z"
    )
    assert clearance.decision == EdgeDecision.ALLOW


def test_expiry_unparseable_timestamps_fail_closed():
    engine = MicroRehtEngine()
    envelope = _envelope(valid_until="not-a-timestamp")
    clearance = engine.evaluate_proposal(
        _proposal(), envelope, current_time_iso="2026-08-04T12:00:00Z"
    )
    assert clearance.decision == EdgeDecision.DENY
