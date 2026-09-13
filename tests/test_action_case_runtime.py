from datetime import datetime, timezone

import pytest

from src.valo_platform.action_case_runtime import (
    ActionCaseVerificationService,
    CaseCondition,
    ConcurrencyConflict,
    CorruptCase,
    DurableActionCaseStore,
    InMemoryAppendLog,
    build_registered_case,
    build_transition,
)
from src.valo_platform.memory_provider import canonical_digest

NOW = datetime(2026, 7, 26, 22, 0, tzinfo=timezone.utc)


def setup_case():
    log = InMemoryAppendLog()
    store = DurableActionCaseStore(log)
    service = ActionCaseVerificationService(store)
    case = build_registered_case(
        case_id="case-1",
        action_ref="action:1",
        principal_id="principal-1",
        registered_at=NOW,
    )
    service.register_case(case, idempotency_key="register-1")
    return log, store, service, case


def append(service, case, *, sequence, previous_digest, previous_state, next_state, key, artifact_type="evaluation"):
    transition = build_transition(
        case=case,
        sequence=sequence,
        previous_receipt_digest=previous_digest,
        previous_state=previous_state,
        next_state=next_state,
        artifact_type=artifact_type,
        artifact_digest=canonical_digest({"artifact": key}),
        actor_id="actor-1",
        idempotency_key=key,
        occurred_at=NOW,
    )
    return service.append_lifecycle_artifact(
        transition,
        expected_sequence=sequence - 1,
        expected_previous_digest=previous_digest,
    )


def test_register_and_append_chain_recover_deterministically():
    _, _, service, case = setup_case()
    first = append(service, case, sequence=1, previous_digest=None, previous_state="PROPOSED", next_state="EVALUATED", key="k1")
    second = append(service, case, sequence=2, previous_digest=first.receipt_digest, previous_state="EVALUATED", next_state="CLEARED", key="k2", artifact_type="clearance")

    recovered = service.get_current_verified_state(case.case_id)
    assert recovered.sequence == 2
    assert recovered.current_state == "CLEARED"
    assert recovered.last_receipt_digest == second.receipt_digest
    assert recovered.condition is CaseCondition.RECOVERED_REVALIDATION_REQUIRED
    assert recovered.automatic_continuation_allowed is False
    assert recovered.revalidation_required is True


def test_same_idempotency_retry_returns_existing_transition():
    _, _, service, case = setup_case()
    transition = build_transition(
        case=case,
        sequence=1,
        previous_receipt_digest=None,
        previous_state="PROPOSED",
        next_state="EVALUATED",
        artifact_type="evaluation",
        artifact_digest=canonical_digest({"x": 1}),
        actor_id="actor-1",
        idempotency_key="retry-1",
        occurred_at=NOW,
    )
    first = service.append_lifecycle_artifact(transition, expected_sequence=0, expected_previous_digest=None)
    retry = service.append_lifecycle_artifact(transition, expected_sequence=1, expected_previous_digest=first.receipt_digest)
    assert retry == first


def test_stale_expected_sequence_rejected():
    _, _, service, case = setup_case()
    transition = build_transition(
        case=case,
        sequence=1,
        previous_receipt_digest=None,
        previous_state="PROPOSED",
        next_state="EVALUATED",
        artifact_type="evaluation",
        artifact_digest=canonical_digest({"x": 1}),
        actor_id="actor-1",
        idempotency_key="k1",
        occurred_at=NOW,
    )
    with pytest.raises(ConcurrencyConflict, match="stale expected sequence"):
        service.append_lifecycle_artifact(transition, expected_sequence=9, expected_previous_digest=None)


def test_stale_previous_digest_rejected():
    _, _, service, case = setup_case()
    first = append(service, case, sequence=1, previous_digest=None, previous_state="PROPOSED", next_state="EVALUATED", key="k1")
    transition = build_transition(
        case=case,
        sequence=2,
        previous_receipt_digest=first.receipt_digest,
        previous_state="EVALUATED",
        next_state="CLEARED",
        artifact_type="clearance",
        artifact_digest=canonical_digest({"x": 2}),
        actor_id="actor-1",
        idempotency_key="k2",
        occurred_at=NOW,
    )
    with pytest.raises(ConcurrencyConflict, match="stale previous"):
        service.append_lifecycle_artifact(transition, expected_sequence=1, expected_previous_digest="sha256:" + "0" * 64)


