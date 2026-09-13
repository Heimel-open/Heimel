from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts.graph import FunctionGraph
from ..contracts.registry import RegistrySnapshot
from ..registry.store import FunctionRegistry


@dataclass(frozen=True)
class ExplainResult:
    question: str
    reasons: list[str] = field(default_factory=list)
    resolved: bool = False


def explain(
    question: str,
    fgraph: FunctionGraph,
    snapshot: RegistrySnapshot,
    registry: FunctionRegistry,
) -> ExplainResult:
    """Deterministic, structured explanation from state — never LLM-only.

    'Why can PAY not execute?' answers from the function's declared contract:
    missing evidence, missing authority, unmet purpose, effects, risk."""
    reasons: list[str] = []
    for call in fgraph.nodes:
        definition = registry.get(call.function_ref.identity)
        label = definition.name
        if definition.evidence_requirements:
            needed = sorted({t for r in definition.evidence_requirements for t in r.required_types})
            reasons.append(f"{label}: requires evidence {needed}")
        if definition.authority_requirements:
            caps = sorted({a.capability for a in definition.authority_requirements})
            reasons.append(f"{label}: requires authority {caps}")
        if definition.purpose_requirements:
            purposes = sorted({p for r in definition.purpose_requirements for p in r.purpose_types})
            reasons.append(f"{label}: requires purpose {purposes}")
        if definition.idempotency_requirement.value != "NONE":
            reasons.append(f"{label}: requires idempotency {definition.idempotency_requirement.value}")
    resolved = "cannot execute" not in question.lower() or any(
        "requires" in reason for reason in reasons
    )
    return ExplainResult(question=question, reasons=reasons, resolved=resolved)

