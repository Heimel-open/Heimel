from __future__ import annotations

from valo_operator import (
    OperatorRequest,
    OperatorSession,
    submit,
    validate_session,
)


def _public_parts(legal_basis_active=True):
    from valo_public_pack import build_public_registry, seed_world
    from valo_public_pack.ports import PublicBaro, PublicGateway, PublicKernel, PublicVeritas

    kernel = seed_world(legal_basis_active=legal_basis_active)
    return (
        build_public_registry(),
        PublicKernel(kernel),
        kernel,
        PublicGateway(),
        PublicVeritas(),
        PublicBaro(),
    )


def _register_request():
    return OperatorRequest(
        correlation_id="corr-s", function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
    )


def test_valid_session_register() -> None:
    from valo_reht import RealReht

    registry, adapter, kernel, gateway, veritas, baro = _public_parts()
    session = OperatorSession(tenant_id="public", actor="system-1", identity_id="id-system-1")
    result = submit(registry, adapter, RealReht(), gateway, veritas, baro, _register_request(), session=session)
    assert result.status == "COMPLETED"
    assert result.decision == "ALLOW"
    assert result.actor == "system-1"
    assert result.tenant_id == "public"
    assert kernel.state().entities["case-1"].state == "REGISTERED"


def test_session_tenant_mismatch_rejected() -> None:
    from valo_reht import RealReht

    registry, adapter, _, gateway, veritas, baro = _public_parts()
    session = OperatorSession(tenant_id="OTHER", actor="system-1", identity_id="id-system-1")
    result = submit(registry, adapter, RealReht(), gateway, veritas, baro, _register_request(), session=session)
    assert result.status == "REJECTED"
    assert "tenant mismatch" in (result.reason or "")
    assert result.gateway_executions == 0


def test_session_unknown_actor_rejected() -> None:
    from valo_reht import RealReht

    registry, adapter, _, gateway, veritas, baro = _public_parts()
    session = OperatorSession(tenant_id="public", actor="ghost", identity_id="id-system-1")
    result = submit(registry, adapter, RealReht(), gateway, veritas, baro, _register_request(), session=session)
    assert result.status == "REJECTED"
    assert "unknown actor" in (result.reason or "")


def test_session_actor_must_match_function() -> None:
    from valo_kernel.contracts import (
        CanonicalEvent,
        Entity,
        EntityType,
        EventType,
        IdentityClaim,
        Provenance,
        VerificationStatus,
        utcnow,
    )
    from valo_reht import RealReht

    registry, adapter, kernel, gateway, veritas, baro = _public_parts()
    now = utcnow()
    prov = Provenance(source_type="system", source_id="s", source_system="operator-test")
    kernel.append(CanonicalEvent(
        event_id="seed-worker", event_type=EventType.ENTITY_REGISTERED,
        tenant_id="public", subject="worker-a", source="kernel", effective_at=now,
        payload={"entity": Entity(
            entity_id="worker-a", entity_type=EntityType.PERSON, tenant_id="public", provenance=prov
        )},
    ))
    kernel.append(CanonicalEvent(
        event_id="seed-worker-id", event_type=EventType.IDENTITY_CLAIMED,
        tenant_id="public", subject="worker-a", source="kernel", effective_at=now,
        payload={"identity": IdentityClaim(
            identity_id="id-worker-a", entity_id="worker-a", tenant_id="public",
            claim_type="person", value="id-worker-a",
            verification_status=VerificationStatus.VERIFIED,
        )},
    ))
    # the registered register_case Function is bound to system-1; a valid
    # session for worker-a must be rejected at the actor-match gate
    session = OperatorSession(tenant_id="public", actor="worker-a", identity_id="id-worker-a")
    result = submit(registry, adapter, RealReht(), gateway, veritas, baro, _register_request(), session=session)
    assert result.status == "REJECTED"
    assert "does not match the registered Function actor" in (result.reason or "")


def test_rights_impacting_requires_step_up() -> None:
    from valo_reht import RealReht

    registry, adapter, _, gateway, veritas, baro = _public_parts()
    request = OperatorRequest(
        correlation_id="corr-step", function_id="valo.public.issue_public_decision",
        inputs={"context": {"case": "case-1"}},
    )
    session = OperatorSession(tenant_id="public", actor="system-1", identity_id="id-system-1", step_up=False)
    result = submit(registry, adapter, RealReht(), gateway, veritas, baro, request, session=session)
    assert result.status == "REJECTED"
    assert "step_up" in (result.reason or "")

    session_ok = OperatorSession(tenant_id="public", actor="system-1", identity_id="id-system-1", step_up=True)
    from valo_operator import act
    act(registry, adapter, RealReht(), gateway, veritas, baro, function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}})
    act(registry, adapter, RealReht(), gateway, veritas, baro, function_id="valo.public.mark_ready_for_review",
        inputs={"case": {"id": "case-1"}})
    act(registry, adapter, RealReht(), gateway, veritas, baro, function_id="valo.public.mark_under_review",
        inputs={"case": {"id": "case-1"}})
    act(registry, adapter, RealReht(), gateway, veritas, baro, function_id="valo.public.mark_ready_for_decision",
        inputs={"case": {"id": "case-1"}})
    result_ok = submit(registry, adapter, RealReht(), gateway, veritas, baro, request, session=session_ok)
    assert result_ok.status == "COMPLETED"
    assert result_ok.decision == "ALLOW"


def test_validate_session_purpose_and_delegation() -> None:
    registry, adapter, kernel, _, _, _ = _public_parts()
    ok = validate_session(kernel, OperatorSession(tenant_id="public", actor="system-1", identity_id="id-system-1"))
    assert ok == []

    unknown_purpose = OperatorSession(
        tenant_id="public", actor="system-1", identity_id="id-system-1", purpose_id="nope"
    )
    assert any(
        "unknown purpose" in v for v in validate_session(kernel, unknown_purpose)
    )

    unknown_delegation = OperatorSession(
        tenant_id="public", actor="system-1", identity_id="id-system-1", delegation_ref="nope"
    )
    assert any(
        "unknown delegation" in v for v in validate_session(kernel, unknown_delegation)
    )
