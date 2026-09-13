from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_external_adapters.contracts import (
    CandidateKind,
    CapabilityLease,
    GovernedProjectionEnvelope,
    GovernedWorkspaceEnvelope,
    ProjectedObject,
    ProjectionSelector,
    StateDependency,
    WorkspaceCapabilitySpec,
    WorkspaceSpec,
    canonical_digest,
)
from valo_external_adapters.uhp import (
    UHP_PROTOCOL_VERSION,
    UHPArtifactReference,
    UHPConformanceClass,
    UHPDiscoveryDocument,
    UHPHarnessDescriptor,
    UHPWorkerTaskBinding,
    build_uhp_artifact_content_request,
    build_uhp_artifact_list_request,
    build_uhp_cancel_request,
    build_uhp_discovery_request,
    build_uhp_worker_task,
    record_uhp_discovery,
    record_uhp_worker_result,
)

NOW = datetime(2026, 8, 17, 13, 30, tzinfo=UTC)


def _workspace() -> GovernedWorkspaceEnvelope:
    expires_at = NOW + timedelta(minutes=10)
    payload = {"name": "Quarterly report"}
    projected = ProjectedObject(
        collection="entities",
        object_id="entity-1",
        payload=payload,
        payload_digest=canonical_digest(payload),
    )
    dependency = StateDependency(
        collection="entities",
        object_id="entity-1",
        object_digest=projected.payload_digest,
    )
    projection = GovernedProjectionEnvelope(
        projection_id="projection-1",
        tenant_id="tenant-1",
        purpose_id="purpose-1",
        source_state_root="a" * 64,
        source_event_position=7,
        projected_at=NOW,
        expires_at=expires_at,
        objects=(projected,),
        dependencies=(dependency,),
        dependency_digest=canonical_digest(
            [dependency.model_dump(mode="json")]
        ),
    )
    capability = WorkspaceCapabilitySpec(
        capability="produce_candidate",
        target_refs=("entity-1",),
    )
    spec = WorkspaceSpec(
        workspace_id="workspace-1",
        work_unit_id="work-unit-1",
        tenant_id="tenant-1",
        purpose_id="purpose-1",
        selectors=(
            ProjectionSelector(
                collection="entities",
                object_ids=("entity-1",),
            ),
        ),
        capabilities=(capability,),
        allowed_output_kinds=(CandidateKind.ARTIFACT, CandidateKind.EXTERNAL_ACTION),
        expires_at=expires_at,
    )
    lease = CapabilityLease(
        handle_ref=f"capability:sha256:{'b' * 64}",
        capability=capability.capability,
        target_refs=capability.target_refs,
        allowed_effects=capability.allowed_effects,
        parameter_constraints=capability.parameter_constraints,
        valid_until=expires_at,
    )
    unsealed = GovernedWorkspaceEnvelope(
        spec=spec,
        projection=projection,
        capability_leases=(lease,),
    )
    return GovernedWorkspaceEnvelope.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "workspace_digest": unsealed.computed_digest,
        }
    )


def _discovery(
    *, idempotency: bool = True, sessions: bool = True
) -> UHPDiscoveryDocument:
    return UHPDiscoveryDocument(
        versions=(UHP_PROTOCOL_VERSION,),
        default_version=UHP_PROTOCOL_VERSION,
        conformance_class=UHPConformanceClass.EXTENDED,
        capabilities={
            "streaming": True,
            "sessions": sessions,
            "cancellation": True,
            "files_input": True,
            "files_output": True,
            "session_listing": True,
            "harness_management": False,
            "session_sharing": False,
            "idempotency": idempotency,
        },
        implementation={"name": "test-uhp", "version": "1"},
    )


def _harness() -> UHPHarnessDescriptor:
    return UHPHarnessDescriptor.model_validate(
        {
            "id": "chrn_test",
            "object": "harness",
            "name": "Replaceable worker",
            "base": "future-harness-x",
            "baseLabel": "Future Harness X",
            "defaultModel": "model-a",
            "disabledTools": ["ExternalEffect"],
            "maxStep": 20,
            "timeoutSeconds": 300,
            "createdAt": 1786973400000,
        }
    )


def _build_task(
    *,
    input_text: str = "Review the projected report and propose corrections.",
    requested_model: str | None = "model-a",
    previous_response_id: str | None = None,
    discovery: UHPDiscoveryDocument | None = None,
):
    return build_uhp_worker_task(
        workspace=_workspace(),
        discovery=discovery or _discovery(),
        harness=_harness(),
        worker_id="worker-uhp-1",
        input_text=input_text,
        effect_isolation_ref="effect-boundary-assurance-1",
        effect_isolation_digest="c" * 64,
        constructed_at=NOW + timedelta(minutes=1),
        requested_model=requested_model,
        previous_response_id=previous_response_id,
        instructions="Return candidate work with evidence references.",
        max_step=8,
        timeout_seconds=120,
    )


