"""Winner-stability audit for result-to-claim evaluation.

Keeps source, rerun, metric, budget, and mechanism dimensions separate.
A claim is stable only when all supplied non-mechanism dimensions preserve the
reported winner. Mechanism evidence is never inferred from rank stability.
"""
from dataclasses import dataclass, field
from typing import Mapping, Sequence


@dataclass(frozen=True)
class AuditResult:
    reported_winner: str
    stable: bool
    classification: str
    changed_dimensions: tuple[str, ...] = field(default_factory=tuple)
    mechanism_identifiable: bool = False


def audit_winner_stability(
    reported_winner: str,
    *,
    source_winners: Sequence[str] = (),
    rerun_winners: Sequence[str] = (),
    metric_winners: Mapping[str, str] | None = None,
    budget_winners: Mapping[str, str] | None = None,
    mechanism_evidence: bool = False,
) -> AuditResult:
    """Audit whether a reported winner survives supplied evidence dimensions.

    Empty dimensions are UNKNOWN, not PASS. They do not create a failure, but
    prevent an unconditional STABLE classification.
    """
    dimensions = {
        "source": tuple(source_winners),
        "rerun": tuple(rerun_winners),
        "metric": tuple((metric_winners or {}).values()),
        "budget": tuple((budget_winners or {}).values()),
    }
    changed = tuple(
        name
        for name, winners in dimensions.items()
        if winners and any(w != reported_winner for w in winners)
    )
    supplied = tuple(name for name, winners in dimensions.items() if winners)

    if changed:
        classification = "CONDITIONAL_OR_UNSTABLE"
        stable = False
    elif len(supplied) == len(dimensions):
        classification = "STABLE_ACROSS_TESTED_DIMENSIONS"
        stable = True
    else:
        classification = "INSUFFICIENT_STABILITY_EVIDENCE"
        stable = False

    return AuditResult(
        reported_winner=reported_winner,
        stable=stable,
        classification=classification,
        changed_dimensions=changed,
        mechanism_identifiable=bool(mechanism_evidence),
    )
