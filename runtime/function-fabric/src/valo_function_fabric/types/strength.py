from __future__ import annotations

from dataclasses import dataclass

# Function Fabric type vocabulary. Refinements are ORTHOGONAL capabilities, not
# a strength ladder: a type is a base plus a SET of refinements, and consumption
# requires the produced set to be a SUPERSET of the required set.
#   Raw (empty) < Candidate, Asserted, Inferred, Admitted, Verified, Reserved,
#   Confirmed, Authorized, Executed, VerifiedEffect
# There is no implicit promotion (Authorized<T> is not Verified<T>; Executed is
# not VerifiedEffect; Inferred is not Confirmed).
REFINEMENTS: frozenset[str] = frozenset(
    {
        "Candidate",
        "Asserted",
        "Inferred",
        "Admitted",
        "Verified",
        "Reserved",
        "Confirmed",
        "Authorized",
        "Executed",
        "VerifiedEffect",
    }
)

# The subset of refinements the Workflow ISA contract can carry directly. The
# ISA contract now carries the full runtime vocabulary (Candidate, Asserted,
# Inferred, Admitted, Verified, Reserved, Authorized, Confirmed, Executed,
# VerifiedEffect), so every Function Fabric refinement lowers losslessly.
ISA_REFINEMENTS: frozenset[str] = frozenset(
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


class TypeExpressionError(ValueError):
    """Malformed or unsupported Function Fabric type expression."""


@dataclass(frozen=True)
class FabricType:
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
    def single(self) -> str | None:
        if len(self.refinements) == 1:
            (refinement,) = self.refinements
            return refinement
        return None


def _canonical(name: str) -> str:
    for known in REFINEMENTS:
        if known.lower() == name.strip().lower():
            return known
    raise TypeExpressionError(f"unknown refinement: {name}")


def parse_type(expression: str) -> FabricType:
    expr = expression.strip()
    if not expr:
        raise TypeExpressionError("empty type expression")
    if expr == "any":
        return FabricType(base="any")
    if expr.endswith("}") and "{" in expr:
        base, refinements = expr[:-1].split("{", 1)
        if not base.strip():
            raise TypeExpressionError(f"missing base type: {expression}")
        refs = frozenset(_canonical(r) for r in refinements.split(",") if r.strip())
        return FabricType(base=base.strip(), refinements=refs)
    if "<" in expr:
        if not expr.endswith(">"):
            raise TypeExpressionError(f"malformed type expression: {expression}")
        wrapper, base = expr.split("<", 1)
        wrapper = wrapper.strip()
        if wrapper in REFINEMENTS:
            if not base[:-1].strip():
                raise TypeExpressionError(f"missing base type: {expression}")
            return FabricType(base=base[:-1], refinements=frozenset({wrapper}))
        # Not a canonical refinement: a domain type constructor such as
        # CandidateSet<Resource> or Calculated<Price> is an opaque atomic type.
        return FabricType(base=expr)
    return FabricType(base=expr)


def validate_type_expression(expression: str) -> tuple[str, frozenset[str]]:
    t = parse_type(expression)
    return t.base, t.refinements


def can_consume(produced: str, required: str) -> bool:
    """Capability-set semantics: produced.refinements must be a superset of
    required.refinements. No implicit promotion in either direction.

    `any` is a wide-open wildcard ONLY as a raw type (no refinements): it
    accepts anything and is accepted by anything (opaque constructors lower to
    it). A REFINED type such as ``Inferred<any>`` is NOT the wildcard — it is a
    concrete base literally named "any", and must satisfy the same base/refined
    rules. Treating refined ``any`` as a wildcard broke transitivity
    (Inferred<0> >= Inferred<any> >= Inferred<00> was spuriously allowed)."""
    produced_t = parse_type(produced)
    required_t = parse_type(required)
    if not produced_t.refinements and produced_t.base == "any":
        return True
    if not required_t.refinements and required_t.base == "any":
        return True
    if produced_t.base != required_t.base:
        return False
    if not required_t.refinements:
        return True  # a raw requirement accepts any value of the base type
    if not produced_t.refinements:
        return False  # raw data never satisfies a refined requirement
    return produced_t.refinements.issuperset(required_t.refinements)


def workflow_type(expression: str) -> str:
    """Lower a Function Fabric type to a Workflow ISA node type LOSSLESSLY.

    The Workflow ISA contract carries the full runtime refinement vocabulary
    (Asserted, Inferred, Admitted, Verified, Reserved, Authorized, Confirmed,
    Executed, VerifiedEffect) with capability-set semantics, so every
    governance refinement lowers losslessly — never projected to a single
    refinement, never downgraded to 'any'. Examples:
      VerifiedEffect<Payment>            -> VerifiedEffect<Payment>
      Evidence{Verified,Admitted}        -> Evidence{Verified,Admitted}
      Candidate<Resource>                -> Candidate<Resource>
    Only opaque domain constructors (e.g. CandidateSet<Resource>,
    Calculated<Price>) that carry no governance refinement and that the ISA
    contract cannot express lower to 'any' — the real type is enforced by FF's
    own typechecker."""
    t = parse_type(expression)
    if t.refinements:
        ordered = ",".join(sorted(t.refinements))
        if len(t.refinements) == 1:
            (refinement,) = t.refinements
            return f"{refinement}<{t.base}>"
        return f"{t.base}{{{ordered}}}"
    if "<" in t.base or "{" in t.base:
        return "any"
    return t.base
