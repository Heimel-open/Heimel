"""A standalone vendor-shaped service that ENFORCES vendor-specific transport.

It requires the vendor's auth header (401 without), dedups by the vendor's
idempotency header, and exposes state at the vendor's paths/fields. It serves
TWO vendor protocols (payments- and messaging-style) on one process, so the
tests prove the SAME operator chain drives both purely via config.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

# per-vendor landing
PAYMENTS_LANDING = os.environ.get("PAYMENTS_LANDING", "SUCCEEDED")
MESSAGING_LANDING = os.environ.get("MESSAGING_LANDING", "delivered")


class _State:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()


STATE = _State()


def _send(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _handle_vendor(
    handler: BaseHTTPRequestHandler,
    *,
    auth_header: str,
    auth_value: str,
    idempotency_header: str,
    landing: str,
    prefix: str,
    kind: str,
    status_field: str,
) -> None:
    # enforce the vendor auth protocol
    if handler.headers.get(auth_header) != auth_value:
        _send(handler, 401, {"error": "unauthorized"})
        return

    length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(length)) if length else {}
    key = handler.headers.get(idempotency_header)
    record_id = body.get("id") or f"{kind}-{uuid.uuid4().hex[:8]}"
    with STATE.lock:
        if record_id in STATE.records:
            _send(handler, 200, STATE.records[record_id])  # idempotent replay
            return
        record = {"id": record_id, "kind": kind, status_field: landing, "idempotency_key": key}
        STATE.records[record_id] = record
    _send(handler, 200, {"accepted": True, "id": record_id})


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/v1/payments":
            _handle_vendor(
                self, auth_header="Authorization", auth_value="Bearer sk-test",
                idempotency_header="Idempotency-Key", landing=PAYMENTS_LANDING,
                prefix="/v1/payments", kind="payment", status_field="status",
            )
            return
        if self.path == "/2010-04-01/Messages.json":
            _handle_vendor(
                self, auth_header="Account-Sid", auth_value="AC-test",
                idempotency_header="X-Idempotency-Key", landing=MESSAGING_LANDING,
                prefix="/2010-04-01/Messages", kind="message", status_field="status",
            )
            return
        _send(self, 404, {"error": "unknown path"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/v1/payments/"):
            record_id = self.path[len("/v1/payments/"):]
            with STATE.lock:
                record = STATE.records.get(record_id)
            if record is None:
                _send(self, 404, {"error": "unknown record"})
                return
            _send(self, 200, record)
            return
        if self.path.startswith("/2010-04-01/Messages/"):
            rest = self.path[len("/2010-04-01/Messages/"):]
            record_id = rest[: -len(".json")] if rest.endswith(".json") else rest
            with STATE.lock:
                record = STATE.records.get(record_id)
            if record is None:
                _send(self, 404, {"error": "unknown record"})
                return
            _send(self, 200, record)
            return
        _send(self, 404, {"error": "unknown path"})


def serve(host: str = "127.0.0.1", port: int = 0) -> HTTPServer:
    server = HTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8400
    server = serve(port=port)
    host, actual = server.server_address[:2]
    print(f"VENDOR_READY {host}:{actual} payments={PAYMENTS_LANDING} messaging={MESSAGING_LANDING}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
