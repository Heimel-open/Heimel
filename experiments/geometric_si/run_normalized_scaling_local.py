#!/usr/bin/env python3
"""LOCAL EXECUTION REQUIRED — GEOMETRIC-SI-03.

Symmetric normalization + symmetric indexing control for GEO vs SYMBOLIC.
GitHub is source/review/evidence storage only; scientific execution is local.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from paios.geometric_si import Relation


@dataclass(frozen=True)
class NormalizedFact:
    source: str
    kind: str
    target: str
    weight: float
    provenance_count: int


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def generate_events(scale: int, seed: int) -> Tuple[List[Relation], Mapping[str, str]]:
    if scale < 16:
        raise ValueError("scale must be at least 16")

    events: List[Relation] = [
        Relation("alpha", "path", "beta", provenance=f"s{seed}:path-1"),
        Relation("beta", "path", "gamma", provenance=f"s{seed}:path-2"),
        Relation("gamma", "path", "delta", provenance=f"s{seed}:path-3"),
        Relation("signal-a", "means", "safe", provenance=f"s{seed}:assoc-a"),
        Relation("signal-b", "means", "unsafe", provenance=f"s{seed}:assoc-b"),
        Relation("self", "prefers", "explore", 1.0, f"s{seed}:choice-1"),
        Relation("self", "prefers", "explore", 1.0, f"s{seed}:choice-2"),
        Relation("self", "prefers", "wait", 0.4, f"s{seed}:choice-3"),
        Relation("partner-pattern", "partner", "p7", 1.0, f"s{seed}:partner-1"),
        Relation("partner-pattern", "partner", "p7", 1.0, f"s{seed}:partner-2"),
        Relation("partner-pattern", "partner", "p3", 0.2, f"s{seed}:partner-3"),
    ]

    # Add deterministic unique distractors until normalized relation count reaches scale.
    # Repeated task observations above intentionally test symmetric normalization.
    base_unique = len({(r.source, r.kind, r.target) for r in events})
    needed = scale - base_unique
    for i in range(needed):
        src = f"d{seed}-{i:05d}"
        tgt = f"v{seed}-{i:05d}"
        kind = f"k{i % 7}"
        events.append(Relation(src, kind, tgt, 1.0 + ((i + seed) % 5) * 0.1, f"s{seed}:d{i}"))

    answers = {
        "association": "safe",
        "composition": "delta",
        "choice_consistency": "explore",
        "partner_recognition": "p7",
    }
    return events, answers


def normalize(events: Iterable[Relation]) -> Tuple[NormalizedFact, ...]:
    totals: Dict[Tuple[str, str, str], float] = defaultdict(float)
    provenance_counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
    for r in events:
        key = (r.source, r.kind, r.target)
        totals[key] += r.weight
        provenance_counts[key] += 1
    return tuple(
        NormalizedFact(source, kind, target, totals[(source, kind, target)], provenance_counts[(source, kind, target)])
        for source, kind, target in sorted(totals)
    )


class IndexedBase:
    def __init__(self, facts: Sequence[NormalizedFact]):
        self.facts = tuple(facts)
        self.by_source_kind: Dict[Tuple[str, str], Tuple[NormalizedFact, ...]] = {}
        groups: Dict[Tuple[str, str], List[NormalizedFact]] = defaultdict(list)
        for fact in self.facts:
            groups[(fact.source, fact.kind)].append(fact)
        for key, vals in groups.items():
            self.by_source_kind[key] = tuple(sorted(vals, key=lambda f: f.target))

    def strongest_target(self, source: str, kind: str) -> str | None:
        candidates = self.by_source_kind.get((source, kind), ())
        if not candidates:
            return None
        return max(candidates, key=lambda f: (f.weight, f.target)).target

    def reachable(self, source: str, kind: str, max_hops: int = 4) -> Tuple[str, ...]:
        seen = {source}
        frontier = [source]
        reached: List[str] = []
        for _ in range(max_hops):
            next_frontier: List[str] = []
            for node in frontier:
                for fact in self.by_source_kind.get((node, kind), ()):
                    if fact.target in seen:
                        continue
                    seen.add(fact.target)
                    reached.append(fact.target)
                    next_frontier.append(fact.target)
            if not next_frontier:
                break
            frontier = next_frontier
        return tuple(reached)

    def logical_ops(self) -> int:
        # Symmetric indexed accounting: one bucket lookup per strongest-target task
        # plus one lookup per visited path node in the fixed four-task bundle.
        return 3 + 4


class NormalizedGeo(IndexedBase):
    def serialize(self) -> bytes:
        # Geometric layout: compact edge tuples under a single edge array.
        payload = {
            "edges": [[f.source, f.kind, f.target, f.weight, f.provenance_count] for f in self.facts]
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


class NormalizedSymbolic(IndexedBase):
    def serialize(self) -> bytes:
        # Symbolic layout: named fields, but exactly the same normalized facts.
        payload = {
            "facts": [
                {
                    "source": f.source,
                    "kind": f.kind,
                    "target": f.target,
                    "weight": f.weight,
                    "provenance_count": f.provenance_count,
                }
                for f in self.facts
            ]
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def load_geo(blob: bytes) -> NormalizedGeo:
    obj = json.loads(blob)
    facts = tuple(NormalizedFact(*row) for row in obj["edges"])
    return NormalizedGeo(facts)


def load_symbolic(blob: bytes) -> NormalizedSymbolic:
    obj = json.loads(blob)
    facts = tuple(NormalizedFact(**row) for row in obj["facts"])
    return NormalizedSymbolic(facts)


def score(state: IndexedBase, answers: Mapping[str, str]) -> Mapping[str, float]:
    metrics = {
        "association": float(state.strongest_target("signal-a", "means") == answers["association"]),
        "composition": float(answers["composition"] in state.reachable("alpha", "path")),
        "choice_consistency": float(state.strongest_target("self", "prefers") == answers["choice_consistency"]),
        "partner_recognition": float(state.strongest_target("partner-pattern", "partner") == answers["partner_recognition"]),
    }
    metrics["acquired_score"] = mean(metrics.values())
    return metrics


def timed_queries(state: IndexedBase, repetitions: int) -> float:
    start = time.perf_counter_ns()
    for _ in range(repetitions):
        state.strongest_target("signal-a", "means")
        state.reachable("alpha", "path")
        state.strongest_target("self", "prefers")
        state.strongest_target("partner-pattern", "partner")
    return (time.perf_counter_ns() - start) / repetitions


def timed_load(loader, blob: bytes, repetitions: int) -> float:
    start = time.perf_counter_ns()
    for _ in range(repetitions):
        loader(blob)
    return (time.perf_counter_ns() - start) / repetitions


def one_run(scale: int, seed: int, repetitions: int, load_repetitions: int) -> Mapping[str, object]:
    events, answers = generate_events(scale, seed)
    facts = normalize(events)
    if len(facts) != scale:
        raise AssertionError(f"normalized fact count {len(facts)} != requested scale {scale}")

    geo = NormalizedGeo(facts)
    symbolic = NormalizedSymbolic(facts)
    geo_blob = geo.serialize()
    symbolic_blob = symbolic.serialize()

    return {
        "scale": scale,
        "seed": seed,
        "event_count": len(events),
        "normalized_relation_count": len(facts),
        "geo": {
            "score": score(geo, answers),
            "serialized_state_bytes": len(geo_blob),
            "logical_query_operations": geo.logical_ops(),
            "query_ns_per_four_task_bundle": timed_queries(geo, repetitions),
            "load_and_index_ns": timed_load(load_geo, geo_blob, load_repetitions),
        },
        "symbolic": {
            "score": score(symbolic, answers),
            "serialized_state_bytes": len(symbolic_blob),
            "logical_query_operations": symbolic.logical_ops(),
            "query_ns_per_four_task_bundle": timed_queries(symbolic, repetitions),
            "load_and_index_ns": timed_load(load_symbolic, symbolic_blob, load_repetitions),
        },
    }


def summarize(runs: Sequence[Mapping[str, object]], scales: Sequence[int], tolerance: float) -> Mapping[str, object]:
    out: Dict[str, object] = {}
    for scale in scales:
        group = [r for r in runs if r["scale"] == scale]
        geo_scores = [r["geo"]["score"]["acquired_score"] for r in group]
        sym_scores = [r["symbolic"]["score"]["acquired_score"] for r in group]
        geo_mean = mean(geo_scores)
        sym_mean = mean(sym_scores)
        delta = abs(geo_mean - sym_mean)

        def avg(side: str, key: str) -> float:
            return mean(r[side][key] for r in group)

        geo_cost = {
            "serialized_state_bytes": avg("geo", "serialized_state_bytes"),
            "logical_query_operations": avg("geo", "logical_query_operations"),
            "query_ns_per_four_task_bundle": avg("geo", "query_ns_per_four_task_bundle"),
            "load_and_index_ns": avg("geo", "load_and_index_ns"),
        }
        sym_cost = {
            "serialized_state_bytes": avg("symbolic", "serialized_state_bytes"),
            "logical_query_operations": avg("symbolic", "logical_query_operations"),
            "query_ns_per_four_task_bundle": avg("symbolic", "query_ns_per_four_task_bundle"),
            "load_and_index_ns": avg("symbolic", "load_and_index_ns"),
        }
        ratios = {k: geo_cost[k] / sym_cost[k] for k in geo_cost}
        out[str(scale)] = {
            "performance": {
                "geo_mean": geo_mean,
                "symbolic_mean": sym_mean,
                "absolute_delta": delta,
                "tolerance": tolerance,
                "equivalent": delta <= tolerance,
            },
            "cost_means": {"geo": geo_cost, "symbolic": sym_cost, "geo_over_symbolic": ratios},
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--scales", type=int, nargs="+", default=[32, 128, 512, 2048])
    parser.add_argument("--repetitions", type=int, default=5000)
    parser.add_argument("--load-repetitions", type=int, default=500)
    parser.add_argument("--performance-tolerance", type=float, default=0.0)
    parser.add_argument("--out", default="experiments/geometric_si/results/GEOMETRIC-SI-03.json")
    args = parser.parse_args()

    if args.seeds <= 0 or args.repetitions <= 0 or args.load_repetitions <= 0:
        raise SystemExit("seeds/repetitions/load-repetitions must be positive")
    if args.performance_tolerance < 0:
        raise SystemExit("performance tolerance must be non-negative")
    if any(scale < 16 for scale in args.scales):
        raise SystemExit("all scales must be >= 16")

    started = time.time()
    runs = [
        one_run(scale, seed, args.repetitions, args.load_repetitions)
        for scale in args.scales
        for seed in range(args.seeds)
    ]

    evidence = {
        "experiment": "GEOMETRIC-SI-03",
        "execution_requirement": "LOCAL EXECUTION REQUIRED",
        "git_head": git_head(),
        "parameters": {
            "seeds": list(range(args.seeds)),
            "scales": args.scales,
            "query_repetitions_per_seed_scale": args.repetitions,
            "load_repetitions_per_seed_scale": args.load_repetitions,
            "performance_tolerance": args.performance_tolerance,
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "elapsed_seconds": time.time() - started,
        "summary": summarize(runs, args.scales, args.performance_tolerance),
        "runs": runs,
        "interpretation_constraints": [
            "Cost comparison is admissible only at scales with performance equivalence.",
            "Both representations receive identical semantic normalization and adjacency indexing.",
            "Serialized-byte differences include representation layout and are not alone evidence of geometry.",
            "Wall-clock timing is local-runtime evidence and requires replication before hardware-general claims.",
            "No result establishes that SI is fundamentally geometric.",
        ],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(out)


if __name__ == "__main__":
    main()
