from __future__ import annotations

from valo_operator import (
    Gateway,
    OperatorRequest,
    OperatorSession,
    ServiceHandler,
    build_public_runtime,
    build_trades_runtime,
)


def _register_request():
    return OperatorRequest(
        correlation_id="corr-surf", function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
    )


def test_library_surface_submit() -> None:
    runtime = build_public_runtime()
    result = runtime.submit(_register_request())
    assert result.decision == "ALLOW"
    assert result.status == "COMPLETED"
    assert runtime.kernel.state().entities["case-1"].state == "REGISTERED"
    assert runtime.pack_id == "public"


def test_library_surface_discover_and_snapshot() -> None:
    runtime = build_public_runtime()
    discovered = runtime.discover()
    assert any(d["function_id"] == "valo.public.issue_public_decision" for d in discovered)
    assert "ISSUE_DECISION" in runtime.capabilities()
    snap = runtime.snapshot()
    assert snap["summary"]["pack"] == "public"


def test_library_surface_session() -> None:
    runtime = build_public_runtime()
    session = OperatorSession(tenant_id="public", actor="system-1", identity_id="id-system-1")
    result = runtime.submit(_register_request(), session=session)
    assert result.decision == "ALLOW"
    assert result.actor == "system-1"


def test_trades_runtime_builds() -> None:
    runtime = build_trades_runtime()
    assert runtime.pack_id == "trades"
    snap = runtime.snapshot()
    assert snap["summary"]["pack"] == "trades"
    assert snap["summary"]["open_workorders"] == ["workorder-1"]


def test_service_surface_submit() -> None:
    runtime = build_public_runtime()
    handler = ServiceHandler(runtime)
    response = handler.handle(
        "submit",
        {"request": _register_request().model_dump(mode="json")},
    )
    assert response["result"]["decision"] == "ALLOW"


def test_service_surface_rejects_session_violation() -> None:
    runtime = build_public_runtime()
    handler = ServiceHandler(runtime)
    response = handler.handle(
        "submit",
        {
            "request": _register_request().model_dump(mode="json"),
            "session": {"tenant_id": "OTHER", "actor": "system-1", "identity_id": "id-system-1"},
        },
    )
    assert response["result"]["status"] == "REJECTED"
    assert "tenant mismatch" in (response["result"]["reason"] or "")


def test_gateway_http_routes() -> None:
    runtime = build_public_runtime()
    gateway = Gateway(runtime)
    status, body = gateway.route("POST", "/submit", {"request": _register_request().model_dump(mode="json")})
    assert status == 200
    assert body["result"]["decision"] == "ALLOW"

    status, body = gateway.route("GET", "/discover")
    assert status == 200
    assert any(f["function_id"] == "valo.public.register_case" for f in body["functions"])

    status, body = gateway.route("GET", "/views")
    assert status == 200
    assert "entities" in body["views"]

    status, _ = gateway.route("GET", "/nope")
    assert status == 404


def test_same_decision_across_surfaces() -> None:
    """The authorization chain is identical regardless of entry point: the same
    request yields the same decision through library, service and gateway."""
    r_lib = build_public_runtime()
    lib = r_lib.submit(_register_request())

    r_ser = build_public_runtime()
    ser = ServiceHandler(r_ser).handle("submit", {"request": _register_request().model_dump(mode="json")})
    assert lib.decision == ser["result"]["decision"] == "ALLOW"

    r_http = build_public_runtime()
    status, body = Gateway(r_http).route("POST", "/submit", {"request": _register_request().model_dump(mode="json")})
    assert status == 200
    assert lib.decision == body["result"]["decision"] == "ALLOW"
