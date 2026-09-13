"""Minimal capability compiler demonstrator.

Given an outcome and a set of candidate resources, identify the smallest
composition that can realize the outcome, certify the composition, and
ablate each dependency to show whether capability disappears.

This module is intentionally domain-agnostic. It does not infer authority;
it only evaluates capability realization. Any real-world effect must still
pass through the governed effect path.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Iterable, Sequence, Tuple


@dataclass(frozen=True)
class Resource:
    resource_id: str
    kind: str
    cost: float

    def __post_init__(self) -> None:
        if not self.resource_id:
            raise ValueError("resource_id is required")
        if self.cost < 0:
            raise ValueError("cost must be non-negative")


@dataclass(frozen=True)
class Outcome:
    outcome_id: str
    description: str

    def __post_init__(self) -> None:
        if not self.outcome_id:
            raise ValueError("outcome_id is required")


@dataclass(frozen=True)
class AblationResult:
    removed_resource_id: str
    still_realized: bool


@dataclass(frozen=True)
class CapabilityCertificate:
    outcome_id: str
    resource_ids: Tuple[str, ...]
    total_cost: float
    realized: bool
    minimal: bool
    ablations: Tuple[AblationResult, ...]

    @property
    def necessary_resource_ids(self) -> Tuple[str, ...]:
        return tuple(
            item.removed_resource_id
            for item in self.ablations
            if not item.still_realized
        )


Evaluator = Callable[[Outcome, Tuple[Resource, ...]], bool]


class CapabilityCompiler:
    """Search minimal capability-bearing resource compositions."""

    def __init__(self, evaluator: Evaluator) -> None:
        self._evaluator = evaluator

    def compile(
        self,
        outcome: Outcome,
        resources: Sequence[Resource],
    ) -> CapabilityCertificate:
        candidates = tuple(resources)
        if not candidates:
            raise ValueError("at least one resource is required")

        # Search by cardinality first, then cost, then stable resource id order.
        for size in range(1, len(candidates) + 1):
            valid = []
            for combo in combinations(candidates, size):
                if self._evaluator(outcome, combo):
                    valid.append(combo)
            if valid:
                winner = min(
                    valid,
                    key=lambda combo: (
                        sum(item.cost for item in combo),
                        tuple(item.resource_id for item in combo),
                    ),
                )
                return self._certificate(outcome, winner)

        return CapabilityCertificate(
            outcome_id=outcome.outcome_id,
            resource_ids=(),
            total_cost=0.0,
            realized=False,
            minimal=False,
            ablations=(),
        )

    def _certificate(
        self,
        outcome: Outcome,
        composition: Tuple[Resource, ...],
    ) -> CapabilityCertificate:
        ablations = []
        for removed in composition:
            reduced = tuple(item for item in composition if item != removed)
            ablations.append(
                AblationResult(
                    removed_resource_id=removed.resource_id,
                    still_realized=self._evaluator(outcome, reduced),
                )
            )

        return CapabilityCertificate(
            outcome_id=outcome.outcome_id,
            resource_ids=tuple(item.resource_id for item in composition),
            total_cost=sum(item.cost for item in composition),
            realized=True,
            minimal=all(not item.still_realized for item in ablations),
            ablations=tuple(ablations),
        )


def invoice_demo_evaluator(
    outcome: Outcome,
    composition: Tuple[Resource, ...],
) -> bool:
    """Deterministic finance-ops demo evaluator.

    The invoice outcome requires three distinct functions:
    extraction, policy validation, and posting. No individual component is
    sufficient. Alternative resources can satisfy each function, allowing
    the compiler to choose the lowest-cost minimal composition.
    """

    if outcome.outcome_id != "invoice-ready-to-post":
        return False

    capabilities = {item.kind for item in composition}
    required = {"extract", "validate", "post"}
    return required.issubset(capabilities)


def demo_resources() -> Tuple[Resource, ...]:
    return (
        Resource("ocr-premium", "extract", 0.18),
        Resource("ocr-local", "extract", 0.03),
        Resource("policy-agent", "validate", 0.08),
        Resource("erp-connector", "post", 0.04),
        Resource("human-reviewer", "validate", 1.20),
    )


def run_invoice_demo() -> CapabilityCertificate:
    compiler = CapabilityCompiler(invoice_demo_evaluator)
    outcome = Outcome(
        "invoice-ready-to-post",
        "Extract invoice fields, validate them against policy, and prepare ERP posting.",
    )
    return compiler.compile(outcome, demo_resources())
