from valo_health_pack import RESERVED_FUNCTION_IDS, seed_world
from valo_operator import OperatorRequest, build_health_runtime


def _request(correlation_id: str, function_id: str, input_name: str, value: dict):
    return OperatorRequest(
        correlation_id=correlation_id,
        function_id=function_id,
        inputs={input_name: value},
    )


def _state(runtime, entity_id: str) -> str | None:
    return runtime.kernel.state().entities[entity_id].state


def test_appointment_runs_function_fabric_reht_gateway_veritas_baro_kernel_chain():
    runtime = build_health_runtime()

    result = runtime.submit(
        _request(
            "health-book-1",
            "valo.health.book_appointment",
            "action",
            {"action_ref": "book-1", "slot_ref": "slot-1"},
        )
    )

    assert result.status == "COMPLETED"
    assert result.decision == "ALLOW"
    assert result.permit and result.permit.startswith("permit:")
    assert result.gateway_executions == 1
    assert result.effect_verified is True
    assert _state(runtime, "appointment-1") == "BOOKED"
    assert [receipt["kind"] for receipt in result.receipts] == [
        "authorization",
        "execution",
        "effect_verified",
    ]


def test_revoked_appointment_authority_denies_before_gateway_and_state_change():
    runtime = build_health_runtime(kernel=seed_world(revoke_appointment_authority=True))

    result = runtime.submit(
        _request(
            "health-book-revoked",
            "valo.health.book_appointment",
            "action",
            {"action_ref": "book-revoked", "slot_ref": "slot-1"},
        )
    )

    assert result.decision == "DENY"
    assert result.gateway_executions == 0
    assert result.effect_verified is False
    assert _state(runtime, "appointment-1") == "AVAILABLE"
    assert runtime.gateway.executions == []


def test_illegal_note_commit_from_draft_fails_before_external_effect():
    runtime = build_health_runtime()

    result = runtime.submit(
        _request(
            "health-note-illegal",
            "valo.health.commit_clinical_note",
            "candidate",
            {"candidate_ref": "candidate-1"},
        )
    )

    assert result.status == "FAILED"
    assert result.gateway_executions == 0
    assert result.effect_verified is False
    assert _state(runtime, "health-record-1") == "DRAFT"
    assert runtime.gateway.executions == []


def test_note_approval_and_commit_are_separate_authorized_effects():
    runtime = build_health_runtime()

    approved = runtime.submit(
        _request(
            "health-note-approve",
            "valo.health.approve_note_draft",
            "review",
            {"review_ref": "review-1", "candidate_digest": "sha256:" + "1" * 64},
        )
    )
    committed = runtime.submit(
        _request(
            "health-note-commit",
            "valo.health.commit_clinical_note",
            "candidate",
            {"candidate_ref": "candidate-1", "content_digest": "sha256:" + "1" * 64},
        )
    )

    assert approved.decision == committed.decision == "ALLOW"
    assert approved.effect_verified is True
    assert committed.effect_verified is True
    assert approved.permit != committed.permit
    assert _state(runtime, "health-record-1") == "NOTE_COMMITTED"
    assert [item["action_type"] for item in runtime.gateway.executions] == [
        "APPROVE_NOTE_DRAFT",
        "COMMIT_CLINICAL_NOTE",
    ]


def test_renewal_reaches_patient_notification_without_prescription_execution():
    runtime = build_health_runtime()
    calls = (
        ("valo.health.capture_renewal_request", "action"),
        ("valo.health.route_renewal_request", "renewal"),
        ("valo.health.request_clinical_review", "renewal"),
        ("valo.health.record_clinician_decision", "renewal"),
        ("valo.health.notify_patient", "action"),
    )

    results = []
    for index, (function_id, input_name) in enumerate(calls, start=1):
        result = runtime.submit(
            _request(
                f"renewal-{index}",
                function_id,
                input_name,
                {"renewal_ref": "renewal-1", "sequence": index},
            )
        )
        results.append(result)

    assert all(result.status == "COMPLETED" for result in results)
    assert all(result.decision == "ALLOW" for result in results)
    assert all(result.effect_verified for result in results)
    assert _state(runtime, "renewal-1") == "PATIENT_NOTIFIED"
    assert RESERVED_FUNCTION_IDS == ("valo.health.execute_authorized_prescription_action",)
    assert all(
        execution["action_type"] != "EXECUTE_AUTHORIZED_PRESCRIPTION_ACTION"
        for execution in runtime.gateway.executions
    )


def test_reht_permits_bind_distinct_health_actions():
    runtime = build_health_runtime()

    book = runtime.submit(
        _request(
            "bind-book",
            "valo.health.book_appointment",
            "action",
            {"action_ref": "book-1", "slot_ref": "slot-1"},
        )
    )
    reschedule = runtime.submit(
        _request(
            "bind-reschedule",
            "valo.health.reschedule_appointment",
            "action",
            {"action_ref": "move-1", "slot_ref": "slot-2"},
        )
    )

    assert book.decision == reschedule.decision == "ALLOW"
    assert book.permit != reschedule.permit
    assert _state(runtime, "appointment-1") == "RESCHEDULED"
