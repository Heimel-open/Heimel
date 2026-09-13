"""Deterministic harness for GEOMETRIC-SI-01.

This module tests representational sufficiency only. It has no authority surface and
must not be used as evidence of identity, consciousness, or substrate independence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from random import Random
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


class Ablation(str, Enum):
    FULL = "full"
    GEO = "geo"
    SYMBOLIC = "symbolic"
    RESET = "reset"
    REWIRED = "rewired"


@dataclass(frozen=True)
class Relation:
    source: str
    kind: str
    target: str
    weight: float = 1.0
    provenance: str = ""

    def __post_init__(self) -> None:
        if not self.source or not self.kind or not self.target:
            raise ValueError("relation endpoints and kind must be non-empty")
        if self.weight <= 0.0:
            raise ValueError("relation weight must be positive")


@dataclass
class GeometricState:
    """Minimal typed directed metric graph.

    The graph is the learned geometric representation. Serialization format is not
    the experimental variable; organization of learned state is.
    """

    edges: Dict[Tuple[str, str, str], Relation] = field(default_factory=dict)

    def learn(self, relation: Relation) -> None:
        key = (relation.source, relation.kind, relation.target)
        current = self.edges.get(key)
        if current is None:
            self.edges[key] = relation
        else:
            self.edges[key] = Relation(
                relation.source,
                relation.kind,
                relation.target,
                current.weight + relation.weight,
                relation.provenance or current.provenance,
            )

    def neighbors(self, source: str, kind: str) -> Tuple[str, ...]:
        return tuple(
            sorted(
                r.target
                for r in self.edges.values()
                if r.source == source and r.kind == kind
            )
        )

    def reachable(self, source: str, kind: str, max_hops: int = 4) -> Tuple[str, ...]:
        seen = {source}
        frontier = [source]
        reached: List[str] = []
        for _ in range(max_hops):
            next_frontier: List[str] = []
            for node in frontier:
                for target in self.neighbors(node, kind):
                    if target in seen:
                        continue
                    seen.add(target)
                    reached.append(target)
                    next_frontier.append(target)
            if not next_frontier:
                break
            frontier = next_frontier
        return tuple(reached)

    def strongest_target(self, source: str, kind: str) -> Optional[str]:
        candidates = [
            r for r in self.edges.values() if r.source == source and r.kind == kind
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda r: (r.weight, r.target)).target

    def copy(self) -> "GeometricState":
        return GeometricState(dict(self.edges))

    def rewire(self, seed: int) -> "GeometricState":
        """Preserve relation counts, kinds and weights while destroying arrangement."""
        rng = Random(seed)
        relations = sorted(
            self.edges.values(), key=lambda r: (r.kind, r.source, r.target, r.weight)
        )
        targets = [r.target for r in relations]
        rng.shuffle(targets)
        rewired = GeometricState()
        for relation, target in zip(relations, targets):
            rewired.learn(
                Relation(
                    relation.source,
                    relation.kind,
                    target,
                    relation.weight,
                    relation.provenance,
                )
            )
        return rewired

    def digest(self) -> str:
        payload = "\n".join(
            f"{r.source}|{r.kind}|{r.target}|{r.weight:.6f}|{r.provenance}"
            for r in sorted(
                self.edges.values(), key=lambda r: (r.source, r.kind, r.target)
            )
        )
        return sha256(payload.encode()).hexdigest()


@dataclass
class SymbolicState:
    records: List[Relation] = field(default_factory=list)

    def learn(self, relation: Relation) -> None:
        self.records.append(relation)

    def exact(self, source: str, kind: str) -> Tuple[str, ...]:
        return tuple(
            sorted(r.target for r in self.records if r.source == source and r.kind == kind)
        )

    def reachable(self, source: str, kind: str, max_hops: int = 4) -> Tuple[str, ...]:
        # Give the symbolic control the same compositional opportunity rather than
        # crippling it to exact lookup.
        adjacency: Dict[str, List[str]] = {}
        for r in self.records:
            if r.kind == kind:
                adjacency.setdefault(r.source, []).append(r.target)
        seen = {source}
        frontier = [source]
        reached: List[str] = []
        for _ in range(max_hops):
            next_frontier: List[str] = []
            for node in frontier:
                for target in sorted(adjacency.get(node, ())):
                    if target in seen:
                        continue
                    seen.add(target)
                    reached.append(target)
                    next_frontier.append(target)
            if not next_frontier:
                break
            frontier = next_frontier
        return tuple(reached)

    def strongest_target(self, source: str, kind: str) -> Optional[str]:
        totals: Dict[str, float] = {}
        for r in self.records:
            if r.source == source and r.kind == kind:
                totals[r.target] = totals.get(r.target, 0.0) + r.weight
        if not totals:
            return None
        return max(totals.items(), key=lambda item: (item[1], item[0]))[0]


@dataclass
class AgentState:
    geometry: GeometricState = field(default_factory=GeometricState)
    symbolic: SymbolicState = field(default_factory=SymbolicState)

    def experience(self, relation: Relation) -> None:
        self.geometry.learn(relation)
        self.symbolic.learn(relation)

    def ablate(self, mode: Ablation, seed: int) -> "AgentState":
        geometry = self.geometry.copy()
        symbolic = SymbolicState(list(self.symbolic.records))
        if mode is Ablation.GEO:
            symbolic = SymbolicState()
        elif mode is Ablation.SYMBOLIC:
            geometry = GeometricState()
        elif mode is Ablation.RESET:
            geometry = GeometricState()
            symbolic = SymbolicState()
        elif mode is Ablation.REWIRED:
            geometry = geometry.rewire(seed)
            symbolic = SymbolicState()
        return AgentState(geometry, symbolic)

    def reachable(self, source: str, kind: str) -> Tuple[str, ...]:
        if self.geometry.edges:
            return self.geometry.reachable(source, kind)
        return self.symbolic.reachable(source, kind)

    def strongest_target(self, source: str, kind: str) -> Optional[str]:
        if self.geometry.edges:
            return self.geometry.strongest_target(source, kind)
        return self.symbolic.strongest_target(source, kind)


@dataclass(frozen=True)
class RunMetrics:
    mode: Ablation
    seed: int
    association: float
    composition: float
    choice_consistency: float
    partner_recognition: float

    @property
    def acquired_score(self) -> float:
        return (
            self.association
            + self.composition
            + self.choice_consistency
            + self.partner_recognition
        ) / 4.0


NURSERY: Tuple[Relation, ...] = (
    Relation("alpha", "path", "beta", provenance="event:path-1"),
    Relation("beta", "path", "gamma", provenance="event:path-2"),
    Relation("gamma", "path", "delta", provenance="event:path-3"),
    Relation("signal-a", "means", "safe", provenance="event:assoc-a"),
    Relation("signal-b", "means", "unsafe", provenance="event:assoc-b"),
    Relation("self", "prefers", "explore", 1.0, "event:choice-1"),
    Relation("self", "prefers", "explore", 1.0, "event:choice-2"),
    Relation("self", "prefers", "wait", 0.4, "event:choice-3"),
    Relation("partner-pattern", "partner", "p7", 1.0, "event:partner-1"),
    Relation("partner-pattern", "partner", "p7", 1.0, "event:partner-2"),
    Relation("partner-pattern", "partner", "p3", 0.2, "event:partner-3"),
)


def nursery_state() -> AgentState:
    state = AgentState()
    for relation in NURSERY:
        state.experience(relation)
    return state


def evaluate(mode: Ablation, seed: int = 0) -> RunMetrics:
    state = nursery_state().ablate(mode, seed)
    association = float(state.strongest_target("signal-a", "means") == "safe")
    composition = float("delta" in state.reachable("alpha", "path"))
    choice = float(state.strongest_target("self", "prefers") == "explore")
    partner = float(state.strongest_target("partner-pattern", "partner") == "p7")
    return RunMetrics(mode, seed, association, composition, choice, partner)


def run_experiment(seeds: Iterable[int] = range(20)) -> Mapping[Ablation, Tuple[RunMetrics, ...]]:
    return {
        mode: tuple(evaluate(mode, seed) for seed in seeds)
        for mode in Ablation
    }
