from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from valo_reht import RealReht

from valo_public_pack import run_golden, seed_world
from valo_public_pack.golden import Scenario


@settings(max_examples=8)
@given(st.booleans())
def test_property_no_decision_without_legal_basis(active) -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(legal_basis_active=active))
    if active:
        assert result.case_state == "CLOSED"
    else:
        assert result.case_state != "DECIDED"


@settings(max_examples=8)
@given(st.booleans())
def test_property_no_decision_without_competence(revoked) -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(revoke_competence=revoked))
    if revoked:
        assert result.case_state != "DECIDED"
    else:
        assert result.case_state == "CLOSED"


def test_property_no_conflicted_fact_silently_confirmed() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(residency_conflicted=True))
    assert result.case_state != "DECIDED"


def test_property_no_appeal_deadline_before_delivery() -> None:
    result = run_golden(reht=RealReht(), scenario=Scenario(notification_delivered=False))
    assert result.case_state != "APPEAL_PERIOD"


def test_property_no_direct_right_mutation() -> None:
    kernel = seed_world()
    entity = kernel.state().entities["case-1"]
    assert not hasattr(entity, "grant_right")


def test_property_shadow_never_writes() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), shadow=True)
    assert result.case_state == "RECEIVED"
    assert result.economics["gateway_executions"] == 0


def test_property_compiled_graph_valid_isa() -> None:
    from valo_workflow_isa import compile_graph as isa_compile

    from valo_public_pack import build_public_registry, compile_golden

    isa_compile(compile_golden(build_public_registry()).workflow_graph)


def test_property_reht_matches_kernel_authority() -> None:
    healthy = run_golden(reht=RealReht(), kernel=seed_world())
    revoked = run_golden(reht=RealReht(), kernel=seed_world(revoke_competence=True))
    assert all(d["decision"] == "ALLOW" for d in healthy.reht_decisions)
    # competence is the REHT check (legal basis is a separate kernel authority)
    assert any(d["decision"] == "DENY" for d in revoked.reht_decisions)


def test_property_delegation_never_widens() -> None:
    from datetime import datetime, timedelta

    from valo_public_pack.legal import Competence, Delegation

    parent = Competence(competence_id="c1", public_body="pb", unit="u", capability="X", scope=["a", "b"], valid_from=datetime.now(__import__("datetime").UTC) - timedelta(days=1), valid_until=datetime.now(__import__("datetime").UTC) + timedelta(days=30))
    delegation = Delegation(delegation_id="d1", delegator="pb", delegate="pb2", competence_ref="c1", scope_reduction=["a"], valid_from=datetime.now(__import__("datetime").UTC) - timedelta(days=1))
    assert delegation.is_active(parent, datetime.now(__import__("datetime").UTC))
    assert delegation.scope_ok(["a"])
    assert not delegation.scope_ok(["b"])
    assert not delegation.scope_ok(["c"])
