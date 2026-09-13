"""A real, standalone external notification service.

Runs as its OWN process with its OWN state over HTTP. The effect point is the
service's record state (DELIVERED / PENDING / FAILED); an HTTP 200 from the
send is NOT that state. Veritas must read it back independently.

Modes (env NOTIFIER_LANDING): DELIVERED, PENDING, FAILED, TIMEOUT.
TIMEOUT accepts the request but never records the effect -> the observer gets
an unknown outcome, never a synthetic success.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

LANDING = os.environ.get("NOTIFIER_LANDING", "DELIVERED")
try:
    LANDING_BY_ACTION = json.loads(os.environ.get("NOTIFIER_LANDING_BY_ACTION", "{}"))
except json.JSONDecodeError:
    LANDING_BY_ACTION = {}


class _State:
    def __init__(self, landing: str, landing_by_action: dict[str, str]) -> None:
        self.landing = landing
        self.landing_by_action = landing_by_action
        self.records: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()


STATE = _State(LANDING, LANDING_BY_ACTION)


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
        record_id = body.get("id") or f"n-{uuid.uuid4().hex[:8]}"
        with STATE.lock:
            if record_id in STATE.records:
                self._send_json(200, STATE.records[record_id])  # idempotent replay
                return
            landing = STATE.landing_by_action.get(body.get("action_type"), STATE.landing)
            if landing == "TIMEOUT":
                # accept the request but produce NO effect
                self._send_json(200, {"accepted": True, "id": record_id})
                return
            record = {"id": record_id, "kind": "notification", "status": landing}
            STATE.records[record_id] = record
        self._send_json(200, {"accepted": True, "id": record_id})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/records/"):
            record_id = self.path[len("/records/"):]
            with STATE.lock:
                record = STATE.records.get(record_id)
            if record is None:
                self._send_json(404, {"error": "unknown record"})
                return
            self._send_json(200, record)
            return
        self._send_json(404, {"error": "unknown path"})


def serve(host: str = "127.0.0.1", port: int = 0) -> HTTPServer:
    server = HTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8200
    server = serve(port=port)
    host, actual = server.server_address[:2]
    print(f"NOTIFIER_READY {host}:{actual} landing={LANDING}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
