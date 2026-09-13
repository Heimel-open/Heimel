"""Customer-facing software ordering contract for Factory OS.

The model is deliberately horizontal: any customer with a software problem can
order from a reusable menu, add options, combine menu items, or submit a fully
custom request. Menu items are recipes, not vertical products and not authority.

Pizza/burger analogy:
- READY_MENU: choose a known recipe and configure allowed options.
- CUSTOM_MENU: describe the desired software outcome from scratch.
- HYBRID: start from one or more recipes and add custom requirements.

An accepted order can be materialized into the existing commercial POC mission
contract. It still traverses normal Factory OS build/QC and VAIG -> REHT -> RACS
for consequence-bearing execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from lib.commercial_loop import CustomerAcceptanceRef
from lib.commercial_missions import CommercialMissionKind, CommercialMissionSpec


class OrderMode(str, Enum):
    READY_MENU = "ready_menu"
    CUSTOM_MENU = "custom_menu"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class SoftwareMenuItem:
    item_id: str
    name: str
    objective: str
    recipe_ref: str
    default_acceptance_criteria: tuple[str, ...]
    configurable_options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("item_id", "name", "objective", "recipe_ref"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if not self.default_acceptance_criteria:
            raise ValueError("default_acceptance_criteria are required")


@dataclass(frozen=True)
class MenuSelection:
    item_id: str
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise ValueError("item_id is required")


@dataclass(frozen=True)
class CustomRequirement:
    requirement_id: str
    description: str
    acceptance_criterion: str

    def __post_init__(self) -> None:
        if not self.requirement_id.strip():
            raise ValueError("requirement_id is required")
        if not self.description.strip():
            raise ValueError("description is required")
        if not self.acceptance_criterion.strip():
            raise ValueError("acceptance_criterion is required")


@dataclass(frozen=True)
class CustomerSoftwareOrder:
    order_id: str
    customer_ref: str
    desired_outcome: str
    menu_selections: tuple[MenuSelection, ...] = ()
    custom_requirements: tuple[CustomRequirement, ...] = ()
    integrations: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    data_inputs: tuple[str, ...] = ()
    deployment_preferences: tuple[str, ...] = ()
    additional_acceptance_criteria: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("order_id", "customer_ref", "desired_outcome"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if not self.menu_selections and not self.custom_requirements:
            raise ValueError("order requires at least one menu selection or custom requirement")

    @property
    def mode(self) -> OrderMode:
        if self.menu_selections and self.custom_requirements:
            return OrderMode.HYBRID
        if self.menu_selections:
            return OrderMode.READY_MENU
        return OrderMode.CUSTOM_MENU

    @property
    def grants_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class ResolvedSoftwareOrder:
    order_id: str
    customer_ref: str
    mode: OrderMode
    objective: str
    recipe_refs: tuple[str, ...]
    selected_options: tuple[tuple[str, tuple[tuple[str, Any], ...]], ...]
    custom_requirements: tuple[CustomRequirement, ...]
    integrations: tuple[str, ...]
    constraints: tuple[str, ...]
    data_inputs: tuple[str, ...]
    deployment_preferences: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]

    @property
    def spec_ref(self) -> str:
        return f"customer-order:{self.order_id}"

    @property
    def grants_authority(self) -> bool:
        return False


class SoftwareMenu:
    """Reusable horizontal software recipes; no industry classification."""

    def __init__(self, items: tuple[SoftwareMenuItem, ...]) -> None:
        if not items:
            raise ValueError("software menu cannot be empty")
        by_id: dict[str, SoftwareMenuItem] = {}
        for item in items:
            if item.item_id in by_id:
                raise ValueError(f"duplicate menu item: {item.item_id}")
            by_id[item.item_id] = item
        self._items = by_id

    def get(self, item_id: str) -> SoftwareMenuItem:
        try:
            return self._items[item_id]
        except KeyError as exc:
            raise ValueError(f"unknown menu item: {item_id}") from exc

    @property
    def items(self) -> tuple[SoftwareMenuItem, ...]:
        return tuple(self._items.values())

    def resolve(self, order: CustomerSoftwareOrder) -> ResolvedSoftwareOrder:
        recipe_refs: list[str] = []
        criteria: list[str] = []
        selected_options: list[tuple[str, tuple[tuple[str, Any], ...]]] = []

        for selection in order.menu_selections:
            item = self.get(selection.item_id)
            allowed = set(item.configurable_options)
            unknown = set(selection.options) - allowed
            if unknown:
                raise ValueError(
                    f"unsupported options for {item.item_id}: {', '.join(sorted(unknown))}"
                )
            recipe_refs.append(item.recipe_ref)
            criteria.extend(item.default_acceptance_criteria)
            selected_options.append(
                (selection.item_id, tuple(sorted(selection.options.items())))
            )

        criteria.extend(
            requirement.acceptance_criterion for requirement in order.custom_requirements
        )
        criteria.extend(order.additional_acceptance_criteria)

        if not criteria:
            raise ValueError("resolved order requires acceptance criteria")

        return ResolvedSoftwareOrder(
            order_id=order.order_id,
            customer_ref=order.customer_ref,
            mode=order.mode,
            objective=order.desired_outcome,
            recipe_refs=tuple(dict.fromkeys(recipe_refs)),
            selected_options=tuple(selected_options),
            custom_requirements=order.custom_requirements,
            integrations=order.integrations,
            constraints=order.constraints,
            data_inputs=order.data_inputs,
            deployment_preferences=order.deployment_preferences,
            acceptance_criteria=tuple(dict.fromkeys(criteria)),
        )


def default_software_menu() -> SoftwareMenu:
    """Small generic menu. Customers can combine items or go fully custom."""

    return SoftwareMenu(
        (
            SoftwareMenuItem(
                item_id="workflow-automation",
                name="Workflow automation",
                objective="Automate a repeated business workflow end to end",
                recipe_ref="recipe:workflow-automation:v1",
                default_acceptance_criteria=(
                    "agreed workflow completes end to end",
                    "failure path is observable and recoverable",
                ),
                configurable_options=("trigger", "approvals", "notifications", "systems"),
            ),
            SoftwareMenuItem(
                item_id="system-integration",
                name="System integration",
                objective="Connect existing software through governed APIs or events",
                recipe_ref="recipe:system-integration:v1",
                default_acceptance_criteria=(
                    "agreed systems exchange the required data",
                    "retries and duplicate delivery are handled deterministically",
                ),
                configurable_options=("source", "destination", "sync_mode", "mapping"),
            ),
            SoftwareMenuItem(
                item_id="ai-agent",
                name="AI agent",
                objective="Build an AI agent around a bounded customer workflow",
                recipe_ref="recipe:ai-agent:v1",
                default_acceptance_criteria=(
                    "agent completes the agreed scenario",
                    "consequence-bearing actions use the configured governance boundary",
                ),
                configurable_options=("tools", "model", "knowledge", "channels"),
            ),
            SoftwareMenuItem(
                item_id="internal-app",
                name="Internal application",
                objective="Build a focused internal software application",
                recipe_ref="recipe:internal-app:v1",
                default_acceptance_criteria=(
                    "agreed users can complete the target task",
                    "required data persists and is retrievable",
                ),
                configurable_options=("users", "roles", "workflows", "integrations"),
            ),
            SoftwareMenuItem(
                item_id="customer-app",
                name="Customer-facing application",
                objective="Build a customer-facing web/API software experience",
                recipe_ref="recipe:customer-app:v1",
                default_acceptance_criteria=(
                    "target customer journey completes end to end",
                    "customer-visible failures are handled explicitly",
                ),
                configurable_options=("surface", "identity", "payments", "integrations"),
            ),
            SoftwareMenuItem(
                item_id="data-product",
                name="Data and reporting product",
                objective="Turn customer data into a usable operational product",
                recipe_ref="recipe:data-product:v1",
                default_acceptance_criteria=(
                    "required source data is ingested and traceable",
                    "agreed output is reproducible from source evidence",
                ),
                configurable_options=("sources", "outputs", "refresh", "retention"),
            ),
        )
    )


def to_poc_mission_spec(
    resolved: ResolvedSoftwareOrder,
    acceptance: CustomerAcceptanceRef,
    *,
    target_repo: str,
    owned_files: tuple[str, ...],
    canonical_base_sha: str | None = None,
) -> CommercialMissionSpec:
    """Materialize an explicitly accepted customer order into a normal POC mission."""

    if acceptance.subject not in {resolved.order_id, resolved.spec_ref}:
        raise ValueError("customer acceptance is not bound to this software order")

    dependencies = tuple(
        dict.fromkeys(
            (
                resolved.spec_ref,
                *resolved.recipe_refs,
                *resolved.integrations,
            )
        )
    )
    return CommercialMissionSpec(
        kind=CommercialMissionKind.POC,
        customer_ref=resolved.customer_ref,
        spec_ref=resolved.spec_ref,
        spec_digest=acceptance.acceptance_ref,
        target_repo=target_repo,
        objective=resolved.objective,
        owned_files=owned_files,
        acceptance_criteria=resolved.acceptance_criteria,
        dependencies=dependencies,
        canonical_base_sha=canonical_base_sha,
    )


__all__ = [
    "CustomerSoftwareOrder",
    "CustomRequirement",
    "MenuSelection",
    "OrderMode",
    "ResolvedSoftwareOrder",
    "SoftwareMenu",
    "SoftwareMenuItem",
    "default_software_menu",
    "to_poc_mission_spec",
]
