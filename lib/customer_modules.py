"""Horizontal customer module catalog for Factory OS.

A module is a reusable business outcome recipe, not an architecture layer and
not a vertical. The catalog is deliberately open-ended: software, innovation,
research, compliance, hiring, contracting and any other repeatable customer
outcome can be offered through the same ready/custom/hybrid ordering model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ModuleOrderMode(str, Enum):
    READY = "ready"
    CUSTOM = "custom"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class CustomerModuleRecipe:
    module_id: str
    name: str
    objective: str
    output_types: tuple[str, ...]
    default_acceptance_criteria: tuple[str, ...]
    configurable_options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("module_id", "name", "objective"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if not self.output_types or not self.default_acceptance_criteria:
            raise ValueError("output_types and default_acceptance_criteria are required")

    @property
    def grants_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class ModuleSelection:
    module_id: str
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.module_id.strip():
            raise ValueError("module_id is required")


@dataclass(frozen=True)
class CustomModuleRequirement:
    requirement_ref: str
    description: str
    acceptance_criterion: str

    def __post_init__(self) -> None:
        if not self.requirement_ref.strip() or not self.description.strip():
            raise ValueError("requirement_ref and description are required")
        if not self.acceptance_criterion.strip():
            raise ValueError("acceptance_criterion is required")


@dataclass(frozen=True)
class CustomerModuleOrder:
    order_ref: str
    customer_ref: str
    desired_outcome: str
    selections: tuple[ModuleSelection, ...] = ()
    custom_requirements: tuple[CustomModuleRequirement, ...] = ()
    constraints: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    additional_acceptance_criteria: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("order_ref", "customer_ref", "desired_outcome"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if not self.selections and not self.custom_requirements:
            raise ValueError("module order requires a selection or custom requirement")

    @property
    def mode(self) -> ModuleOrderMode:
        if self.selections and self.custom_requirements:
            return ModuleOrderMode.HYBRID
        if self.selections:
            return ModuleOrderMode.READY
        return ModuleOrderMode.CUSTOM

    @property
    def grants_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class ResolvedModuleOrder:
    order_ref: str
    customer_ref: str
    mode: ModuleOrderMode
    desired_outcome: str
    module_ids: tuple[str, ...]
    output_types: tuple[str, ...]
    selected_options: tuple[tuple[str, tuple[tuple[str, Any], ...]], ...]
    custom_requirements: tuple[CustomModuleRequirement, ...]
    constraints: tuple[str, ...]
    inputs: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]

    @property
    def grants_authority(self) -> bool:
        return False


class CustomerModuleCatalog:
    def __init__(self, recipes: tuple[CustomerModuleRecipe, ...]) -> None:
        if not recipes:
            raise ValueError("module catalog cannot be empty")
        by_id: dict[str, CustomerModuleRecipe] = {}
        for recipe in recipes:
            if recipe.module_id in by_id:
                raise ValueError(f"duplicate module: {recipe.module_id}")
            by_id[recipe.module_id] = recipe
        self._recipes = by_id

    def get(self, module_id: str) -> CustomerModuleRecipe:
        try:
            return self._recipes[module_id]
        except KeyError as exc:
            raise ValueError(f"unknown module: {module_id}") from exc

    @property
    def recipes(self) -> tuple[CustomerModuleRecipe, ...]:
        return tuple(self._recipes.values())

    def resolve(self, order: CustomerModuleOrder) -> ResolvedModuleOrder:
        module_ids: list[str] = []
        output_types: list[str] = []
        criteria: list[str] = []
        selected_options: list[tuple[str, tuple[tuple[str, Any], ...]]] = []

        for selection in order.selections:
            recipe = self.get(selection.module_id)
            unknown = set(selection.options) - set(recipe.configurable_options)
            if unknown:
                raise ValueError(
                    f"unsupported options for {recipe.module_id}: {', '.join(sorted(unknown))}"
                )
            module_ids.append(recipe.module_id)
            output_types.extend(recipe.output_types)
            criteria.extend(recipe.default_acceptance_criteria)
            selected_options.append(
                (selection.module_id, tuple(sorted(selection.options.items())))
            )

        criteria.extend(
            requirement.acceptance_criterion for requirement in order.custom_requirements
        )
        criteria.extend(order.additional_acceptance_criteria)
        if not criteria:
            raise ValueError("resolved module order requires acceptance criteria")

        return ResolvedModuleOrder(
            order_ref=order.order_ref,
            customer_ref=order.customer_ref,
            mode=order.mode,
            desired_outcome=order.desired_outcome,
            module_ids=tuple(dict.fromkeys(module_ids)),
            output_types=tuple(dict.fromkeys(output_types)),
            selected_options=tuple(selected_options),
            custom_requirements=order.custom_requirements,
            constraints=order.constraints,
            inputs=order.inputs,
            acceptance_criteria=tuple(dict.fromkeys(criteria)),
        )


def default_customer_module_catalog() -> CustomerModuleCatalog:
    """Starter menu. The catalog is extensible and these are not boundaries."""

    return CustomerModuleCatalog(
        (
            CustomerModuleRecipe(
                "software",
                "Custom Software",
                "Design, build, test and deliver customer-specific software",
                ("software", "deployment", "tests"),
                ("accepted scope is implemented", "independent verification passes"),
                ("surface", "integrations", "deployment", "support"),
            ),
            CustomerModuleRecipe(
                "shadow-discovery",
                "Shadow Discovery",
                "Understand the business through scoped read-only swarm observation",
                ("evidence-map", "opportunity-map", "proposal"),
                ("all findings are evidence-backed", "proposal includes scope price and delivery"),
                ("sources", "roles", "duration", "continuous"),
            ),
            CustomerModuleRecipe(
                "innovation",
                "Innovation",
                "Discover, prototype and validate new products, services or operating models",
                ("opportunity-map", "prototype", "business-case"),
                ("hypothesis is explicit", "prototype tests agreed hypothesis"),
                ("domain", "budget", "horizon", "prototype_depth"),
            ),
            CustomerModuleRecipe(
                "research",
                "Research",
                "Answer a customer research question with traceable evidence",
                ("research-report", "evidence-pack", "recommendation"),
                ("claims are traceable to evidence", "uncertainty and conflicts are explicit"),
                ("depth", "sources", "jurisdictions", "time_window"),
            ),
            CustomerModuleRecipe(
                "compliance",
                "Compliance",
                "Assess requirements, gaps and remediation work against selected obligations",
                ("gap-analysis", "control-map", "remediation-plan"),
                ("requirements are source-linked", "gaps and remediation owners are explicit"),
                ("frameworks", "jurisdictions", "systems", "evidence_scope"),
            ),
            CustomerModuleRecipe(
                "hiring",
                "Hiring",
                "Define a role, source candidates and prepare an evidence-backed shortlist",
                ("role-spec", "candidate-evidence", "shortlist"),
                ("role criteria are explicit", "shortlist is evidence-backed and reviewable"),
                ("role", "location", "seniority", "channels"),
            ),
            CustomerModuleRecipe(
                "contracting",
                "Contracting",
                "Prepare and negotiate bounded commercial/legal document workflows",
                ("contract-draft", "issue-list", "negotiation-package"),
                ("terms map to customer instructions", "exceptions are surfaced for approval"),
                ("contract_type", "jurisdiction", "counterparty", "risk_tolerance"),
            ),
            CustomerModuleRecipe(
                "procurement",
                "Procurement",
                "Research suppliers, compare options and prepare a governed purchase recommendation",
                ("supplier-set", "comparison", "purchase-recommendation"),
                ("selection criteria are explicit", "recommendation is evidence-backed"),
                ("category", "budget", "region", "requirements"),
            ),
            CustomerModuleRecipe(
                "operations",
                "Operations",
                "Analyze and improve a business process or operational system",
                ("process-map", "improvement-plan", "automation-spec"),
                ("baseline is evidenced", "target outcome and metrics are explicit"),
                ("process", "systems", "metric", "constraint"),
            ),
            CustomerModuleRecipe(
                "customer-service",
                "Customer Service",
                "Build or operate governed customer-support workflows",
                ("service-workflow", "knowledge-pack", "support-automation"),
                ("service policy is explicit", "escalation and exception paths are defined"),
                ("channels", "sla", "knowledge", "escalation"),
            ),
        )
    )


__all__ = [
    "CustomerModuleCatalog",
    "CustomerModuleOrder",
    "CustomerModuleRecipe",
    "CustomModuleRequirement",
    "ModuleOrderMode",
    "ModuleSelection",
    "ResolvedModuleOrder",
    "default_customer_module_catalog",
]
