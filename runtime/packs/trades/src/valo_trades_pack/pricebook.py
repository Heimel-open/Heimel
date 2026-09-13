from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class PriceComponent:
    labor_rate_per_hour: Decimal
    callout_fee: Decimal
    materials_cost: Decimal
    travel_cost: Decimal
    tax_rate: Decimal  # 0.25 = 25%
    minimum_charge: Decimal
    discount_constraints: tuple[Decimal, ...] = (Decimal("0.00"),)


class PriceBook:
    """Deterministic Price Book. The LLM may interpret the customer's
    description; it never decides the final price."""

    def __init__(self, component: PriceComponent) -> None:
        self.component = component

    def calculate(
        self,
        *,
        scope: dict[str, Any],
        estimated_duration_minutes: int,
        materials_cost: Decimal | None = None,
        discount: Decimal = Decimal("0.00"),
    ) -> dict[str, Decimal]:
        hours = Decimal(estimated_duration_minutes) / Decimal(60)
        labor = hours * self.component.labor_rate_per_hour
        materials = materials_cost if materials_cost is not None else self.component.materials_cost
        subtotal = self.component.callout_fee + labor + materials + self.component.travel_cost
        subtotal = max(subtotal, self.component.minimum_charge)
        max_discount = max(self.component.discount_constraints)
        discount = min(discount, max_discount)
        discounted = subtotal - discount
        tax = discounted * self.component.tax_rate
        total = discounted + tax
        return {
            "labor": labor,
            "materials": materials,
            "callout_fee": self.component.callout_fee,
            "travel": self.component.travel_cost,
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "total": total.quantize(Decimal("0.01")),
        }

    def reprice(self, scope: dict[str, Any], estimated_duration_minutes: int, materials_cost: Decimal | None = None) -> dict[str, Decimal]:
        return self.calculate(scope=scope, estimated_duration_minutes=estimated_duration_minutes, materials_cost=materials_cost)


STANDARD_PRICE_BOOK = PriceBook(
    PriceComponent(
        labor_rate_per_hour=Decimal(850),
        callout_fee=Decimal(500),
        materials_cost=Decimal(9000),
        travel_cost=Decimal(300),
        tax_rate=Decimal("0.25"),
        minimum_charge=Decimal(1500),
        discount_constraints=(Decimal("0.00"), Decimal(500), Decimal(1000)),
    )
)
