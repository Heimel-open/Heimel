"""Deterministic instrumentation for TS-1 and TS-4.

Scope: operational/system-level relational time and reachability only.
This module does not model or make claims about physical spacetime.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import hashlib
import heapq
import math
from typing import FrozenSet, Tuple


LOCAL_COMPUTE_RULE = "synchronous-frontier-propagation-v1"
Edge = Tuple[str, str, float]


@dataclass(frozen=True)
class RelationalState:
    """Measured relational/boundary state X_k for the synthetic harness."""

    nodes: Tuple[str, ...]
    edges: Tuple[Edge, ...]
    informed: FrozenSet[str] = frozenset()
    version: int = 0

    def __post_init__(self) -> None:
        if len(set(self.nodes)) != len(self.nodes):
            raise ValueError("nodes must be unique")
        known = set(self.nodes)
        seen_pairs: set[tuple[str, str]] = set()
        for source, target, cost in self.edges:
            if source not in known or target not in known:
                raise ValueError("edges must reference declared nodes")
            if source == target:
                raise ValueError("self-edges are excluded from this harness")
            if cost <= 0 or not math.isfinite(cost):
                raise ValueError("edge cost must be finite and > 0")
            pair = (source, target)
            if pair in seen_pairs:
                raise ValueError("parallel duplicate edges are excluded")
            seen_pairs.add(pair)
        if not self.informed.issubset(known):
            raise ValueError("informed nodes must be declared nodes")
        if self.version < 0:
            raise ValueError("version must be >= 0")

    def adjacency(self) -> dict[str, tuple[tuple[str, float], ...]]:
        outgoing: dict[str, list[tuple[str, float]]] = {node: [] for node in self.nodes}
        for source, target, cost in self.edges:
            outgoing[source].append((target, cost))
        return {
            node: tuple(sorted(neighbours, key=lambda item: (item[0], item[1])))
            for node, neighbours in outgoing.items()
        }

    def geometry_fingerprint(self) -> str:
        payload = "|".join(
            f"{source}>{target}:{cost:.12g}" for source, target, cost in sorted(self.edges)
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def trajectory_fingerprint(self) -> str:
        payload = (
            self.geometry_fingerprint()
            + "|"
            + ",".join(sorted(self.informed))
            + f"|v={self.version}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScheduleRun:
    """The same causal trace embedded in one wall-clock schedule."""

    trace: Tuple[RelationalState, ...]
    event_times: Tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.trace) != len(self.event_times):
            raise ValueError("one wall-clock time is required per causal state")
        if not self.trace:
            raise ValueError("trace must not be empty")
        if self.event_times[0] != 0:
            raise ValueError("first event time must be 0")
        if any(
            right <= left
            for left, right in zip(self.event_times, self.event_times[1:])
        ):
            raise ValueError("event times must be strictly increasing")

    def state_at(self, wall_time: float) -> RelationalState:
        index = bisect_right(self.event_times, wall_time) - 1
        if index < 0:
            raise ValueError("wall_time precedes the initial state")
        return self.trace[index]


def compute_rule_hash() -> str:
    return hashlib.sha256(LOCAL_COMPUTE_RULE.encode("utf-8")).hexdigest()


def geometry_distance(state: RelationalState, source: str, target: str) -> float:
    """Weighted directed shortest-path distance derived only from geometry(X_k)."""

    if source not in state.nodes or target not in state.nodes:
        raise ValueError("source and target must be declared nodes")
    if source == target:
        return 0.0

    distances = {source: 0.0}
    queue: list[tuple[float, str]] = [(0.0, source)]
    adjacency = state.adjacency()

    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances[node]:
            continue
        if node == target:
            return distance
        for neighbour, edge_cost in adjacency[node]:
            candidate = distance + edge_cost
            if candidate < distances.get(neighbour, math.inf):
                distances[neighbour] = candidate
                heapq.heappush(queue, (candidate, neighbour))
    return math.inf


def causal_trace(
    state: RelationalState, source: str, target: str
) -> Tuple[RelationalState, ...]:
    """Apply the fixed local rule and return ordered X_k updates.

    Every local node uses the same rule. One causal update propagates the
    signal across all currently admissible outgoing relations from the
    current frontier. Wall-clock duration is deliberately absent.
    """

    if source not in state.nodes or target not in state.nodes:
        raise ValueError("source and target must be declared nodes")

    current = RelationalState(
        nodes=state.nodes,
        edges=state.edges,
        informed=frozenset({source}),
        version=0,
    )
    trace = [current]
    frontier = {source}
    adjacency = current.adjacency()

    while target not in current.informed and frontier:
        next_frontier: set[str] = set()
        for node in sorted(frontier):
            for neighbour, _edge_cost in adjacency[node]:
                if neighbour not in current.informed:
                    next_frontier.add(neighbour)

        if not next_frontier:
            break

        current = RelationalState(
            nodes=current.nodes,
            edges=current.edges,
            informed=current.informed | frozenset(next_frontier),
            version=current.version + 1,
        )
        trace.append(current)
        frontier = next_frontier

    return tuple(trace)


def relational_time_to_target(
    state: RelationalState, source: str, target: str
) -> float:
    """Operational t_rel: causal X_k updates required for target reachability."""

    trace = causal_trace(state, source, target)
    if target not in trace[-1].informed:
        return math.inf
    return float(trace[-1].version)


def jaccard(left: FrozenSet[str], right: FrozenSet[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def relational_alignment(left: ScheduleRun, right: ScheduleRun) -> float:
    """Alignment when both runs are indexed by ordered relational updates."""

    if len(left.trace) != len(right.trace):
        return 0.0
    return sum(
        jaccard(a.informed, b.informed) for a, b in zip(left.trace, right.trace)
    ) / len(left.trace)


def wall_clock_alignment(left: ScheduleRun, right: ScheduleRun) -> float:
    """Alignment when the same runs are indexed by elapsed wall-clock time."""

    probes = tuple(sorted(set(left.event_times) | set(right.event_times)))
    return sum(
        jaccard(left.state_at(t).informed, right.state_at(t).informed)
        for t in probes
    ) / len(probes)


def baseline_state() -> RelationalState:
    """Five fixed-compute nodes with one relational shortcut."""

    return RelationalState(
        nodes=("A", "B", "C", "D", "E"),
        edges=(
            ("A", "B", 1.0),
            ("B", "C", 1.0),
            ("C", "D", 1.0),
            ("D", "E", 1.0),
            ("B", "D", 1.0),
        ),
    )


def remove_relation(
    state: RelationalState, source: str, target: str
) -> RelationalState:
    remaining = tuple(
        edge for edge in state.edges if (edge[0], edge[1]) != (source, target)
    )
    if len(remaining) == len(state.edges):
        raise ValueError("relation does not exist")
    return RelationalState(nodes=state.nodes, edges=remaining)


def add_relation(
    state: RelationalState, source: str, target: str, cost: float = 1.0
) -> RelationalState:
    return RelationalState(nodes=state.nodes, edges=state.edges + ((source, target, cost),))


def run_ts1() -> dict[str, object]:
    """TS-1 schedule perturbation using the exact same causal state trace."""

    state = baseline_state()
    trace = causal_trace(state, "A", "E")
    regular = ScheduleRun(trace=trace, event_times=(0.0, 1.0, 2.0, 3.0))
    perturbed = ScheduleRun(trace=trace, event_times=(0.0, 3.0, 4.0, 8.0))

    rel_alignment = relational_alignment(regular, perturbed)
    wall_alignment = wall_clock_alignment(regular, perturbed)

    return {
        "test": "TS-1",
        "relational_alignment": rel_alignment,
        "wall_clock_alignment": wall_alignment,
        "same_causal_trace": tuple(s.trajectory_fingerprint() for s in regular.trace)
        == tuple(s.trajectory_fingerprint() for s in perturbed.trace),
        "pass": rel_alignment == 1.0 and wall_alignment < 0.8,
    }


def _projection_pair(state: RelationalState) -> tuple[float, float]:
    return (
        relational_time_to_target(state, "A", "E"),
        geometry_distance(state, "A", "E"),
    )


def run_ts4() -> dict[str, object]:
    """TS-4 intervention and negative control on one measured X_k substrate."""

    baseline = baseline_state()
    bridge_removed = remove_relation(baseline, "B", "D")
    irrelevant_added = add_relation(baseline, "E", "A")

    base_time, base_space = _projection_pair(baseline)
    bridge_time, bridge_space = _projection_pair(bridge_removed)
    control_time, control_space = _projection_pair(irrelevant_added)

    bridge_delta_time = bridge_time - base_time
    bridge_delta_space = bridge_space - base_space
    control_delta_time = control_time - base_time
    control_delta_space = control_space - base_space

    fixed_compute = compute_rule_hash()

    coordinated_bridge_effect = (
        bridge_delta_time > 0
        and bridge_delta_space > 0
        and math.copysign(1.0, bridge_delta_time)
        == math.copysign(1.0, bridge_delta_space)
    )
    clean_negative_control = control_delta_time == 0 and control_delta_space == 0

    return {
        "test": "TS-4",
        "compute_rule_hash": fixed_compute,
        "node_count": len(baseline.nodes),
        "baseline": {"t_rel": base_time, "space": base_space},
        "bridge_removed": {
            "t_rel": bridge_time,
            "space": bridge_space,
            "delta_t_rel": bridge_delta_time,
            "delta_space": bridge_delta_space,
        },
        "irrelevant_relation_control": {
            "t_rel": control_time,
            "space": control_space,
            "delta_t_rel": control_delta_time,
            "delta_space": control_delta_space,
        },
        "coordinated_bridge_effect": coordinated_bridge_effect,
        "clean_negative_control": clean_negative_control,
        "pass": coordinated_bridge_effect and clean_negative_control,
    }


def run_all() -> dict[str, dict[str, object]]:
    return {"TS-1": run_ts1(), "TS-4": run_ts4()}


if __name__ == "__main__":
    import json

    print(json.dumps(run_all(), indent=2, sort_keys=True))
