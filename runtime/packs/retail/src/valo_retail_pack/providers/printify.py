from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from valo_retail_pack.pod_broker import ProductReceipt, ProductSpec


@dataclass
class PrintifyProvider:
    token: str
    shop_id: str
    base_url: str = "https://api.printify.com/v1"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json;charset=utf-8",
                "User-Agent": "valo-retail-pack-pod-broker/0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}

    def upload_artwork(self, artwork_url: str) -> str:
        file_name = os.path.basename(artwork_url.split("?", 1)[0]) or "artwork.png"
        result = self._request(
            "POST",
            "/uploads/images.json",
            {"file_name": file_name, "url": artwork_url},
        )
        return str(result["id"])

    def create_product(self, spec: ProductSpec) -> ProductReceipt:
        image_id = self.upload_artwork(spec.artwork_url)
        variants = [
            {"id": variant_id, "price": spec.retail_price_cents, "is_enabled": True}
            for variant_id in spec.variant_ids
        ]
        payload = {
            "title": spec.title,
            "description": spec.description,
            "blueprint_id": spec.blueprint_id,
            "print_provider_id": spec.print_provider_id,
            "variants": variants,
            "print_areas": [
                {
                    "variant_ids": list(spec.variant_ids),
                    "placeholders": [
                        {
                            "position": "front",
                            "images": [
                                {
                                    "id": image_id,
                                    "x": 0.5,
                                    "y": 0.5,
                                    "scale": 1.0,
                                    "angle": 0,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = self._request("POST", f"/shops/{self.shop_id}/products.json", payload)
        return ProductReceipt(
            provider="printify",
            provider_product_id=str(result["id"]),
            published=False,
            shop_id=self.shop_id,
        )

    def publish_product(self, provider_product_id: str) -> ProductReceipt:
        payload = {
            "title": True,
            "description": True,
            "images": True,
            "variants": True,
            "tags": True,
            "keyFeatures": True,
            "shipping_template": True,
        }
        self._request(
            "POST",
            f"/shops/{self.shop_id}/products/{provider_product_id}/publish.json",
            payload,
        )
        return ProductReceipt(
            provider="printify",
            provider_product_id=provider_product_id,
            published=True,
            shop_id=self.shop_id,
        )
