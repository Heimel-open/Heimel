from __future__ import annotations

from valo_reht import RealReht

CASE_CTX = {
    "actor": "system-1",
    "identity": "id-system-1",
    "time": {"now": "2026-08-08T00:00:00+00:00"},
    "authority": [{
        "authority_id": "auth-1",
        "principal": "system-1",
        "capability": "ISSUE_DECISION",
        "scope": ["case-1"],
        "constraints": {"service": "PUBLIC_SERVICE_A"},
        "validity": {"valid_from": "2026-01-01T00:00:00+00:00", "valid_until": "2030-01-01T00:00:00+00:00"},
        "status": "ACTIVE",
    }],
}


def _allow_contract(target="case-1", **extra):
    contract = {"capability": "ISSUE_DECISION", "target": target, "action_type": "ISSUE_DECISION"}
    contract.update(extra)
    return contract


def test_allow_in_scope() -> None:
    reht = RealReht()
    result = reht.authorize(CASE_CTX, _allow_contract())
    assert result.decision == "ALLOW"
    assert result.clearance_ref and result.clearance_ref.startswith("clearance:")
    assert result.permit_ref and result.permit_ref.startswith("permit:")
    assert result.execution_context_hash


def test_deny_without_identity() -> None:
    reht = RealReht()
    ctx = dict(CASE_CTX, identity=None)
    assert reht.authorize(ctx, _allow_contract()).decision == "DENY"


def test_deny_no_authority() -> None:
    reht = RealReht()
    ctx = dict(CASE_CTX, authority=[])
    result = reht.authorize(ctx, _allow_contract())
    assert result.decision == "DENY"
    assert "no active authority" in (result.reason or "")


def test_deny_out_of_scope() -> None:
    reht = RealReht()
    result = reht.authorize(CASE_CTX, _allow_contract(target="case-2"))
    assert result.decision == "DENY"
    assert "scope" in (result.reason or "")


def test_allow_empty_scope_is_unrestricted() -> None:
    ctx = {**CASE_CTX, "authority": [{**CASE_CTX["authority"][0], "scope": []}]}
    reht = RealReht()
    assert reht.authorize(ctx, _allow_contract(target="case-9")).decision == "ALLOW"


def test_allow_star_scope() -> None:
    ctx = {**CASE_CTX, "authority": [{**CASE_CTX["authority"][0], "scope": ["*"]}]}
    reht = RealReht()
    assert reht.authorize(ctx, _allow_contract(target="case-9")).decision == "ALLOW"


def test_deny_revoked_authority() -> None:
    ctx = {**CASE_CTX, "authority": [{**CASE_CTX["authority"][0], "status": "REVOKED"}]}
    reht = RealReht()
    assert reht.authorize(ctx, _allow_contract()).decision == "DENY"


def test_deny_expired_authority() -> None:
    ctx = {**CASE_CTX, "authority": [{
        **CASE_CTX["authority"][0],
        "validity": {"valid_from": "2026-01-01T00:00:00+00:00", "valid_until": "2026-02-01T00:00:00+00:00"},
    }]}
    reht = RealReht()
    assert reht.authorize(ctx, _allow_contract()).decision == "DENY"


def test_deny_constraint_mismatch() -> None:
    contract = _allow_contract(constraints={"service": "SERVICE_X"})
    reht = RealReht()
    result = reht.authorize(CASE_CTX, contract)
    assert result.decision == "DENY"


def test_allow_constraint_match() -> None:
    contract = _allow_contract(constraints={"service": "PUBLIC_SERVICE_A"})
    reht = RealReht()
    assert reht.authorize(CASE_CTX, contract).decision == "ALLOW"


def test_deny_required_purpose_not_permitted() -> None:
    ctx = {**CASE_CTX, "authority": [{
        **CASE_CTX["authority"][0],
        "constraints": {"service": "PUBLIC_SERVICE_A", "purposes": ["SERVICE_A"]},
    }]}
    contract = _allow_contract(purpose_id="SERVICE_B")
    reht = RealReht()
    assert reht.authorize(ctx, contract).decision == "DENY"


