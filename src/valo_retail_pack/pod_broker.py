from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProductSpec:
    title: str
    blueprint_id: int
    print_provider_id: int
    variant_ids: tuple[int, ...]
    artwork_url: str
    retail_price_cents: int
    description: str = ""


@dataclass(frozen=True)
class ProductReceipt:
    provider: str
    provider_product_id: str
    published: bool
    shop_id: str


class PODProvider(Protocol):
    def create_product(self, spec: ProductSpec) -> ProductReceipt: ...
    def publish_product(self, provider_product_id: str) -> ProductReceipt: ...


class PODBroker:
    """Provider-neutral agent boundary for create -> publish.

    The broker deliberately exposes a small deterministic contract so Hermes/Codex
    can operate POD backends without humans using provider dashboards.
    """

    def __init__(self, provider: PODProvider) -> None:
        self._provider = provider

    def create_and_publish(self, spec: ProductSpec) -> ProductReceipt:
        created = self._provider.create_product(spec)
        if created.published:
            return created
        return self._provider.publish_product(created.provider_product_id)
