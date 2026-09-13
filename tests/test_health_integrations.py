from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_operator.adapters.health import (
    HealthConfiguredGateway,
    HealthConfiguredVeritas,
    ehr_vendor,
    provider_variant,
    renewal_workqueue_vendor,
    scheduling_vendor,
)
from valo_operator.adapters.integrations import spawn_service
from valo_operator.health_receipts import (
    FORBIDDEN_HEALTH_RECEIPT_FIELDS,
    HealthMinimumReceiptV1,
    HealthRetentionClass,
    HealthRetentionPolicyV1,
    HealthRetentionRule,
    assert_minimum_disclosure,
)

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64


def _provider_a_schedule(base_url: str):
    return scheduling_vendor(
        base_url,
        auth_header=("Authorization", "Bearer health-a"),
    )


def _provider_b_schedule(base_url: str):
    return provider_variant(
        scheduling_vendor(base_url),
        name="provider-b-scheduling",
        send_path="/api/actions/schedule",
        state_path="/api/state/schedule/{id}",
        id_field="resource_id",
        state_field="state",
        success_state="done",
        idempotency_header="X-Request-Key",
        auth_header=("X-API-Key", "health-b"),
    )


def _execute_and_observe(config, action_type: str, key: str):
    gateway = HealthConfiguredGateway(config)
    veritas = HealthConfiguredVeritas(config)
    action = {
        "action_type": action_type,
        "target": "health-target-1",
        "requested_transition": {"state": "requested"},
        "postconditions": {},
        "action_ref": f"action:{key}",
        "payload_digest": D1,
    }
    execution = gateway.execute("binding:health", action, key)
    observation = veritas.observe(execution, action)
    return gateway, execution, observation


def test_same_schedule_semantics_work_across_two_provider_protocols():
    svc = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        _, first_execution, first = _execute_and_observe(
            _provider_a_schedule(svc.base_url),
            "BOOK_APPOINTMENT",
            "book-a",
        )
        _, second_execution, second = _execute_and_observe(
            _provider_b_schedule(svc.base_url),
            "BOOK_APPOINTMENT",
            "book-b",
        )

        assert first_execution.success is True
        assert second_execution.success is True
        assert first.observed["appointment_booked"] is True
        assert second.observed["appointment_booked"] is True
        assert first.observed["outcome"] == second.observed["outcome"] == "VERIFIED"
    finally:
        svc.stop()


def test_ehr_commit_requires_independent_committed_readback():
    svc = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        config = ehr_vendor(
            svc.base_url,
            auth_header=("Authorization", "Bearer health-a"),
        )
        _, execution, observed = _execute_and_observe(
            config,
            "COMMIT_CLINICAL_NOTE",
            "note-1",
        )

        assert execution.success is True
        assert observed.observed["clinical_record_committed"] is True
        assert observed.observed["verified"] is True
    finally:
        svc.stop()


def test_renewal_workqueue_can_record_clinician_decision_but_does_not_prescribe():
    svc = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        config = renewal_workqueue_vendor(
            svc.base_url,
            auth_header=("Authorization", "Bearer health-a"),
        )
        _, _, observed = _execute_and_observe(
            config,
            "RECORD_CLINICIAN_DECISION",
            "renewal-decision-1",
        )

        assert observed.observed["clinician_decision_recorded"] is True
        assert "prescription_executed" not in observed.observed
    finally:
        svc.stop()


def test_unknown_health_action_cannot_become_verified_by_successful_api_call():
    svc = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        config = _provider_a_schedule(svc.base_url)
        _, execution, observed = _execute_and_observe(config, "DIAGNOSE_PATIENT", "bad-1")

        assert execution.success is True
        assert observed.observed["verified"] is False
        assert observed.observed["outcome"] == "NOT_VERIFIED"
        assert observed.observed["reason"] == "unknown_health_action_type"
    finally:
        svc.stop()