def test_corrupt_receipt_quarantines_case():
    log, _, service, case = setup_case()
    first = append(service, case, sequence=1, previous_digest=None, previous_state="PROPOSED", next_state="EVALUATED", key="k1")
    payload = first.model_dump(mode="json")
    payload["next_state"] = "COMMITTED"
    log._records[case.case_id].append({"kind": "transition", "payload": payload})

    recovered = service.get_current_verified_state(case.case_id)
    assert recovered.condition is CaseCondition.QUARANTINED
    assert recovered.errors
    assert service.verify_full_chain(case.case_id).valid is False


def test_partial_log_record_quarantines_case():
    log, _, service, case = setup_case()
    log._records[case.case_id].append({"kind": "partial"})
    recovered = service.get_current_verified_state(case.case_id)
    assert recovered.condition is CaseCondition.QUARANTINED
    assert "partial or unknown log record" in recovered.errors


def test_cross_case_injection_rejected():
    _, _, service, case = setup_case()
    other = build_registered_case(case_id="case-2", action_ref="action:2", principal_id="principal-1", registered_at=NOW)
    transition = build_transition(
        case=other,
        sequence=1,
        previous_receipt_digest=None,
        previous_state="PROPOSED",
        next_state="EVALUATED",
        artifact_type="evaluation",
        artifact_digest=canonical_digest({"x": 1}),
        actor_id="actor-1",
        idempotency_key="k1",
        occurred_at=NOW,
    )
    transition = transition.model_copy(update={"case_id": case.case_id})
    with pytest.raises(CorruptCase):
        service.append_lifecycle_artifact(transition, expected_sequence=0, expected_previous_digest=None)


def test_terminal_case_cannot_continue():
    _, _, service, case = setup_case()
    terminal = append(service, case, sequence=1, previous_digest=None, previous_state="PROPOSED", next_state="DENIED", key="deny", artifact_type="denial")
    next_transition = build_transition(
        case=case,
        sequence=2,
        previous_receipt_digest=terminal.receipt_digest,
        previous_state="DENIED",
        next_state="EVALUATED",
        artifact_type="evaluation",
        artifact_digest=canonical_digest({"x": 2}),
        actor_id="actor-1",
        idempotency_key="after-terminal",
        occurred_at=NOW,
    )
    with pytest.raises(ConcurrencyConflict, match="terminal"):
        service.append_lifecycle_artifact(next_transition, expected_sequence=1, expected_previous_digest=terminal.receipt_digest)


def test_execution_recovery_requires_revalidation_and_no_resume():
    _, _, service, case = setup_case()
    running = append(service, case, sequence=1, previous_digest=None, previous_state="PROPOSED", next_state="EXECUTING", key="exec", artifact_type="execution_start")
    recovered = service.get_current_verified_state(case.case_id)
    assert recovered.condition is CaseCondition.INCOMPLETE_EXECUTION
    assert recovered.automatic_continuation_allowed is False
    assert recovered.revalidation_required is True
    assert recovered.last_receipt_digest == running.receipt_digest


def test_unresolved_outcome_recovery_is_distinct():
    _, _, service, case = setup_case()
    append(service, case, sequence=1, previous_digest=None, previous_state="PROPOSED", next_state="OUTCOME_RECORDED", key="outcome", artifact_type="outcome")
    recovered = service.get_current_verified_state(case.case_id)
    assert recovered.condition is CaseCondition.UNRESOLVED_OUTCOME


def test_remediation_link_is_explicit_and_separate_case():
    _, _, service, case = setup_case()
    child = build_registered_case(
        case_id="case-remediation",
        action_ref="action:remediation",
        principal_id="principal-1",
        registered_at=NOW,
        linked_parent_case_id=case.case_id,
    )
    service.register_linked_remediation_case(case.case_id, child, idempotency_key="register-remediation")
    recovered = service.get_current_verified_state(case.case_id)
    assert recovered.linked_remediation_cases == (child.case_id,)


def test_evidence_export_is_byte_identical_on_rerun():
    _, _, service, case = setup_case()
    first = append(service, case, sequence=1, previous_digest=None, previous_state="PROPOSED", next_state="EVALUATED", key="k1")
    append(service, case, sequence=2, previous_digest=first.receipt_digest, previous_state="EVALUATED", next_state="CLOSED", key="close", artifact_type="closure")

    a = service.export_evidence_package(case.case_id, unresolved_effects=("effect-1",), dissent=("dissent-1",))
    b = service.export_evidence_package(case.case_id, unresolved_effects=("effect-1",), dissent=("dissent-1",))
    assert a.model_dump_json() == b.model_dump_json()
    assert a.package_digest == b.package_digest
    assert a.verification.grants_authority is False
