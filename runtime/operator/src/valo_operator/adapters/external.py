"""A real-ish external system for production-adapter tests.

An in-process HTTP server simulating an external service (e.g. a notification
service). The send response (HTTP 200) is SEPARATE from the observed state:
records land in DELIVERED / PENDING / FAILED, and Veritas must query the state
endpoint — never trust the POST response alone.
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


class ExternalSystem:
    """Minimal external service. `landing` controls whether submitted records
    become DELIVERED (reality) or stay PENDING/FAILED even though the HTTP
    send succeeded — the crux of the HTTP-200-is-not-delivered invariant."""

    def __init__(
        self,
        landing: str = "DELIVERED",
        landing_by_action: dict[str, str] | None = None,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.landing = landing
        self.landing_by_action = landing_by_action or {}
        self.records: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.server = HTTPServer((host, port), self._handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _handler(self):
        external = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                return

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                record_id = body.get("id") or f"ext-{uuid.uuid4().hex[:8]}"
                with external.lock:
                    if record_id in external.records:
                        # idempotent replay: the external system returns the
                        # SAME record — no double effect
                        existing = external.records[record_id]
                        self._send_json(200, existing)
                        return
                    record = {
                        "id": record_id,
                        "action_type": body.get("action_type"),
                        "status": external.landing_by_action.get(body.get("action_type"), external.landing),
                    }
                    external.records[record_id] = record
                self._send_json(200, {"accepted": True, "id": record_id})

            def do_GET(self) -> None:  # noqa: N802
                path = self.path
                prefix = "/records/"
                if path.startswith(prefix):
                    record_id = path[len(prefix):]
                    with external.lock:
                        record = external.records.get(record_id)
                    if record is None:
                        self._send_json(404, {"error": "unknown record"})
                        return
                    self._send_json(200, record)
                    return
                self._send_json(404, {"error": "unknown path"})

        return _Handler
