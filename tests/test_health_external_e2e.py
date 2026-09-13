from __future__ import annotations

from valo_health_pack import RESERVED_FUNCTION_IDS, seed_world
from valo_operator import OperatorRequest, build_health_runtime
from valo_operator.adapters.health import (
    HealthConfiguredGateway,
    HealthConfiguredVeritas,
    ehr_vendor,
    renewal_workqueue_vendor,
    scheduling_vendor,
)
from valo_operator.adapters.integrations import spawn_service
from valo_operator.health_receipts import project_health_minimum_receipt

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64


def _request(correlation_id: str, function_id: str, input_name: str, value: dict) -> OperatorRequest:
    return OperatorRequest(
        correlation_id=correlation_id,
        function_id=function_id,
        inputs={input_name: value},
    )


def _runtime(config, *, kernel=None):
    return build_health_runtime(
        kernel=kernel,
        gateway=HealthConfiguredGateway(config),
        veritas=HealthConfiguredVeritas(config),
    )


def test_external_appointment_flow_crosses_reht_and_is_verified_by_readback():
    service = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        config = scheduling_vendor(
            service.base_url,
            auth_header=("Authorization", "Bearer health-a"),
        )
        runtime = _runtime(config)
        result = runtime.submit(
            _request(
                "external-book-1",
                "valo.health.book_appointment",
                "action",
                {
                    "action_ref": "book-1",
                    "patient_ref": "patient-1",
                    "appointment_ref": "appointment-1",
                    "slot_ref": "slot-1",
                    "payload_digest": D2,
                },
            )
        )

        assert result.status == "COMPLETED"
        assert result.decision == "ALLOW"
        assert result.permit and result.permit.startswith("permit:")
        assert result.gateway_executions == 1
        assert result.effect_verified is True
        assert runtime.kernel.state().entities["appointment-1"].state == "BOOKED"

        proof = project_health_minimum_receipt(
            result,
            patient_context_digest=D1,
            candidate_or_action_digest=D2,
            destination_ref="schedule:provider-a",
            retention_policy_ref="retention:health-min",
        )
        assert proof.observed_outcome_status == "VERIFIED"
        assert proof.execution_receipt_ref
        assert "patient_name" not in proof.model_dump()
        assert "transcript_text" not in proof.model_dump()
    finally:
        service.stop()


def test_external_provider_receives_zero_effect_after_reht_revocation():
    service = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        config = scheduling_vendor(
            service.base_url,
            auth_header=("Authorization", "Bearer health-a"),
        )
        runtime = _runtime(config, kernel=seed_world(revoke_appointment_authority=True))
        result = runtime.submit(
            _request(
                "external-book-revoked",
                "valo.health.book_appointment",
                "action",
                {"action_ref": "book-revoked", "slot_ref": "slot-1", "payload_digest": D2},
            )
        )

        assert result.decision == "DENY"
        assert result.gateway_executions == 0
        assert runtime.gateway.executions == []
        assert runtime.kernel.state().entities["appointment-1"].state == "AVAILABLE"
    finally:
        service.stop()


def test_external_note_review_and_commit_are_separate_verified_effects():
    service = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        config = ehr_vendor(
            service.base_url,
            auth_header=("Authorization", "Bearer health-a"),
        )
        runtime = _runtime(config)

        review = runtime.submit(
            _request(
                "external-note-review",
                "valo.health.approve_note_draft",
                "review",
                {
                    "review_ref": "review-1",
                    "patient_ref": "patient-1",
                    "candidate_digest": D1,
                },
            )
        )
        commit = runtime.submit(
            _request(
                "external-note-commit",
                "valo.health.commit_clinical_note",
                "candidate",
                {
                    "candidate_ref": "candidate-1",
                    "patient_ref": "patient-1",
                    "content_digest": D1,
                },
            )
        )

        assert review.decision == commit.decision == "ALLOW"
        assert review.effect_verified is True
        assert commit.effect_verified is True
        assert review.permit != commit.permit
        assert runtime.kernel.state().entities["health-record-1"].state == "NOTE_COMMITTED"
        assert len(runtime.gateway.executions) == 2
    finally:
        service.stop()


def test_external_renewal_workflow_stops_at_clinician_decision_and_notification():
    service = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        config = renewal_workqueue_vendor(
            service.base_url,
            auth_header=("Authorization", "Bearer health-a"),
        )
        runtime = _runtime(config)
        sequence = (
            ("valo.health.capture_renewal_request", "action"),
            ("valo.health.route_renewal_request", "renewal"),
            ("valo.health.request_clinical_review", "renewal"),
            ("valo.health.record_clinician_decision", "renewal"),
            ("valo.health.notify_patient", "action"),
        )

        results = []
        for index, (function_id, input_name) in enumerate(sequence, start=1):
            results.append(
                runtime.submit(
                    _request(
                        f"external-renewal-{index}",
                        function_id,
                        input_name,
                        {
                            "renewal_ref": "renewal-1",
                            "patient_ref": "patient-1",
                            "payload_digest": D2,
                            "sequence": index,
                        },
                    )
                )
            )

        assert all(result.status == "COMPLETED" for result in results)
        assert all(result.decision == "ALLOW" for result in results)
        assert all(result.effect_verified for result in results)
        assert runtime.kernel.state().entities["renewal-1"].state == "PATIENT_NOTIFIED"
        assert RESERVED_FUNCTION_IDS == ("valo.health.execute_authorized_prescription_action",)
        assert len(runtime.gateway.executions) == 5
        assert all(
            execution["action_type"] != "EXECUTE_AUTHORIZED_PRESCRIPTION_ACTION"
            for execution in runtime.gateway.executions
        )
    finally:
        service.stop()
