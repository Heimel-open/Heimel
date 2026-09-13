"""Standalone health-provider-shaped fixture service.

Two deliberately different protocols expose scheduling, EHR-note and renewal
work-queue effects. The process contains no VALO authorization logic; it only
enforces transport protocol, idempotency and independently readable state.
"""

from __future__ import annotations

import json
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


class _State:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.by_key: dict[tuple[str, str], str] = {}
        self.lock = threading.Lock()


STATE = _State()


def _send(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _store(
    handler: BaseHTTPRequestHandler,
    *,
    provider: str,
    auth_name: str,
    auth_value: str,
    idem_name: str,
    id_field: str,
    state_field: str,
    landing: str,
    kind: str,
) -> None:
    if handler.headers.get(auth_name) != auth_value:
        _send(handler, 401, {"error": "unauthorized"})
        return
    length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(length)) if length else {}
    idem = handler.headers.get(idem_name) or ""
    key = (provider, idem)
    with STATE.lock:
        existing_id = STATE.by_key.get(key) if idem else None
        if existing_id is not None:
            existing = STATE.records[existing_id]
            _send(handler, 200, {id_field: existing_id, state_field: existing[state_field]})
            return
        record_id = f"{provider}-{kind}-{uuid.uuid4().hex[:8]}"
        record = {
            id_field: record_id,
            "kind": kind,
            state_field: landing,
            "request_digest": body.get("payload_digest") or body.get("candidate_digest"),
            "action_type": body.get("action_type"),
        }
        STATE.records[record_id] = record
        if idem:
            STATE.by_key[key] = record_id
    _send(handler, 200, {id_field: record_id})


def _lookup(
    handler: BaseHTTPRequestHandler,
    *,
    provider: str,
    prefix: str,
    auth_name: str,
    auth_value: str,
    id_field: str,
) -> None:
    if handler.headers.get(auth_name) != auth_value:
        _send(handler, 401, {"error": "unauthorized"})
        return
    record_id = handler.path[len(prefix) :]
    with STATE.lock:
        record = STATE.records.get(record_id)
    if record is None or not record_id.startswith(f"{provider}-"):
        _send(handler, 404, {"error": "unknown record"})
        return
    if id_field not in record:
        _send(handler, 500, {"error": "fixture schema mismatch"})
        return
    _send(handler, 200, record)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        provider_a = {
            "/appointments/actions": ("schedule", "APPLIED"),
            "/clinical-notes": ("ehr", "COMMITTED"),
            "/renewals/actions": ("renewal", "APPLIED"),
        }
        if self.path in provider_a:
            kind, landing = provider_a[self.path]
            _store(
                self,
                provider="a",
                auth_name="Authorization",
                auth_value="Bearer health-a",
                idem_name="Idempotency-Key",
                id_field="id",
                state_field="status",
                landing=landing,
                kind=kind,
            )
            return

        provider_b = {
            "/api/actions/schedule": "schedule",
            "/api/records/notes": "ehr",
            "/api/tasks/renewal": "renewal",
        }
        if self.path in provider_b:
            _store(
                self,
                provider="b",
                auth_name="X-API-Key",
                auth_value="health-b",
                idem_name="X-Request-Key",
                id_field="resource_id",
                state_field="state",
                landing="done",
                kind=provider_b[self.path],
            )
            return
        _send(self, 404, {"error": "unknown path"})

    def do_GET(self) -> None:  # noqa: N802
        for prefix in (
            "/appointments/actions/",
            "/clinical-notes/",
            "/renewals/actions/",
        ):
            if self.path.startswith(prefix):
                _lookup(
                    self,
                    provider="a",
                    prefix=prefix,
                    auth_name="Authorization",
                    auth_value="Bearer health-a",
                    id_field="id",
                )
                return
        for prefix in (
            "/api/state/schedule/",
            "/api/state/notes/",
            "/api/state/renewal/",
        ):
            if self.path.startswith(prefix):
                _lookup(
                    self,
                    provider="b",
                    prefix=prefix,
                    auth_name="X-API-Key",
                    auth_value="health-b",
                    id_field="resource_id",
                )
                return
        _send(self, 404, {"error": "unknown path"})


def serve(host: str = "127.0.0.1", port: int = 0) -> HTTPServer:
    server = HTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8450
    server = serve(port=port)
    host, actual = server.server_address[:2]
    print(f"HEALTH_VENDOR_READY {host}:{actual}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
