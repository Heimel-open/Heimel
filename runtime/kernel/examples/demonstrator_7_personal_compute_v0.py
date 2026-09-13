"""Demonstrator 7: sovereign personal compute V0.

A persistent Kernel domain produces a minimal governed projection, admits an
external compute route only after disclosure authorization, receives a worker
candidate, seals the exact consequence action for REHT, performs JIT semantic
disclosure at the REHT boundary, and lets an external demo Gateway append the
approved effect. A signed receipt is then appended to the evidence history.

The demo REHT predicate and Gateway are deliberately outside Kernel. Kernel has
no execute path.
"""

from __future__ import annotations

import base64
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from valo_kernel import (
    Authority,
    CandidateKind,
    IdentityClaim,
    KernelEngine,
    ProjectionSelector,
    ProposedAction,
    Purpose,
    TimeWindow,
    VerificationStatus,
    WorkspaceCapabilitySpec,
    WorkspaceSpec,
    canonical_digest,
    compile_governed_workspace,
    create_candidate_result,
    utcnow,
)
from valo_kernel.contracts import CanonicalEvent, EntityType, EventType
from valo_kernel.contracts.semantic_disclosure import ExecutionBoundaryKey
from valo_kernel.credentials import EncryptedFileCredentialStore
from valo_kernel.kernel.compute_routing import (
    seal_compute_node_profile,
    seal_compute_route_candidate,
    seal_compute_route_request,
)
from valo_kernel.kernel.model_portability import (
    assess_model_portability,
    seal_hardware_capability_profile,
    seal_portable_model_artifact,
    seal_semantic_equivalence_evidence,
)
from valo_kernel.kernel.personal_runtime import (
    open_execution_handoff_at_reht,
    prepare_execution_handoff,
    prepare_worker_invocation,
)
from valo_kernel.kernel.sovereignty import (
    assess_disclosure,
    seal_disclosure_authorization,
)
from valo_kernel.storage import SQLiteStore


def _entity(tenant: str, entity_id: str, entity_type: EntityType, state: str):
    return CanonicalEvent(
        event_id=f"entity-{entity_id}",
        event_type=EventType.ENTITY_REGISTERED,
        tenant_id=tenant,
        subject=entity_id,
        source="bootstrap",
        payload={
            "entity": {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "tenant_id": tenant,
                "state": state,
                "provenance": {
                    "source_type": "system",
                    "source_id": "personal-compute-v0",
                    "source_system": "valo-kernel",
                },
            }
        },
    )


def _boundary_key(now):
    private_key = X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    descriptor = ExecutionBoundaryKey(
        key_ref="reht:v0:key-1",
        boundary_id="reht:v0",
        public_key_b64=base64.b64encode(public_bytes).decode("ascii"),
        valid_from=now - timedelta(seconds=1),
        valid_until=now + timedelta(minutes=10),
    )
    return descriptor, private_bytes


def _demo_reht_authorizes(boundary_handoff) -> bool:
    """Demo-only deterministic predicate, not the production REHT implementation."""
    action = boundary_handoff.disclosed_action.action
    context = boundary_handoff.execution_context
    purpose = context["purpose"]
    if purpose is None or action.capability not in purpose["permitted_actions"]:
        return False
    for authority in context["authority"]:
        if authority["capability"] != action.capability:
            continue
        scope = authority["scope"]
        if not scope or "*" in scope or action.target in scope:
            return True
    return False


