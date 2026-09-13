from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_operator import (
    OperatorRequest,
    OperatorResult,
    capabilities,
    discover_functions,
    find_functions_by_capability,
    submit,
)


def _public_parts(legal_basis_active=True):
    from valo_public_pack import build_public_registry, seed_world
    from valo_public_pack.ports import PublicBaro, PublicGateway, PublicKernel, PublicVeritas

    kernel = seed_world(legal_basis_active=legal_basis_active)
    return (
        build_public_registry(),
        PublicKernel(kernel),
        None,  # reht injected per submit below
        PublicGateway(),
        PublicVeritas(),
        PublicBaro(),
        kernel,
    )


def _with_reht(parts, reht):
    return (parts[0], parts[1], reht, parts[3], parts[4], parts[5], parts[6])


def test_request_contract_frozen_and_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        OperatorRequest(correlation_id="c1", function_id="x", unexpected_field=True)
    with pytest.raises(ValidationError):
        OperatorRequest(correlation_id="", function_id="x")
    req = OperatorRequest(
        correlation_id="c1", function_id="valo.public.register_case",
        inputs={"application": {"id": "a1"}},
    )
    assert req.api_version == "1.0"


def test_submit_rejects_unsupported_api_version() -> None:
    from valo_reht import RealReht

    parts = _public_parts()
    registry, adapter, _, gateway, veritas, baro, _ = parts
    request = OperatorRequest(
        api_version="9.9", correlation_id="c1", function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1"}},
    )
    with pytest.raises(ValueError):
        submit(registry, adapter, RealReht(), gateway, veritas, baro, request)


def test_submit_allowed_with_correlation() -> None:
    from valo_reht import RealReht

    parts = _with_reht(_public_parts(), RealReht())
    registry, adapter, reht, gateway, veritas, baro, kernel = parts
    request = OperatorRequest(
        correlation_id="corr-1", function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
    )
    result = submit(registry, adapter, reht, gateway, veritas, baro, request)
    assert isinstance(result, OperatorResult)
    assert result.correlation_id == "corr-1"
    assert result.decision == "ALLOW"
    assert result.status == "COMPLETED"
    assert result.effect_verified is True
    assert kernel.state().entities["case-1"].state == "REGISTERED"


def test_submit_denied_without_authority() -> None:
    from valo_kernel.contracts import CanonicalEvent, EventType, utcnow
    from valo_reht import RealReht

    parts = _public_parts()
    registry, adapter, _, gateway, veritas, baro, kernel = parts
    kernel.append(CanonicalEvent(
        event_id="revoke-admin", event_type=EventType.AUTHORITY_REVOKED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=utcnow(),
        payload={"authority_id": "auth-system-ADMIN", "revocation_ref": "rev-admin"},
    ))
    request = OperatorRequest(
        correlation_id="corr-2", function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1"}},
    )
    result = submit(registry, adapter, RealReht(), gateway, veritas, baro, request)
    assert result.decision == "DENY"
    assert result.gateway_executions == 0
    assert result.effect_verified is False


def test_submit_rejects_unknown_function() -> None:
    from valo_function_fabric.registry.store import RegistryError
    from valo_reht import RealReht

    parts = _public_parts()
    registry, adapter, _, gateway, veritas, baro, _ = parts
    request = OperatorRequest(correlation_id="corr-3", function_id="valo.nope.unknown", inputs={})
    with pytest.raises(RegistryError):
        submit(registry, adapter, RealReht(), gateway, veritas, baro, request)


def test_discover_functions_lists_registered() -> None:
    registry, *_ = _public_parts()
    discovered = discover_functions(registry)
    ids = {d["function_id"] for d in discovered}
    assert "valo.public.register_case" in ids
    assert "valo.public.issue_public_decision" in ids
    assert "valo.identity.verify_identity" in ids
    issue = next(d for d in discovered if d["function_id"] == "valo.public.issue_public_decision")
    assert issue["risk_class"] == "R4_RIGHTS_IMPACTING"
    assert "ISSUE_DECISION" in issue["capabilities"]
    assert issue["output_type"]["type"] == "VerifiedEffect<PublicDecision>"


def test_capabilities_discovery() -> None:
    registry, *_ = _public_parts()
    caps = capabilities(registry)
    assert "ISSUE_DECISION" in caps
    assert "ADMIN" in caps
    assert find_functions_by_capability(registry, "ISSUE_DECISION") == ["valo.public.issue_public_decision"]


def test_discovery_is_read_only() -> None:
    registry, _, _, _, _, _, kernel = _public_parts()
    before = kernel.sequence()
    discover_functions(registry)
    capabilities(registry)
    assert kernel.sequence() == before
