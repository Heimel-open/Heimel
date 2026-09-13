"""Ten negative demonstrators — enforced by the REAL runtime path: Kernel
authorities (legal basis + competence), deterministic Case transition
admissibility, REHT, Gateway, Veritas, BARO."""

from __future__ import annotations

from valo_reht import RealReht

from valo_public_pack import run_golden, seed_world
from valo_public_pack.golden import Scenario


def test_negative_1_missing_legal_basis() -> None:
    """Legal basis is a SEPARATE Kernel authority from competence. When it is
    inactive, the decision boundary re-derives that no decision may be issued
    (kernel invariant), even though the competence authority is still active."""
    result = run_golden(reht=RealReht(), kernel=seed_world(legal_basis_active=False))
    assert result.case_state == "READY_FOR_DECISION", "decision must be blocked without legal basis"
    assert result.economics["executions_by_type"].get("ISSUE_DECISION", 0) == 0, "ISSUE_DECISION must never reach the Gateway"


def test_negative_2_revoked_competence() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(revoke_competence=True))
    assert result.case_state == "READY_FOR_DECISION", "decision must be blocked without competence"


def test_negative_3_invalid_representation() -> None:
    result = run_golden(reht=RealReht(), scenario=Scenario(has_representation=True, representation_scope_ok=False))
    assert result.case_state == "READY_FOR_DECISION", "invalid representation must block the decision"


def test_negative_4_conflicting_evidence() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(residency_conflicted=True))
    assert result.case_state == "READY_FOR_DECISION", "conflicted critical fact must block the decision"


def test_negative_5_habilitet() -> None:
    result = run_golden(reht=RealReht(), scenario=Scenario(decision_maker_relationship="SPOUSE"))
    assert result.case_state == "READY_FOR_DECISION", "DISQUALIFIED decision maker must block the decision"


def test_negative_6_expired_evidence() -> None:
    result = run_golden(reht=RealReht(), scenario=Scenario(evidence_stale=True))
    assert result.case_state == "READY_FOR_DECISION", "stale evidence must trigger revalidation, not a decision"


def test_negative_7_notification_failure() -> None:
    """Decision is issued, but delivery is not verified. Appeal deadline must
    NOT start; an exception is raised."""
    result = run_golden(reht=RealReht(), scenario=Scenario(notification_delivered=False))
    assert result.case_state == "DECIDED", "decision issued but not delivered"
    assert result.case_state != "APPEAL_PERIOD", "appeal deadline must not start without delivery"


def test_negative_8_direct_right_change() -> None:
    """No agent grants rights directly: there is no grant_right API; rights
    effects only arise through the issued decision."""
    from valo_public_pack.domain import CaseState

    kernel = seed_world()
    assert not hasattr(kernel.state().entities.get("case-1"), "grant_right")
    result = run_golden(reht=RealReht(), kernel=kernel)
    assert result.case_state == CaseState.CLOSED.value


def test_negative_9_purpose_violation() -> None:
    result = run_golden(reht=RealReht(), scenario=Scenario(purpose_violation=True))
    assert result.case_state == "READY_FOR_DECISION", "evidence from an unrelated purpose must block the decision"


def test_negative_10_equal_treatment() -> None:
    """Structurally equivalent cases with different outcomes produce a
    CONSISTENCY_REVIEW_REQUIRED signal — never an automatic override."""
    from valo_public_pack import comparable_case_signature, equal_treatment_signal

    a = comparable_case_signature({"residency": {"object": "NO", "status": "CONFIRMED"}}, "basis.public_service_a.v1", "GRANT")
    b = comparable_case_signature({"residency": {"object": "NO", "status": "CONFIRMED"}}, "basis.public_service_a.v1", "DENY")
    assert equal_treatment_signal(a, b) == "CONSISTENCY_REVIEW_REQUIRED"
