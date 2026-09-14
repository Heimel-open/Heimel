from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class RealizationStep:
    name: str
    trust_domain: str
    crosses_boundary: bool = False
    irreversible: bool = False
    evidence: bool = False


@dataclass(frozen=True)
class RealizationWitness:
    witness_id: str
    effect: str
    steps: tuple[RealizationStep, ...]

    @property
    def trust_domains(self) -> frozenset[str]:
        return frozenset(step.trust_domain for step in self.steps)

    @property
    def boundary_crossed(self) -> bool:
        return any(step.crosses_boundary for step in self.steps)

    @property
    def irreversible_steps(self) -> tuple[RealizationStep, ...]:
        return tuple(step for step in self.steps if step.irreversible)

    @property
    def evidence_domains(self) -> frozenset[str]:
        return frozenset(step.trust_domain for step in self.steps if step.evidence)


@dataclass(frozen=True)
class BoundaryControl:
    boundary_id: str
    alter_domains: frozenset[str] = field(default_factory=frozenset)
    satisfy_domains: frozenset[str] = field(default_factory=frozenset)
    disable_domains: frozenset[str] = field(default_factory=frozenset)
    bypass_domains: frozenset[str] = field(default_factory=frozenset)

    @property
    def capture_domains(self) -> frozenset[str]:
        return (
            self.alter_domains
            | self.satisfy_domains
            | self.disable_domains
            | self.bypass_domains
        )


@dataclass(frozen=True)
class AuthorityDecompositionResult:
    effect: str
    witness_count: int
    minimal_coalitions: tuple[frozenset[str], ...]
    witness_bypass: tuple[str, ...]
    boundary_capture_domains: frozenset[str]
    uncovered_commit_points: tuple[str, ...]
    evidence_control_collapse: tuple[str, ...]

    @property
    def no_direct_effect_path(self) -> bool:
        return not self.witness_bypass

    @property
    def no_unilateral_boundary_capture(self) -> bool:
        return not self.boundary_capture_domains

    @property
    def commit_point_coverage(self) -> bool:
        return not self.uncovered_commit_points

    @property
    def evidence_independence(self) -> bool:
        return not self.evidence_control_collapse

    @property
    def passes(self) -> bool:
        return (
            self.no_direct_effect_path
            and self.no_unilateral_boundary_capture
            and self.commit_point_coverage
            and self.evidence_independence
        )


def _minimal_sets(candidates: Iterable[frozenset[str]]) -> tuple[frozenset[str], ...]:
    unique = sorted(set(candidates), key=lambda value: (len(value), tuple(sorted(value))))
    minimal: list[frozenset[str]] = []
    for candidate in unique:
        if any(existing <= candidate for existing in minimal):
            continue
        minimal.append(candidate)
    return tuple(minimal)


def analyze_authority_decomposition(
    *,
    effect: str,
    witnesses: Iterable[RealizationWitness],
    boundary: BoundaryControl,
) -> AuthorityDecompositionResult:
    relevant = tuple(witness for witness in witnesses if witness.effect == effect)
    if not relevant:
        raise ValueError(f"no realization witnesses supplied for effect: {effect}")

    witness_bypass = tuple(
        witness.witness_id for witness in relevant if not witness.boundary_crossed
    )

    minimal_coalitions = _minimal_sets(
        witness.trust_domains for witness in relevant
    )

    # A trust domain that participates in realizing the effect and can independently
    # alter, satisfy, disable, or bypass the boundary can capture the claimed final
    # boundary unilaterally.
    realizing_domains = frozenset().union(*(witness.trust_domains for witness in relevant))
    boundary_capture_domains = realizing_domains & boundary.capture_domains

    uncovered_commit_points: list[str] = []
    for witness in relevant:
        boundary_seen = False
        for step in witness.steps:
            if step.crosses_boundary:
                boundary_seen = True
            if step.irreversible and not boundary_seen:
                uncovered_commit_points.append(f"{witness.witness_id}:{step.name}")

    evidence_control_collapse: list[str] = []
    for witness in relevant:
        execution_domains = frozenset(
            step.trust_domain for step in witness.steps if not step.evidence
        )
        evidence_domains = witness.evidence_domains
        if evidence_domains and evidence_domains <= execution_domains:
            evidence_control_collapse.append(witness.witness_id)

    return AuthorityDecompositionResult(
        effect=effect,
        witness_count=len(relevant),
        minimal_coalitions=minimal_coalitions,
        witness_bypass=witness_bypass,
        boundary_capture_domains=boundary_capture_domains,
        uncovered_commit_points=tuple(uncovered_commit_points),
        evidence_control_collapse=tuple(evidence_control_collapse),
    )
