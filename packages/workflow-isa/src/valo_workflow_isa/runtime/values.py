from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeValue:
    """A runtime value that provably carries its declared refinements. Only the
    handler that produced the proof (the WRITE boundary that verified the
    effect, or a reconciliation/verification node) may attach refinements such
    as RESERVED, VERIFIED, AUTHORIZED, VERIFIED_EFFECT. The runtime fails
    closed when a produced value does not satisfy the node's declared output
    type."""

    value: Any
    base_type: str
    refinements: frozenset[str] = frozenset()
    evidence_refs: list[str] = field(default_factory=list)
    receipt_refs: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def satisfies(self, base_type: str, refinements: frozenset[str]) -> bool:
        return self.base_type == base_type and self.refinements.issuperset(refinements)
