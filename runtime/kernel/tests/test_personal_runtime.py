from __future__ import annotations

import base64
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from valo_kernel import (
    Authority,
    EntityType,
    IdentityClaim,
    TimeWindow,
    VerificationStatus,
    utcnow,
)
from valo_kernel.contracts import CanonicalEvent, EventType
from valo_kernel.contracts.semantic_disclosure import ExecutionBoundaryKey
from valo_kernel.kernel.errors import FailClosedError
from valo_kernel.kernel.personal_runtime import (
    open_execution_handoff_at_reht,
    prepare_execution_handoff,
    prepare_worker_invocation,
)

from .conftest import entity_event
from .test_compute_routing import _candidate as _route_candidate
from .test_compute_routing import _model, _node, _portability, _request
from .test_workspace import _candidate, _register_purpose, _workspace


def _execution_boundary(now):
    private_key = X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return (
        ExecutionBoundaryKey(
            key_ref="boundary-key:reht-v0",
            boundary_id="reht-boundary-v0",
            public_key_b64=base64.b64encode(public_bytes).decode("ascii"),
            valid_from=now - timedelta(seconds=1),
            valid_until=now + timedelta(minutes=10),
        ),
        private_bytes,
    )


def _governed_engine(engine):
    now = utcnow()
    engine.append(
        entity_event(
            "tenant-a",
            "job-1",
            entity_type=EntityType.JOB,
            state="READY",
        )
    )
    engine.append(
        entity_event(
            "tenant-a",
            "agent-1",
            entity_type=EntityType.AGENT,
            state="ACTIVE",
        )
    )
    _register_purpose(engine)
    engine.append(
        CanonicalEvent(
            event_id="identity-agent-1",
            event_type=EventType.IDENTITY_CLAIMED,
            tenant_id="tenant-a",
            subject="agent-1",
            source="kernel",
            timestamp=now,
            effective_at=now,
            payload={
                "identity": IdentityClaim(
                    identity_id="id-agent-1",
                    entity_id="agent-1",
                    tenant_id="tenant-a",
                    claim_type="internal_id",
                    value="agent-1",
                    verification_status=VerificationStatus.VERIFIED,
                    issued_at=now,
                )
            },
        )
    )
    engine.append(
        CanonicalEvent(
            event_id="authority-agent-1-book",
            event_type=EventType.AUTHORITY_GRANTED,
            tenant_id="tenant-a",
            subject="agent-1",
            source="kernel",
            timestamp=now,
            effective_at=now,
            payload={
                "authority": Authority(
                    authority_id="authority-agent-1-book",
                    principal="agent-1",
                    capability="BOOK",
                    scope=["job-1"],
                    basis="principal-delegation",
                    validity=TimeWindow(
                        valid_from=now - timedelta(seconds=1),
                        valid_until=now + timedelta(hours=1),
                    ),
                )
            },
        )
    )
    return now


def test_worker_route_is_admitted_without_giving_router_authority(engine) -> None:
    now = _governed_engine(engine)
    workspace = _workspace(engine, moment=now)
    model = _model()
    portability = _portability(model)
    node = _node(model)
    request = _request(
        model,
        tenant_id=workspace.spec.tenant_id,
        purpose_id=workspace.spec.purpose_id,
        source_state_root=workspace.projection.source_state_root,
    )
    route = _route_candidate(request, node, portability)

    prepared = prepare_worker_invocation(
        workspace,
        request,
        route,
        node,
        portability,
        current_state_root=engine.state().root_hash(),
    )

    assert prepared.destination_id == "provider-a"
    assert prepared.route_assessment.outcome.value == "PASS"
    assert prepared.route_assessment.chooses_provider is False
    assert prepared.route_assessment.can_issue_clearance is False


def test_worker_route_fails_when_runtime_rebinds_purpose(engine) -> None:
    now = _governed_engine(engine)
    workspace = _workspace(engine, moment=now)
    model = _model()
    portability = _portability(model)
    node = _node(model)
    request = _request(
        model,
        tenant_id=workspace.spec.tenant_id,
        purpose_id="another-purpose",
        source_state_root=workspace.projection.source_state_root,
    )
    route = _route_candidate(request, node, portability)

    with pytest.raises(FailClosedError, match="purpose differs"):
        prepare_worker_invocation(
            workspace,
            request,
            route,
            node,
            portability,
            current_state_root=engine.state().root_hash(),
        )


def test_candidate_crosses_as_sealed_action_and_opens_only_at_reht(engine) -> None:
    now = _governed_engine(engine)
    workspace = _workspace(engine, moment=now)
    candidate = _candidate(workspace)
    boundary_key, boundary_private = _execution_boundary(now)

    handoff = prepare_execution_handoff(
        workspace,
        candidate,
        engine.state(),
        action_id="action-1",
        recipient_key=boundary_key,
        moment=now,
    )

    serialized = handoff.sealed_binding.model_dump_json()
    assert handoff.sealed_binding.plaintext_action_exposed is False
    assert '"capability":"BOOK"' not in serialized

    open_moment = now + timedelta(seconds=1)
    requested = CanonicalEvent(
        event_id="requested-book-job-1",
        event_type=EventType.ENTITY_UPDATED,
        tenant_id="tenant-a",
        subject="job-1",
        actor="agent-1",
        source="reht",
        timestamp=open_moment,
        effective_at=open_moment,
        payload={"entity_id": "job-1", "state": "BOOKED"},
    )
    reht = open_execution_handoff_at_reht(
        handoff,
        workspace,
        candidate,
        engine.state(),
        actor="agent-1",
        requested_transition=requested,
        boundary_private_key=boundary_private,
        identity_id="id-agent-1",
        event_position=engine.sequence(),
        reht_evaluation_id="reht-eval-v0",
        moment=open_moment,
    )

    assert reht.disclosed_action.action.capability == "BOOK"
    assert reht.disclosed_action.execution_effect == "NONE"
    assert reht.execution_context["authority"]
    assert reht.execution_context["state_root"] == engine.state().root_hash()
    assert reht.disclosure_context.can_issue_clearance is False
