from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Canonical refinements. These are ORTHOGONAL capabilities, not a strength
# ladder: a value carries a SET of refinements and consumption requires the
# produced set to be a superset of the required set. There is no implicit
# promotion (Authorized<T> is not Verified<T>, Executed<T> is not
# VerifiedEffect<T>). The set covers every refinement that can survive to the
# runtime boundary, including the Function Fabric vocabulary.
REFINEMENTS: frozenset[str] = frozenset(
    {
        "Candidate",
        "Asserted",
        "Inferred",
        "Admitted",
        "Verified",
        "Reserved",
        "Authorized",
        "Confirmed",
        "Executed",
        "VerifiedEffect",
    }
)

# Kept for tooling/introspection; NOT used for promotion.
WRAPPER_LEVELS: dict[str, int] = {name: i for i, name in enumerate(sorted(REFINEMENTS))}


@dataclass(frozen=True)
class WorkflowType:
    """A parsed workflow type.

    A type is a base plus a SET of orthogonal refinements:
      Verified<Evidence>        -> base Evidence, {VERIFIED}
      Evidence{VERIFIED,ADMITTED} -> base Evidence, {VERIFIED, ADMITTED}
      Evidence                  -> base Evidence, {} (raw)
    Refinements are capabilities, not maturity levels. `Verified<T>` is not
    `Authorized<T>`; only a value carrying the required refinement (or a
    superset) can satisfy a refined requirement."""

    base: str
    refinements: frozenset[str] = frozenset()

    def __str__(self) -> str:
        if not self.refinements:
            return self.base
        if len(self.refinements) == 1:
            (refinement,) = self.refinements
            return f"{refinement}<{self.base}>"
        ordered = ",".join(sorted(self.refinements))
        return f"{self.base}{{{ordered}}}"

    @property
    def wrapper(self) -> str | None:
        """Backward-compatible single-wrapper view. None when the type carries
        zero or multiple refinements."""
        if len(self.refinements) == 1:
            (refinement,) = self.refinements
            return refinement
        return None


def _canonical_refinement(name: str) -> str:
    """Case-insensitive canonical form of a refinement name."""
    for known in REFINEMENTS:
        if known.lower() == name.lower():
            return known
    raise ValueError(f"unknown refinement: {name}")


def parse_type(expression: str) -> WorkflowType:
    expr = expression.strip()
    if expr == "any":
        return WorkflowType(base="any")
    if expr.endswith("}") and "{" in expr:
        base, refinements = expr[:-1].split("{", 1)
        refs = frozenset(_canonical_refinement(r.strip()) for r in refinements.split(",") if r.strip())
        return WorkflowType(base=base.strip(), refinements=refs)
    if "<" in expr:
        assert expr.endswith(">"), f"malformed type expression: {expression}"
        wrapper, base = expr.split("<", 1)
        return WorkflowType(base=base[:-1], refinements=frozenset({_canonical_refinement(wrapper.strip())}))
    return WorkflowType(base=expr)


def can_consume(produced: str, required: str) -> bool:
    """Can a value of type `produced` satisfy an input requiring `required`?

    Capability-set semantics: the produced refinement set must be a SUPERSET of
    the required refinement set. Orthogonal — there is no implicit promotion:
      Authorized<T> !-> Verified<T>
      Reserved<T>   !-> Verified<T>
      Confirmed<T>  !-> Authorized<T>
      Verified<T>   !-> Admitted<T>
      Candidate<T>  !-> Verified<T>
    A raw requirement accepts any value of the same base; a raw value can never
    satisfy a refined requirement. A multi-refinement value satisfies any
    single-refinement requirement it carries."""
    produced_t = parse_type(produced)
    required_t = parse_type(required)
    if produced_t.base == "any" or required_t.base == "any":
        return True
    if produced_t.base != required_t.base:
        return False
    if not required_t.refinements:
        return True  # a raw requirement accepts any value of the base type
    if not produced_t.refinements:
        return False  # raw data can never satisfy a refined requirement
    return produced_t.refinements.issuperset(required_t.refinements)


def satisfies_input(outputs: list[Any], required: str) -> bool:
    """True if any declared output type can satisfy the required input type."""
    for output in outputs:
        if can_consume(output.type, required):
            return True
    return False