def _response(*, actual_model: str = "model-a", fallback: bool = False):
    metadata = {
        "session_id": "sess_1",
        "harness_id": "chrn_test",
    }
    if fallback:
        metadata.update(
            {
                "requested_model": "model-a",
                "model_fallback": True,
                "model_fallback_reason": "model-a unavailable for this harness",
            }
        )
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 1786973460,
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "previous_response_id": None,
        "model": actual_model,
        "output": [
            {
                "id": "fc_1",
                "type": "function_call",
                "call_id": "call_1",
                "name": "read_file",
                "arguments": '{"path":"README.md"}',
                "status": "completed",
            },
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Candidate complete.",
                        "annotations": [
                            {
                                "type": "container_file_citation",
                                "container_id": "cntr_1",
                                "file_id": "file_1",
                                "filename": "candidate.md",
                                "download_url": (
                                    "https://uhp.example/v1/containers/"
                                    "cntr_1/files/file_1/content"
                                ),
                                "start_index": 0,
                                "end_index": 18,
                            }
                        ],
                    }
                ],
            },
        ],
        "store": True,
        "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        "metadata": metadata,
    }


def test_discovery_projection_pins_protocol_without_credentials() -> None:
    request = build_uhp_discovery_request()

    assert request.method == "GET"
    assert request.path == "/v1/uhp"
    assert request.requires_bearer_auth is False
    assert request.headers["UHP-Version"] == UHP_PROTOCOL_VERSION
    assert all(key.lower() != "authorization" for key in request.headers)
    assert request.request_digest == request.computed_digest
    assert request.actual_network_io is False


def test_discovery_fails_closed_on_protocol_version_mismatch() -> None:
    with pytest.raises(ValueError, match="protocol version mismatch"):
        record_uhp_discovery(
            payload=_discovery().model_dump(mode="json"),
            response_headers={"UHP-Version": "2026-01-01"},
        )


def test_extended_discovery_requires_extended_capabilities() -> None:
    with pytest.raises(ValidationError, match="contradicts capabilities"):
        UHPDiscoveryDocument(
            versions=(UHP_PROTOCOL_VERSION,),
            default_version=UHP_PROTOCOL_VERSION,
            conformance_class=UHPConformanceClass.EXTENDED,
            capabilities={"files_input": True, "files_output": False},
        )


def test_harness_base_is_opaque_and_tool_policy_is_not_authority() -> None:
    harness = _harness()

    assert harness.base == "future-harness-x"
    assert harness.disabled_tools == ("ExternalEffect",)
    assert harness.tool_enforcement_assurance == "UNVERIFIED_BY_UHP"


def test_worker_task_is_deterministically_bound_to_governed_workspace() -> None:
    binding, request = _build_task()

    assert binding.binding_digest == binding.computed_digest
    assert binding.workspace_digest == _workspace().workspace_digest
    assert binding.harness_base == "future-harness-x"
    assert binding.can_execute_external_effects is False
    assert binding.can_issue_clearance is False
    assert binding.requires_fresh_authority_evaluation is True
    assert request.path == "/v1/responses"
    assert request.headers["Idempotency-Key"] == binding.idempotency_key
    assert request.headers["UHP-Version"] == UHP_PROTOCOL_VERSION
    assert request.body is not None
    assert request.body["metadata"]["valo_request_id"] == binding.request_id
    assert request.body["metadata"]["valo_workspace_digest"] == binding.workspace_digest
    assert "Do not perform consequence-bearing external actions" in request.body["instructions"]
    assert all(key.lower() != "authorization" for key in request.headers)


def test_same_work_produces_same_idempotency_binding() -> None:
    first_binding, first_request = _build_task()
    second_binding, second_request = _build_task()

    assert first_binding.request_id == second_binding.request_id
    assert first_binding.idempotency_key == second_binding.idempotency_key
    assert first_request.request_digest == second_request.request_digest


def test_changed_work_changes_idempotency_binding() -> None:
    first_binding, _ = _build_task(input_text="Candidate A")
    second_binding, _ = _build_task(input_text="Candidate B")

    assert first_binding.request_id != second_binding.request_id
    assert first_binding.idempotency_key != second_binding.idempotency_key


def test_governed_task_requires_uhp_idempotency_capability() -> None:
    with pytest.raises(ValueError, match="advertise idempotency"):
        _build_task(discovery=_discovery(idempotency=False))


def test_continuation_requires_uhp_sessions_capability() -> None:
    with pytest.raises(ValueError, match="advertise sessions"):
        _build_task(
            previous_response_id="resp_previous",
            discovery=_discovery(sessions=False),
        )


