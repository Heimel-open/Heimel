"""A real, standalone external ledger service.

Runs as its OWN process with its OWN state over HTTP. The effect point is a
committed ledger entry. It accepts only entries it can commit (balance /
consistency), so a send can succeed while the commit fails — again proving the
send response is not the effect.

The service is deliberately "dumb": it applies whatever entry it is asked to
commit. It has NO authorization logic — the Operator contract carries none of
it into the adapter (acceptance criterion 9).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

MODE = os.environ.get("LEDGER_MODE", "OK")  # OK | REJECT | TIMEOUT


class _State:
    def __init__(self) -> None:
        self.entries: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()


STATE = _State()


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
        entry_id = body.get("id") or f"l-{uuid.uuid4().hex[:8]}"
        with STATE.lock:
            if entry_id in STATE.entries:
                self._send_json(200, STATE.entries[entry_id])  # idempotent replay
                return
            if MODE == "TIMEOUT":
                self._send_json(200, {"accepted": True, "id": entry_id})
                return
            if MODE == "REJECT":
                self._send_json(200, {"accepted": False, "id": entry_id, "reason": "consistency rejected"})
                return
            entry = {"id": entry_id, "kind": "ledger", "amount": body.get("amount"), "status": "COMMITTED"}
            STATE.entries[entry_id] = entry
        self._send_json(200, {"accepted": True, "id": entry_id})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/entries/"):
            entry_id = self.path[len("/entries/"):]
            with STATE.lock:
                entry = STATE.entries.get(entry_id)
            if entry is None:
                self._send_json(404, {"error": "unknown entry"})
                return
            self._send_json(200, entry)
            return
        self._send_json(404, {"error": "unknown path"})


def serve(host: str = "127.0.0.1", port: int = 0) -> HTTPServer:
    server = HTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8300
    server = serve(port=port)
    host, actual = server.server_address[:2]
    print(f"LEDGER_READY {host}:{actual} mode={MODE}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
