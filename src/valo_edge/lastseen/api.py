"""Local HTTP API and web UI for LastSeen. Binds to localhost only, no telemetry."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
from typing import Any, Sequence
from urllib.parse import parse_qs, unquote, urlparse

from valo_edge.lastseen.cli import _result_payload
from valo_edge.lastseen.service import LastSeenService, MemoryScope


_OBJECT_PATH = re.compile(r"^/objects/(?P<name>[^/]+)/last-seen$")
_OBJECT_DELETE_PATH = re.compile(r"^/objects/(?P<name>[^/]+)$")
_HISTORY_PATH = re.compile(r"^/objects/(?P<name>[^/]+)/history$")
_RECEIPT_PATH = re.compile(r"^/receipts/(?P<digest>[^/]+)$")

WEB_ROOT = Path(__file__).resolve().parent / "web"


def _write(
    handler: BaseHTTPRequestHandler,
    status: int,
    payload: Any,
    content_type: str = "application/json; charset=utf-8",
) -> None:
    if content_type.startswith("application/json"):
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    else:
        body = payload.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    return payload


def _scope_from_query(query: dict[str, list[str]]) -> MemoryScope:
    return MemoryScope(
        camera_ids=tuple(query.get("camera_id", ())),
        zone_ids=tuple(query.get("zone_id", ())),
        since_iso=query.get("since", [None])[0],
        until_iso=query.get("until", [None])[0],
    )


class LastSeenRequestHandler(BaseHTTPRequestHandler):
    server_version = "LastSeen/0.2.0"

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _service(self) -> LastSeenService:
        return self.server.service  # type: ignore[attr-defined]

    def _send(self, status: int, payload: Any) -> None:
        _write(self, status, payload)

    def _handle_error(self, exc: Exception) -> None:
        if isinstance(exc, KeyError):
            self._send(400, {"error": f"missing required field: {exc.args[0]}"})
        elif isinstance(exc, ValueError):
            self._send(400, {"error": str(exc)})
        elif isinstance(exc, PermissionError):
            self._send(403, {"error": str(exc)})
        else:
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

    def _serve_index(self) -> None:
        index_path = WEB_ROOT / "index.html"
        if not index_path.exists():
            self._send(404, "index.html not found", content_type="text/html; charset=utf-8")
            return
        _write(
            self,
            200,
            index_path.read_text(encoding="utf-8"),
            content_type="text/html; charset=utf-8",
        )

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path in ("/", "/index.html"):
                self._serve_index()
                return
            receipt_match = _RECEIPT_PATH.match(path)
            if receipt_match:
                digest = receipt_match.group("digest")
                receipt = self._service().get_receipt(digest)
                if receipt is None:
                    self._send(404, {"error": "receipt not found", "digest": digest})
                    return
                self._send(200, receipt)
                return
            last_seen_match = _OBJECT_PATH.match(path)
            if last_seen_match:
                name = unquote(last_seen_match.group("name"))
                aliases = tuple(query.get("alias", ()))
                result = self._service().find(
                    name,
                    aliases=aliases,
                    scope=_scope_from_query(query),
                )
                if result is None:
                    self._send(404, {"found": False, "object": name})
                    return
                self._send(200, _result_payload(result))
                return
            history_match = _HISTORY_PATH.match(path)
            if history_match:
                name = unquote(history_match.group("name"))
                limit = int(query.get("limit", ["100"])[0])
                results = self._service().history(
                    name,
                    aliases=tuple(query.get("alias", ())),
                    scope=_scope_from_query(query),
                    limit=limit,
                )
                self._send(
                    200,
                    {
                        "found": bool(results),
                        "count": len(results),
                        "results": [_result_payload(result) for result in results],
                    },
                )
                return
            self._send(404, {"error": "not found", "path": path})
        except Exception as exc:
            self._handle_error(exc)

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path != "/observations":
                self._send(404, {"error": "not found", "path": parsed.path})
                return
            body = _read_json(self)
            metadata = body.get("metadata") or {}
            result = self._service().remember(
                body["object_name"],
                body["location"],
                image_ref=body.get("image_ref"),
                confidence=float(body.get("confidence", 1.0)),
                observed_at_iso=body.get("observed_at_iso"),
                metadata=metadata,
                source_id=body.get("source_id"),
                source_type=body.get("source_type", "api-observation"),
                source_device_id=body.get("source_device_id"),
                camera_id=body.get("camera_id") or metadata.get("camera_id"),
                zone_id=body.get("zone_id") or metadata.get("zone_id"),
                policy_version=body.get("policy_version"),
                aliases=body.get("aliases", ()),
            )
            self._send(201, _result_payload(result))
        except Exception as exc:
            self._handle_error(exc)

    def do_DELETE(self) -> None:
        try:
            parsed = urlparse(self.path)
            match = _OBJECT_DELETE_PATH.match(parsed.path)
            if not match:
                self._send(404, {"error": "not found", "path": parsed.path})
                return
            name = unquote(match.group("name"))
            deletion = self._service().forget_with_receipt(name)
            self._send(200, asdict(deletion))
        except Exception as exc:
            self._handle_error(exc)


class LastSeenHTTPServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], service: LastSeenService) -> None:
        self.service = service
        super().__init__(address, LastSeenRequestHandler)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lastseen-api",
        description="Serve the LastSeen local HTTP API and web UI.",
    )
    parser.add_argument("--db", default="lastseen.db", help="Local SQLite database path")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (localhost only by default)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    parser.add_argument(
        "--policy-version",
        default="lastseen-policy-v1",
        help="Local policy version recorded in source provenance and receipts",
    )
    args = parser.parse_args(argv)
    with LastSeenService(args.db, policy_version=args.policy_version) as service:
        httpd = LastSeenHTTPServer((args.host, args.port), service)
        print(f"LastSeen API listening on http://{args.host}:{args.port}")
        print("Memory stays local. No telemetry. Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
