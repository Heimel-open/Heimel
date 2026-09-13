"""Deployment surfaces over one shared OperatorRuntime.

The SAME runtime (and therefore the SAME authorization chain) is exposed as a
library, a transport-agnostic service handler (sidecar), and an HTTP gateway.
Switching surface never changes the boundary.
"""

from __future__ import annotations

from typing import Any

from .api import API_VERSION, OperatorRequest
from .runtime import OperatorRuntime
from .session import OperatorSession


def build_public_runtime(reht: Any | None = None, kernel: Any | None = None, **ports: Any) -> OperatorRuntime:
    """Library surface: build a Public Operator runtime."""
    from valo_public_pack import build_public_registry, seed_world
    from valo_public_pack.ports import PublicBaro, PublicGateway, PublicKernel, PublicVeritas
    from valo_reht import RealReht

    kernel = kernel or seed_world()
    return OperatorRuntime(
        pack_id="public",
        registry=build_public_registry(),
        kernel_adapter=PublicKernel(kernel),
        reht=reht or RealReht(),
        gateway=ports.get("gateway") or PublicGateway(),
        veritas=ports.get("veritas") or PublicVeritas(),
        baro=ports.get("baro") or PublicBaro(),
    )


def build_trades_runtime(reht: Any | None = None, kernel: Any | None = None, **ports: Any) -> OperatorRuntime:
    """Library surface: build a Trades Operator runtime."""
    from valo_reht import RealReht
    from valo_trades_pack import build_trades_registry, seed_world
    from valo_trades_pack.ports import TradeBaro, TradeGateway, TradeKernel, TradeVeritas

    kernel = kernel or seed_world()
    return OperatorRuntime(
        pack_id="trades",
        registry=build_trades_registry(),
        kernel_adapter=TradeKernel(kernel),
        reht=reht or RealReht(),
        gateway=ports.get("gateway") or TradeGateway(),
        veritas=ports.get("veritas") or TradeVeritas(),
        baro=ports.get("baro") or TradeBaro(),
    )


def build_health_runtime(reht: Any | None = None, kernel: Any | None = None, **ports: Any) -> OperatorRuntime:
    """Library surface: build a Health Operator runtime over the same boundary."""
    from valo_reht import RealReht

    from valo_health_pack import (
        HealthBaro,
        HealthGateway,
        HealthKernel,
        HealthVeritas,
        build_health_registry,
        seed_world,
    )

    kernel = kernel or seed_world()
    return OperatorRuntime(
        pack_id="health",
        registry=build_health_registry(),
        kernel_adapter=HealthKernel(kernel),
        reht=reht or RealReht(),
        gateway=ports.get("gateway") or HealthGateway(),
        veritas=ports.get("veritas") or HealthVeritas(),
        baro=ports.get("baro") or HealthBaro(),
    )


class ServiceHandler:
    """Transport-agnostic sidecar/service surface. JSON-able request in, JSON-
    able response out. Mount it behind HTTP, gRPC, message queue, whatever."""

    def __init__(self, runtime: OperatorRuntime) -> None:
        self.runtime = runtime

    def handle(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action == "submit":
            request = OperatorRequest.model_validate(payload.pop("request"))
            session = OperatorSession.model_validate(payload["session"]) if payload.get("session") else None
            result = self.runtime.submit(request, session=session)
            return {"api_version": API_VERSION, "result": result.model_dump(mode="json")}
        if action == "discover":
            return {"api_version": API_VERSION, "functions": self.runtime.discover()}
        if action == "capabilities":
            return {"api_version": API_VERSION, "capabilities": self.runtime.capabilities()}
        if action == "views":
            return {"api_version": API_VERSION, "views": self.runtime.views()}
        if action == "snapshot":
            return {"api_version": API_VERSION, "snapshot": self.runtime.snapshot()}
        raise ValueError(f"unknown action {action!r}")


class Gateway:
    """HTTP gateway/API surface. A pure route function (testable in-process)
    plus a minimal stdlib HTTP server. No change to the authorization chain."""

    def __init__(self, runtime: OperatorRuntime) -> None:
        self.handler = ServiceHandler(runtime)

    def route(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        if method == "POST" and path == "/submit":
            return 200, self.handler.handle("submit", body or {})
        if method == "GET" and path == "/discover":
            return 200, self.handler.handle("discover", {})
        if method == "GET" and path == "/capabilities":
            return 200, self.handler.handle("capabilities", {})
        if method == "GET" and path == "/views":
            return 200, self.handler.handle("views", {})
        if method == "GET" and path == "/snapshot":
            return 200, self.handler.handle("snapshot", {})
        return 404, {"error": f"no route for {method} {path}"}

    def serve(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        import json
        from http.server import BaseHTTPRequestHandler, HTTPServer

        gateway = self

        class _Handler(BaseHTTPRequestHandler):
            def _respond(self, status: int, payload: dict[str, Any]) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                status, payload = gateway.route("POST", self.path, body)
                self._respond(status, payload)

            def do_GET(self) -> None:  # noqa: N802
                status, payload = gateway.route("GET", self.path)
                self._respond(status, payload)

        server = HTTPServer((host, port), _Handler)
        server.serve_forever()