def test_unresolvable_readback_stays_unknown():
    svc = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        send_config = _provider_a_schedule(svc.base_url)
        gateway = HealthConfiguredGateway(send_config)
        action = {"action_type": "BOOK_APPOINTMENT", "target": "appointment-1"}
        execution = gateway.execute("binding:1", action, "unknown-1")

        broken = provider_variant(
            send_config,
            name="broken-observer",
            send_path=send_config.send_path,
            state_path="/does-not-exist/{id}",
            id_field=send_config.id_field,
            state_field=send_config.state_field,
            success_state=send_config.success_state,
            idempotency_header=send_config.idempotency_header or "Idempotency-Key",
            auth_header=send_config.auth_header,
        )
        observed = HealthConfiguredVeritas(broken).observe(execution, action)

        assert observed.observed == {"outcome": "UNKNOWN", "verified": False}
    finally:
        svc.stop()


def test_health_gateway_retry_does_not_send_second_effect():
    svc = spawn_service(
        "valo_operator.adapters.services.health_vendor",
        ready_prefix="HEALTH_VENDOR_READY",
    )
    try:
        config = _provider_a_schedule(svc.base_url)
        gateway = HealthConfiguredGateway(config)
        action = {"action_type": "BOOK_APPOINTMENT", "target": "appointment-1"}

        first = gateway.execute("binding:1", action, "same-key")
        second = gateway.execute("binding:1", action, "same-key")

        assert first.success is True
        assert second.external_id == "replayed"
        assert len(gateway.executions) == 1
    finally:
        svc.stop()


def test_health_minimum_receipt_contains_digests_not_raw_phi():
    receipt = HealthMinimumReceiptV1(
        correlation_id="corr-1",
        instance_id="instance-1",
        function_id="valo.health.commit_clinical_note",
        effect="clinical_record_committed",
        decision="ALLOW",
        permit_ref="permit:1",
        patient_context_digest=D1,
        candidate_or_action_digest=D2,
        destination_ref="ehr:clinic-1",
        execution_receipt_ref="execution:1",
        observed_outcome_digest=D1,
        observed_outcome_status="VERIFIED",
        retention_policy_ref="retention:health-min",
    )
    assert_minimum_disclosure(receipt)
    dumped = receipt.model_dump()

    assert FORBIDDEN_HEALTH_RECEIPT_FIELDS.isdisjoint(dumped)
    assert "patient_name" not in dumped
    assert "transcript_text" not in dumped
    assert "clinical_note" not in dumped


def test_raw_phi_cannot_be_smuggled_into_minimum_receipt():
    with pytest.raises(ValidationError):
        HealthMinimumReceiptV1.model_validate(
            {
                "correlation_id": "corr-1",
                "instance_id": "instance-1",
                "function_id": "valo.health.commit_clinical_note",
                "effect": "clinical_record_committed",
                "decision": "ALLOW",
                "patient_context_digest": D1,
                "candidate_or_action_digest": D2,
                "destination_ref": "ehr:clinic-1",
                "observed_outcome_status": "UNKNOWN",
                "retention_policy_ref": "retention:health-min",
                "transcript_text": "raw health information",
            }
        )


def test_retention_policy_can_drop_raw_audio_while_preserving_operational_proof():
    policy = HealthRetentionPolicyV1(
        policy_ref="retention:health-min",
        rules=(
            HealthRetentionRule(
                data_class=HealthRetentionClass.RAW_AUDIO,
                retain=False,
                ttl_seconds=0,
                storage_policy_ref="storage:none",
            ),
            HealthRetentionRule(
                data_class=HealthRetentionClass.OPERATIONAL_RECEIPT,
                retain=True,
                ttl_seconds=31_536_000,
                storage_policy_ref="storage:worm-health",
            ),
            HealthRetentionRule(
                data_class=HealthRetentionClass.MINIMUM_DISCLOSURE_PROOF,
                retain=True,
                ttl_seconds=31_536_000,
                storage_policy_ref="storage:worm-health",
            ),
        ),
    )

    rules = {rule.data_class: rule for rule in policy.rules}
    assert rules[HealthRetentionClass.RAW_AUDIO].retain is False
    assert rules[HealthRetentionClass.OPERATIONAL_RECEIPT].retain is True