def test_allow_required_purpose_permitted() -> None:
    ctx = {**CASE_CTX, "authority": [{
        **CASE_CTX["authority"][0],
        "constraints": {"service": "PUBLIC_SERVICE_A", "purposes": ["SERVICE_A"]},
    }]}
    contract = _allow_contract(purpose_id="SERVICE_A")
    reht = RealReht()
    assert reht.authorize(ctx, contract).decision == "ALLOW"


def test_deterministic_artifact() -> None:
    reht_a, reht_b = RealReht(), RealReht()
    r_a = reht_a.authorize(CASE_CTX, _allow_contract())
    r_b = reht_b.authorize(CASE_CTX, _allow_contract())
    assert r_a.clearance_ref == r_b.clearance_ref
    assert r_a.permit_ref == r_b.permit_ref
    assert r_a.execution_context_hash == r_b.execution_context_hash


def test_deny_missing_clock() -> None:
    reht = RealReht()
    ctx = dict(CASE_CTX)
    ctx["time"] = {}
    result = reht.authorize(ctx, _allow_contract())
    assert result.decision == "DENY"
    assert "time" in (result.reason or "")


def test_deny_invalid_clock() -> None:
    reht = RealReht()
    ctx = {**CASE_CTX, "time": {"now": "not-a-time"}}
    result = reht.authorize(ctx, _allow_contract())
    assert result.decision == "DENY"
    assert "time" in (result.reason or "")


def test_deny_naive_clock() -> None:
    reht = RealReht()
    ctx = {**CASE_CTX, "time": {"now": "2026-08-08T00:00:00"}}
    result = reht.authorize(ctx, _allow_contract())
    assert result.decision == "DENY"
    assert "time" in (result.reason or "")


def test_deny_naive_validity_is_fail_closed() -> None:
    """An ACTIVE authority whose validity timestamps are naive must not be
    authorized — freshness cannot be proven."""
    reht = RealReht()
    ctx = {**CASE_CTX, "authority": [{
        **CASE_CTX["authority"][0],
        "validity": {"valid_from": "2026-01-01", "valid_until": "2030-01-01"},
    }]}
    result = reht.authorize(ctx, _allow_contract())
    assert result.decision == "DENY"
    assert "no active authority" in (result.reason or "")


def test_deny_wrong_principal() -> None:
    """Defense-in-depth: an authority for a DIFFERENT actor must not authorize
    this actor, even if the Kernel would have filtered it."""
    reht = RealReht()
    ctx = {**CASE_CTX, "actor": "other-actor", "authority": [
        {**CASE_CTX["authority"][0], "principal": "system-1"}
    ]}
    result = reht.authorize(ctx, _allow_contract())
    assert result.decision == "DENY"
    assert "no active authority" in (result.reason or "")


def test_deny_wrong_capability() -> None:
    """Defense-in-depth: an authority for the WRONG capability must not
    authorize an action requiring a different capability."""
    reht = RealReht()
    ctx = {**CASE_CTX, "authority": [
        {**CASE_CTX["authority"][0], "capability": "SOMETHING_ELSE"}
    ]}
    result = reht.authorize(ctx, _allow_contract())
    assert result.decision == "DENY"
    assert "no active authority" in (result.reason or "")


def test_permit_binds_full_action_contract() -> None:
    """permit(A) cannot execute B: changing any action-contract field must
    change the permit. Same context, different contract -> different permit."""
    reht = RealReht()
    r_a = reht.authorize(CASE_CTX, _allow_contract(action_type="ISSUE_DECISION"))
    r_b = reht.authorize(CASE_CTX, _allow_contract(action_type="ISSUE_DECISION_V2"))
    assert r_a.decision == "ALLOW" and r_b.decision == "ALLOW"
    assert r_a.permit_ref != r_b.permit_ref
    assert r_a.clearance_ref != r_b.clearance_ref


def test_permit_same_contract_same_permit() -> None:
    reht = RealReht()
    r_a = reht.authorize(CASE_CTX, _allow_contract())
    r_b = reht.authorize(CASE_CTX, _allow_contract())
    assert r_a.permit_ref == r_b.permit_ref
