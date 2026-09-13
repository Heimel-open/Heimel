from __future__ import annotations

from valo_reht import RealReht

from valo_public_pack import run_golden, seed_world
from valo_public_pack.golden import Scenario
from valo_public_pack.integrity import (
    check_conflict_of_interest,
    comparable_case_signature,
    equal_treatment_signal,
    purpose_allows,
)
from valo_public_pack.legal import Competence, Delegation, LegalBasis
from valo_public_pack.trace import explain, replay


def _run(scenario: Scenario | None = None, **seed):
    kernel = seed_world(**seed) if seed else None
    return run_golden(reht=RealReht(), kernel=kernel, scenario=scenario)


def test_happy_path_closed() -> None:
    assert _run().case_state == "CLOSED"


def test_identity_verified() -> None:
    assert _run().instance_status == "COMPLETED"


def test_legal_basis_first_class() -> None:
    basis = LegalBasis(basis_id="b1", source="s", provision="§1", valid_from=__import__("datetime").datetime.now(__import__("datetime").UTC))
    assert basis.is_active(basis.valid_from + __import__("datetime").timedelta(hours=1))
    assert basis.permits_action("ISSUE_DECISION", basis.valid_from + __import__("datetime").timedelta(hours=1)) is False  # permits empty


def test_competence_first_class() -> None:
    from datetime import datetime, timedelta

    competence = Competence(competence_id="c1", public_body="pb", unit="u", capability="ISSUE_DECISION", scope=["*"], valid_from=datetime.now(__import__("datetime").UTC) - timedelta(days=1))
    assert competence.grants("pb", "u", "ISSUE_DECISION", ["case-1"], datetime.now(__import__("datetime").UTC))
    assert not competence.grants("wrong", "u", "ISSUE_DECISION", ["case-1"], datetime.now(__import__("datetime").UTC))


def test_delegation_narrower_scope_only() -> None:
    from datetime import datetime, timedelta

    parent = Competence(competence_id="c1", public_body="pb", unit="u", capability="ISSUE_DECISION", scope=["case-1", "case-2"], valid_from=datetime.now(__import__("datetime").UTC) - timedelta(days=1), valid_until=datetime.now(__import__("datetime").UTC) + timedelta(days=30))
    delegation = Delegation(delegation_id="d1", delegator="pb", delegate="pb2", competence_ref="c1", scope_reduction=["case-1"], valid_from=datetime.now(__import__("datetime").UTC) - timedelta(days=1))
    assert delegation.scope_ok(["case-1"])
    assert not delegation.scope_ok(["case-2"])  # cannot widen scope
    assert delegation.is_active(parent, datetime.now(__import__("datetime").UTC))
    assert not delegation.is_active(parent, datetime.now(__import__("datetime").UTC) + timedelta(days=5000))  # parent expiry kills it


def test_representation_enforced() -> None:
    assert _run(Scenario(has_representation=True, representation_scope_ok=False)).case_state == "READY_FOR_DECISION"


def test_habilitet_blocks() -> None:
    assert _run(Scenario(decision_maker_relationship="SPOUSE")).case_state == "READY_FOR_DECISION"
    assert check_conflict_of_interest("dm", "app", [{"subject": "dm", "object": "app", "kind": "SPOUSE"}]).value == "DISQUALIFIED"
    assert check_conflict_of_interest("dm", "app", []).value == "CLEAR"


def test_conflicted_residency_blocks_decision() -> None:
    assert _run(residency_conflicted=True).case_state == "READY_FOR_DECISION"


def test_stale_evidence_blocks_decision() -> None:
    assert _run(Scenario(evidence_stale=True)).case_state == "READY_FOR_DECISION"


def test_purpose_violation_blocks() -> None:
    assert _run(Scenario(purpose_violation=True)).case_state == "READY_FOR_DECISION"
    assert purpose_allows("SERVICE_A", "SERVICE_A", ["SERVICE_A"]) is True
    assert purpose_allows("SERVICE_A", "SERVICE_B", ["SERVICE_C"]) is False


def test_notification_failure_no_appeal() -> None:
    result = _run(Scenario(notification_delivered=False))
    assert result.case_state == "DECIDED"
    assert result.case_state != "APPEAL_PERIOD"


def test_legal_basis_expired_blocks() -> None:
    assert _run(legal_basis_active=False).case_state == "READY_FOR_DECISION"


def test_competence_revoked_blocks() -> None:
    assert _run(revoke_competence=True).case_state == "READY_FOR_DECISION"


def test_equal_treatment_signal() -> None:
    sig_a = comparable_case_signature({"residency": {"object": "NO", "status": "CONFIRMED"}}, "b", "GRANT")
    sig_b = comparable_case_signature({"residency": {"object": "NO", "status": "CONFIRMED"}}, "b", "DENY")
    assert equal_treatment_signal(sig_a, sig_b) == "CONSISTENCY_REVIEW_REQUIRED"
    assert equal_treatment_signal(sig_a, sig_a) == "NO_SIGNAL"


def test_explain_from_state() -> None:
    kernel = seed_world()
    result = run_golden(reht=RealReht(), kernel=kernel)
    explanation = explain(kernel, result.case_state)
    assert explanation["decision_ready"] is True
    assert explanation["legal_basis_active"] is True


def test_replay_matches() -> None:
    kernel = seed_world()
    result = run_golden(reht=RealReht(), kernel=kernel)
    report = replay(kernel, result.case_state)
    assert report["matches_original"] is True


def test_shadow_no_writes() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), shadow=True)
    assert result.case_state == "RECEIVED"
    assert result.economics["gateway_executions"] == 0
    assert result.economics["proposed_kernel_events"] > 0


def test_kernel_events_append_only() -> None:
    kernel = seed_world()
    before = kernel.sequence()
    run_golden(reht=RealReht(), kernel=kernel)
    assert kernel.sequence() > before


def test_kernel_revalidates_legal_basis_at_decision() -> None:
    """Legal basis is a separate Kernel authority; the decision boundary
    re-derives decidable-ness from it (inactive legal basis blocks)."""
    result = run_golden(reht=RealReht(), kernel=seed_world(legal_basis_active=False))
    assert result.case_state == "READY_FOR_DECISION"


def test_rights_effect_via_decision_only() -> None:
    """No direct right mutation: the case entity has no grant_right API."""
    kernel = seed_world()
    entity = kernel.state().entities["case-1"]
    assert not hasattr(entity, "grant_right")


def test_idempotency_key_dedup() -> None:
    from valo_public_pack.ports import PublicGateway

    gateway = PublicGateway()
    gateway.execute("binding", {"action_type": "NOTIFY"}, "key-1")
    r2 = gateway.execute("binding", {"action_type": "NOTIFY"}, "key-1")
    assert r2.external_id == "replayed"


def test_deadline_created_after_delivery() -> None:
    result = _run()
    assert result.case_state == "CLOSED"
    # appeal period was entered (APPEAL_PERIOD -> FINAL -> CLOSED)

    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    transitions = [e.payload.get("state") for e in kernel.events() if e.subject == "case-1" and e.event_type.value == "ENTITY_UPDATED"]
    assert "APPEAL_PERIOD" in transitions


def test_no_rights_impact_without_competence() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(revoke_competence=True))
    assert result.case_state == "READY_FOR_DECISION"
