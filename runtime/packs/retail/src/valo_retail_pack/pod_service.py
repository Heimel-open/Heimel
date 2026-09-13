from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from valo_retail_pack.pod_broker import PODBroker, ProductSpec
from valo_retail_pack.providers.printify import PrintifyProvider


def _broker() -> PODBroker:
    token = os.environ["PRINTIFY_TOKEN"]
    shop_id = os.environ["PRINTIFY_SHOP_ID"]
    return PODBroker(PrintifyProvider(token=token, shop_id=shop_id))


class Handler(BaseHTTPRequestHandler):
    server_version = "valo-pod-broker/0.1"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        expected = os.environ.get("POD_BROKER_KEY")
        return bool(expected) and self.headers.get("Authorization") == f"Bearer {expected}"

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"ok": True})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/v1/products":
            self._json(404, {"error": "not_found"})
            return
        if not self._authorized():
            self._json(401, {"error": "unauthorized"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
            spec = ProductSpec(
                title=data["title"],
                blueprint_id=int(data["blueprint_id"]),
                print_provider_id=int(data["print_provider_id"]),
                variant_ids=tuple(int(v) for v in data["variant_ids"]),
                artwork_url=data["artwork_url"],
                retail_price_cents=int(data["retail_price_cents"]),
                description=data.get("description", ""),
            )
            receipt = _broker().create_and_publish(spec)
            self._json(
                201,
                {
                    "provider": receipt.provider,
                    "provider_product_id": receipt.provider_product_id,
                    "published": receipt.published,
                    "shop_id": receipt.shop_id,
                },
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": "invalid_request", "detail": str(exc)})
        except Exception as exc:
            self._json(502, {"error": "provider_failure", "detail": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