def test_stale_workspace_fails_closed_before_worker_projection() -> None:
    with pytest.raises(ValueError, match="not fresh"):
        build_uhp_worker_task(
            workspace=_workspace(),
            discovery=_discovery(),
            harness=_harness(),
            worker_id="worker-uhp-1",
            input_text="Do work",
            effect_isolation_ref="effect-boundary-assurance-1",
            effect_isolation_digest="c" * 64,
            constructed_at=NOW + timedelta(minutes=11),
        )


def test_tampered_worker_binding_is_rejected() -> None:
    binding, _ = _build_task()
    data = binding.model_dump(mode="python")
    data["worker_id"] = "worker-tampered"

    with pytest.raises(ValidationError, match="binding digest mismatch"):
        UHPWorkerTaskBinding.model_validate(data)


def test_completed_worker_result_is_candidate_evidence_not_clearance() -> None:
    binding, _ = _build_task()
    evidence = record_uhp_worker_result(
        binding=binding,
        response_payload=_response(),
        response_headers={"UHP-Version": UHP_PROTOCOL_VERSION},
        observed_at=NOW + timedelta(minutes=2),
    )

    assert evidence.status.value == "completed"
    assert evidence.worker_output_role == "CANDIDATE_ONLY"
    assert evidence.completed_is_clearance is False
    assert evidence.can_issue_clearance is False
    assert evidence.can_execute_external_effects is False
    assert evidence.requires_fresh_authority_evaluation is True
    assert evidence.tool_enforcement_assurance == "UNVERIFIED_BY_UHP"
    assert evidence.observed_tool_calls == ("read_file",)
    assert evidence.evidence_digest == evidence.computed_digest


def test_uhp_artifacts_are_hostile_until_governed_admission() -> None:
    binding, _ = _build_task()
    evidence = record_uhp_worker_result(
        binding=binding,
        response_payload=_response(),
        response_headers={"UHP-Version": UHP_PROTOCOL_VERSION},
        observed_at=NOW + timedelta(minutes=2),
    )

    assert evidence.artifact_trust == "ATTACKER_INFLUENCED"
    assert len(evidence.artifact_refs) == 1
    artifact = evidence.artifact_refs[0]
    assert artifact.trust == "ATTACKER_INFLUENCED"
    assert artifact.authoritative_state is False
    assert artifact.can_issue_clearance is False

    listing = build_uhp_artifact_list_request(evidence=evidence)
    content = build_uhp_artifact_content_request(artifact=artifact)
    assert listing.path == "/v1/sessions/sess_1/files"
    assert content.path == "/v1/containers/cntr_1/files/file_1/content"


def test_artifact_path_traversal_is_rejected() -> None:
    with pytest.raises(ValidationError, match="path traversal"):
        UHPArtifactReference(
            container_id="cntr_../secret",
            file_id="file_1",
            filename="candidate.md",
            download_url="https://uhp.example/secret",
        )


def test_explicit_model_substitution_requires_downstream_readmission() -> None:
    binding, _ = _build_task(requested_model="model-a")
    evidence = record_uhp_worker_result(
        binding=binding,
        response_payload=_response(actual_model="model-b", fallback=True),
        response_headers={"UHP-Version": UHP_PROTOCOL_VERSION},
        observed_at=NOW + timedelta(minutes=2),
    )

    assert evidence.model_fallback is True
    assert evidence.actual_model == "model-b"
    assert evidence.requested_model == "model-a"
    assert evidence.requires_model_readmission is True


def test_silent_model_substitution_fails_closed() -> None:
    binding, _ = _build_task(requested_model="model-a")

    with pytest.raises(ValueError, match="not explicitly reported"):
        record_uhp_worker_result(
            binding=binding,
            response_payload=_response(actual_model="model-b", fallback=False),
            response_headers={"UHP-Version": UHP_PROTOCOL_VERSION},
            observed_at=NOW + timedelta(minutes=2),
        )


def test_response_harness_mismatch_fails_closed() -> None:
    binding, _ = _build_task()
    response = _response()
    response["metadata"]["harness_id"] = "chrn_other"

    with pytest.raises(ValueError, match="harness binding mismatch"):
        record_uhp_worker_result(
            binding=binding,
            response_payload=response,
            response_headers={"UHP-Version": UHP_PROTOCOL_VERSION},
            observed_at=NOW + timedelta(minutes=2),
        )


def test_cancel_projection_cannot_escape_uhp_response_namespace() -> None:
    binding, _ = _build_task()
    cancel = build_uhp_cancel_request(binding=binding, response_id="resp_123")

    assert cancel.path == "/v1/responses/resp_123/cancel"
    assert cancel.can_execute_external_effects is False

    with pytest.raises(ValueError, match="unsafe path syntax"):
        build_uhp_cancel_request(binding=binding, response_id="resp_../escape")