def run(root: Path | None = None) -> dict[str, str]:
    temporary = TemporaryDirectory() if root is None else None
    base = Path(temporary.name) if temporary is not None else root
    assert base is not None
    tenant = "personal-v0"
    database = base / "domain.db"
    credential_directory = base / "credentials"
    receipt_passphrase = b"demo-only-receipt-passphrase"
    now = utcnow()

    store = SQLiteStore(database)
    engine = KernelEngine(tenant, storage=store)
    credentials = EncryptedFileCredentialStore(credential_directory)
    credentials.create_credential("receipt-signer-1", receipt_passphrase)

    engine.append(_entity(tenant, "principal-1", EntityType.PERSON, "ACTIVE"))
    engine.append(_entity(tenant, "agent-1", EntityType.AGENT, "ACTIVE"))
    engine.append(_entity(tenant, "job-1", EntityType.JOB, "READY"))

    engine.append(
        CanonicalEvent(
            event_id="identity-agent-1",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id=tenant,
            subject="agent-1",
            source="principal",
            timestamp=now,
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id="id-agent-1",
                    entity_id="agent-1",
                    tenant_id=tenant,
                    claim_type="principal-agent",
                    value="agent-1",
                    verification_status=VerificationStatus.VERIFIED,
                    issued_at=now,
                )
            },
        )
    )

    purpose = Purpose(
        purpose_id="personal.booking",
        purpose_type="booking",
        scope=["job-1"],
        basis="principal-request",
        permitted_data=["entities:job-1"],
        permitted_actions=["BOOK"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(hours=1),
        ),
    )
    engine.append(
        CanonicalEvent(
            event_id="purpose-personal-booking",
            event_type=EventType.PURPOSE_REGISTERED,
            tenant_id=tenant,
            subject=purpose.purpose_id,
            source="principal",
            timestamp=now,
            effective_at=now,
            payload={"purpose": purpose},
        )
    )
    engine.append(
        CanonicalEvent(
            event_id="authority-agent-book",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id=tenant,
            subject="agent-1",
            source="principal",
            timestamp=now,
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="authority-agent-book",
                    principal="agent-1",
                    capability="BOOK",
                    scope=["job-1"],
                    basis="principal-delegation",
                    validity=TimeWindow(
                        valid_from=now - timedelta(minutes=1),
                        valid_until=now + timedelta(hours=1),
                    ),
                )
            },
        )
    )

    workspace = compile_governed_workspace(
        engine.state(),
        WorkspaceSpec(
            workspace_id="workspace-book-job-1",
            work_unit_id="work-book-job-1",
            tenant_id=tenant,
            purpose_id=purpose.purpose_id,
            selectors=(
                ProjectionSelector(collection="entities", object_ids=("job-1",)),
            ),
            capabilities=(
                WorkspaceCapabilitySpec(
                    capability="BOOK",
                    target_refs=("job-1",),
                    allowed_effects=("book",),
                ),
            ),
            allowed_output_kinds=(CandidateKind.EXTERNAL_ACTION,),
            expires_at=now + timedelta(minutes=15),
        ),
        source_event_position=engine.sequence(),
        moment=now,
    )

    projection_digest = canonical_digest(workspace.projection.model_dump(mode="json"))
    authority_state_digest = canonical_digest(
        [item.model_dump(mode="json") for item in engine.state().authorities.values()]
    )
    disclosure_authorization = seal_disclosure_authorization(
        authorization_id="disclose-cloud-a",
        tenant_id=tenant,
        principal_id="principal-1",
        destination_id="cloud-a",
        purpose_id=purpose.purpose_id,
        projection_id=workspace.projection.projection_id,
        projection_digest=projection_digest,
        source_state_root=workspace.projection.source_state_root,
        source_event_position=workspace.projection.source_event_position,
        allowed_object_refs=tuple(sorted(item.ref for item in workspace.projection.objects)),
        authority_basis_refs=("authority:principal-disclosure",),
        authority_state_digest=authority_state_digest,
        issued_at=now - timedelta(seconds=1),
        valid_until=now + timedelta(minutes=5),
    )
    disclosure = assess_disclosure(
        workspace,
        disclosure_authorization,
        destination_id="cloud-a",
        current_state_root=engine.state().root_hash(),
        current_authority_state_digest=authority_state_digest,
        moment=now,
    )
    assert disclosure.outcome.value == "PASS"

    model = seal_portable_model_artifact(
        model_id="worker-model-v0",
        format_id="portable-ir.v1",
        graph_digest="a" * 64,
        weights_digest="b" * 64,
        metadata_digest="c" * 64,
        semantic_contract_digest="d" * 64,
        required_operators=("attention", "matmul"),
        allowed_precisions=("FP16",),
        minimum_memory_bytes=1_000_000,
        reference_backend_id="cpu-reference",
    )
    hardware = seal_hardware_capability_profile(
        backend_id="cloud-backend-a",
        hardware_class="GPU",
        supported_formats=("portable-ir.v1",),
        supported_operators=("attention", "matmul"),
        supported_precisions=("FP16",),
        available_memory_bytes=8_000_000,
        trust_root_ids=("cloud-root-a",),
    )
    equivalence = seal_semantic_equivalence_evidence(
        evidence_id="eq-worker-model-v0",
        portable_model_digest=model.artifact_digest,
        reference_backend_id=model.reference_backend_id,
        candidate_backend_id=hardware.backend_id,
        test_suite_digest="e" * 64,
        tolerance_profile_digest="f" * 64,
        passed=True,
    )
    portability = assess_model_portability(
        model,
        hardware,
        equivalence_evidence=equivalence,
    )
    node = seal_compute_node_profile(
        node_id="cloud-node-a",
        provider_id="cloud-a",
        backend_id=hardware.backend_id,
        trust_domain="external",
        locality="cloud",
        capability_classes=("reasoning",),
        supported_model_digests=(model.artifact_digest,),
        latency_budget_ms=100,
        cost_ceiling_minor_units=10,
        allows_raw_personal_data=True,
    )
    route_request = seal_compute_route_request(
        request_id="route-book-job-1",
        tenant_id=tenant,
        principal_id="principal-1",
        purpose_id=purpose.purpose_id,
        workload_digest="1" * 64,
        portable_model_digest=model.artifact_digest,
        required_capabilities=("reasoning",),
        allowed_provider_ids=("cloud-a",),
        allowed_trust_domains=("external",),
        max_latency_ms=100,
        max_cost_minor_units=10,
        raw_personal_data_required=True,
        disclosure_authorization_digest=disclosure_authorization.authorization_digest,
        source_state_root=workspace.projection.source_state_root,
    )
    route_candidate = seal_compute_route_candidate(
        candidate_id="route-cloud-a",
        request_digest=route_request.request_digest,
        node_profile_digest=node.profile_digest,
        node_id=node.node_id,
        provider_id=node.provider_id,
        backend_id=node.backend_id,
        predicted_latency_ms=25,
        predicted_cost_minor_units=2,
        model_portability_assessment_digest=portability.assessment_digest,
    )
    dispatch = prepare_worker_invocation(
        workspace,
        route_request,
        route_candidate,
        node,
        portability,
        current_state_root=engine.state().root_hash(),
        disclosure=disclosure,
    )
    assert dispatch.destination_id == "cloud-a"

    action = ProposedAction(
        action_id="book-job-1",
        capability="BOOK",
        target="job-1",
        purpose_id=purpose.purpose_id,
        declared_effects=("book",),
    )
    worker_candidate = create_candidate_result(
        candidate_id="worker-candidate-1",
        invocation_id="worker-invocation-1",
        worker_id="cloud-a:worker-model-v0",
        workspace_id=workspace.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        output_kind=CandidateKind.EXTERNAL_ACTION,
        proposed_actions=(action,),
    )

    boundary_key, boundary_private = _boundary_key(now)
    execution_handoff = prepare_execution_handoff(
        workspace,
        worker_candidate,
        engine.state(),
        action_id=action.action_id,
        recipient_key=boundary_key,
        moment=now,
    )
    assert "job-1" not in execution_handoff.sealed_binding.sealed_action.ciphertext_b64

    effect_time = now + timedelta(seconds=1)
    requested_transition = CanonicalEvent(
        event_id="effect-book-job-1",
        event_type=EventType.ENTITY_UPDATED,
        tenant_id=tenant,
        subject="job-1",
        actor="agent-1",
        source="gateway",
        timestamp=effect_time,
        effective_at=effect_time,
        idempotency_key="effect-book-job-1",
        payload={"entity_id": "job-1", "state": "BOOKED"},
    )
    reht_handoff = open_execution_handoff_at_reht(
        execution_handoff,
        workspace,
        worker_candidate,
        engine.state(),
        actor="agent-1",
        requested_transition=requested_transition,
        boundary_private_key=boundary_private,
        identity_id="id-agent-1",
        event_position=engine.sequence(),
        reht_evaluation_id="reht-v0-eval-1",
        moment=effect_time,
    )
    assert _demo_reht_authorizes(reht_handoff) is True

    pre_effect_root = engine.state().root_hash()
    gateway_event = engine.append(requested_transition, expected_version=engine.sequence())
    post_effect_root = engine.state().root_hash()

    receipt_payload = {
        "receipt_id": "receipt-book-job-1",
        "action_digest": canonical_digest(
            reht_handoff.disclosed_action.action.model_dump(mode="json")
        ),
        "reht_evaluation_id": "reht-v0-eval-1",
        "effect_event_hash": gateway_event.event_hash,
        "pre_effect_state_root": pre_effect_root,
        "post_effect_state_root": post_effect_root,
    }
    receipt_digest = canonical_digest(receipt_payload)
    receipt_signature = credentials.sign(
        "receipt-signer-1",
        receipt_digest.encode("ascii"),
        receipt_passphrase,
    )
    assert credentials.verify(
        "receipt-signer-1",
        receipt_digest.encode("ascii"),
        receipt_signature,
    )
    engine.append(
        CanonicalEvent(
            event_id="receipt-observed-book-job-1",
            event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
            tenant_id=tenant,
            subject="job-1",
            actor="agent-1",
            source="veritas-demo",
            timestamp=effect_time,
            effective_at=effect_time,
            payload={
                "receipt": receipt_payload,
                "receipt_digest": receipt_digest,
                "receipt_signature_hex": receipt_signature.hex(),
            },
            evidence_refs=[],
            causation_id=requested_transition.event_id,
        )
    )

    final_root = engine.state().root_hash()
    assert engine.state().entities["job-1"].state == "BOOKED"
    engine.verify_integrity()
    store.close()

    restarted_store = SQLiteStore(database)
    restarted = KernelEngine(tenant, storage=restarted_store)
    restarted.verify_integrity()
    assert restarted.state().root_hash() == final_root
    assert restarted.state().entities["job-1"].state == "BOOKED"
    result = {
        "disclosure": disclosure.outcome.value,
        "route": dispatch.route_assessment.outcome.value,
        "conformance": execution_handoff.conformance_report.outcome.value,
        "effect": restarted.state().entities["job-1"].state,
        "receipt": receipt_digest,
        "state_root": final_root,
    }
    restarted_store.close()
    if temporary is not None:
        temporary.cleanup()
    return result


def test_demonstrator_7_personal_compute_v0() -> None:
    result = run()
    assert result["disclosure"] == "PASS"
    assert result["route"] == "PASS"
    assert result["conformance"] == "PASS"
    assert result["effect"] == "BOOKED"


if __name__ == "__main__":
    print(run())
