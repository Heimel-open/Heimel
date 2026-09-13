#!/usr/bin/env python3
"""LOCAL EXECUTION REQUIRED — GEOMETRIC-SI-04.

Encoding-neutral control for GEO vs SYMBOLIC organization.
GitHub is source/review/evidence storage only; scientific execution is local.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import struct
import subprocess
import time
import tracemalloc
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from paios.geometric_si import Relation

RECORD = struct.Struct("!III d I")


@dataclass(frozen=True)
class Fact:
    source: int
    kind: int
    target: int
    weight: float
    provenance_count: int


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def generate_events(scale: int, seed: int) -> Tuple[List[Relation], Mapping[str, str]]:
    if scale < 16:
        raise ValueError("scale must be at least 16")
    events = [
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
    base_unique = len({(r.source, r.kind, r.target) for r in events})
    for i in range(scale - base_unique):
        events.append(Relation(
            f"d{seed}-{i:05d}", f"k{i % 7}", f"v{seed}-{i:05d}",
            1.0 + ((i + seed) % 5) * 0.1, f"s{seed}:d{i}"
        ))
    answers = {
        "association": "safe",
        "composition": "delta",
        "choice_consistency": "explore",
        "partner_recognition": "p7",
    }
    return events, answers


def normalize(events: Iterable[Relation]) -> Tuple[Tuple[str, str, str, float, int], ...]:
    totals: Dict[Tuple[str, str, str], float] = defaultdict(float)
    counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
    for r in events:
        key = (r.source, r.kind, r.target)
        totals[key] += r.weight
        counts[key] += 1
    return tuple((s, k, t, totals[(s, k, t)], counts[(s, k, t)]) for s, k, t in sorted(totals))


def encode_shared(rows: Sequence[Tuple[str, str, str, float, int]]) -> Tuple[bytes, Dict[str, int], Tuple[str, ...]]:
    symbols = tuple(sorted({x for row in rows for x in row[:3]}))
    ids = {s: i for i, s in enumerate(symbols)}
    header = json.dumps(symbols, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = bytearray(struct.pack("!I", len(header)))
    payload.extend(header)
    payload.extend(struct.pack("!I", len(rows)))
    for s, k, t, w, p in rows:
        payload.extend(RECORD.pack(ids[s], ids[k], ids[t], float(w), int(p)))
    return bytes(payload), ids, symbols


def decode_shared(blob: bytes) -> Tuple[Tuple[str, ...], Tuple[Fact, ...]]:
    offset = 0
    (header_len,) = struct.unpack_from("!I", blob, offset); offset += 4
    symbols = tuple(json.loads(blob[offset:offset + header_len])); offset += header_len
    (count,) = struct.unpack_from("!I", blob, offset); offset += 4
    facts = []
    for _ in range(count):
        facts.append(Fact(*RECORD.unpack_from(blob, offset)))
        offset += RECORD.size
    if offset != len(blob):
        raise ValueError("trailing bytes in packed source")
    return symbols, tuple(facts)


class PackedGeo:
    def __init__(self, facts: Sequence[Fact]):
        self.edges: Dict[Tuple[int, int, int], List[float | int]] = {}
        self.adj: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        for f in facts:
            self.edges[(f.source, f.kind, f.target)] = [f.weight, f.provenance_count]
            self.adj[(f.source, f.kind)].append(f.target)
        for key in self.adj:
            self.adj[key].sort()

    def strongest_target(self, source: int, kind: int) -> int | None:
        targets = self.adj.get((source, kind), ())
        if not targets:
            return None
        return max(targets, key=lambda t: (self.edges[(source, kind, t)][0], t))

    def reachable(self, source: int, kind: int, max_hops: int = 4) -> Tuple[int, ...]:
        seen = {source}; frontier = [source]; reached = []
        for _ in range(max_hops):
            nxt = []
            for node in frontier:
                for target in self.adj.get((node, kind), ()):
                    if target not in seen:
                        seen.add(target); reached.append(target); nxt.append(target)
            if not nxt:
                break
            frontier = nxt
        return tuple(reached)

    def mutate(self, fact: Fact) -> None:
        key = (fact.source, fact.kind, fact.target)
        if key in self.edges:
            self.edges[key][0] += fact.weight
            self.edges[key][1] += fact.provenance_count
        else:
            self.edges[key] = [fact.weight, fact.provenance_count]
            bucket = self.adj[(fact.source, fact.kind)]
            bucket.append(fact.target); bucket.sort()

    def semantic_rows(self) -> Tuple[Tuple[int, int, int, float, int], ...]:
        return tuple((s, k, t, float(v[0]), int(v[1])) for (s, k, t), v in sorted(self.edges.items()))


class PackedSymbolic:
    def __init__(self, facts: Sequence[Fact]):
        self.sources: List[int] = []
        self.kinds: List[int] = []
        self.targets: List[int] = []
        self.weights: List[float] = []
        self.provenance_counts: List[int] = []
        self.primary: Dict[Tuple[int, int, int], int] = {}
        self.adj: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        for f in facts:
            self._append(f)

    def _append(self, f: Fact) -> None:
        idx = len(self.sources)
        self.sources.append(f.source); self.kinds.append(f.kind); self.targets.append(f.target)
        self.weights.append(f.weight); self.provenance_counts.append(f.provenance_count)
        self.primary[(f.source, f.kind, f.target)] = idx
        self.adj[(f.source, f.kind)].append(idx)
        self.adj[(f.source, f.kind)].sort(key=lambda i: self.targets[i])

    def strongest_target(self, source: int, kind: int) -> int | None:
        rows = self.adj.get((source, kind), ())
        if not rows:
            return None
        idx = max(rows, key=lambda i: (self.weights[i], self.targets[i]))
        return self.targets[idx]

    def reachable(self, source: int, kind: int, max_hops: int = 4) -> Tuple[int, ...]:
        seen = {source}; frontier = [source]; reached = []
        for _ in range(max_hops):
            nxt = []
            for node in frontier:
                for idx in self.adj.get((node, kind), ()):
                    target = self.targets[idx]
                    if target not in seen:
                        seen.add(target); reached.append(target); nxt.append(target)
            if not nxt:
                break
            frontier = nxt
        return tuple(reached)

    def mutate(self, fact: Fact) -> None:
        key = (fact.source, fact.kind, fact.target)
        idx = self.primary.get(key)
        if idx is None:
            self._append(fact)
        else:
            self.weights[idx] += fact.weight
            self.provenance_counts[idx] += fact.provenance_count

    def semantic_rows(self) -> Tuple[Tuple[int, int, int, float, int], ...]:
        rows = []
        for i in range(len(self.sources)):
            rows.append((self.sources[i], self.kinds[i], self.targets[i], self.weights[i], self.provenance_counts[i]))
        return tuple(sorted(rows))


def digest_rows(rows: Sequence[Tuple[int, int, int, float, int]]) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update(RECORD.pack(*row))
    return h.hexdigest()


def score(state, ids: Mapping[str, int], answers: Mapping[str, str]) -> Mapping[str, float]:
    metrics = {
        "association": float(state.strongest_target(ids["signal-a"], ids["means"]) == ids[answers["association"]]),
        "composition": float(ids[answers["composition"]] in state.reachable(ids["alpha"], ids["path"])),
        "choice_consistency": float(state.strongest_target(ids["self"], ids["prefers"]) == ids[answers["choice_consistency"]]),
        "partner_recognition": float(state.strongest_target(ids["partner-pattern"], ids["partner"]) == ids[answers["partner_recognition"]]),
    }
    metrics["acquired_score"] = mean(metrics.values())
    return metrics


def timed_queries(state, ids: Mapping[str, int], repetitions: int) -> float:
    start = time.perf_counter_ns()
    for _ in range(repetitions):
        state.strongest_target(ids["signal-a"], ids["means"])
        state.reachable(ids["alpha"], ids["path"])
        state.strongest_target(ids["self"], ids["prefers"])
        state.strongest_target(ids["partner-pattern"], ids["partner"])
    return (time.perf_counter_ns() - start) / repetitions


def timed_build(cls, facts: Sequence[Fact], repetitions: int) -> float:
    start = time.perf_counter_ns()
    for _ in range(repetitions):
        cls(facts)
    return (time.perf_counter_ns() - start) / repetitions


def traced_build_peak(cls, facts: Sequence[Fact]) -> int:
    tracemalloc.start()
    cls(facts)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def mutation_stream(facts: Sequence[Fact], count: int) -> Tuple[Fact, ...]:
    out = []
    n = len(facts)
    for i in range(count):
        base = facts[(i * 17 + 3) % n]
        out.append(Fact(base.source, base.kind, base.target, 0.125 + (i % 5) * 0.025, 1))
    return tuple(out)


def timed_mutations(state, mutations: Sequence[Fact]) -> float:
    start = time.perf_counter_ns()
    for f in mutations:
        state.mutate(f)
    return (time.perf_counter_ns() - start) / len(mutations)


def one_run(scale: int, seed: int, repetitions: int, build_repetitions: int, tolerance: float) -> Mapping[str, object]:
    events, answers = generate_events(scale, seed)
    rows = normalize(events)
    blob, ids, _ = encode_shared(rows)
    _, facts = decode_shared(blob)
    if len(facts) != scale:
        raise AssertionError("decoded relation count mismatch")

    geo = PackedGeo(facts)
    sym = PackedSymbolic(facts)
    geo_score = score(geo, ids, answers)
    sym_score = score(sym, ids, answers)
    equivalent = abs(geo_score["acquired_score"] - sym_score["acquired_score"]) <= tolerance

    mutation_count = max(32, scale // 4)
    mutations = mutation_stream(facts, mutation_count)
    geo_mut = PackedGeo(facts)
    sym_mut = PackedSymbolic(facts)
    geo_mut_ns = timed_mutations(geo_mut, mutations)
    sym_mut_ns = timed_mutations(sym_mut, mutations)
    geo_digest = digest_rows(geo_mut.semantic_rows())
    sym_digest = digest_rows(sym_mut.semantic_rows())

    return {
        "scale": scale,
        "seed": seed,
        "source_encoding_bytes": len(blob),
        "source_encoding_sha256": hashlib.sha256(blob).hexdigest(),
        "performance_equivalent": equivalent,
        "mutation_count": mutation_count,
        "post_mutation_digest_equal": geo_digest == sym_digest,
        "geo": {
            "score": geo_score,
            "build_and_index_ns": timed_build(PackedGeo, facts, build_repetitions),
            "build_peak_traced_bytes": traced_build_peak(PackedGeo, facts),
            "logical_query_operations": 7,
            "query_ns_per_four_task_bundle": timed_queries(geo, ids, repetitions),
            "mutation_ns_per_operation": geo_mut_ns,
            "post_mutation_digest": geo_digest,
        },
        "symbolic": {
            "score": sym_score,
            "build_and_index_ns": timed_build(PackedSymbolic, facts, build_repetitions),
            "build_peak_traced_bytes": traced_build_peak(PackedSymbolic, facts),
            "logical_query_operations": 7,
            "query_ns_per_four_task_bundle": timed_queries(sym, ids, repetitions),
            "mutation_ns_per_operation": sym_mut_ns,
            "post_mutation_digest": sym_digest,
        },
    }


def summarize(runs: Sequence[Mapping[str, object]], scales: Sequence[int]) -> Mapping[str, object]:
    out = {}
    for scale in scales:
        group = [r for r in runs if r["scale"] == scale]
        def avg(side: str, key: str) -> float:
            return mean(r[side][key] for r in group)
        geo = {k: avg("geo", k) for k in (
            "build_and_index_ns", "build_peak_traced_bytes", "logical_query_operations",
            "query_ns_per_four_task_bundle", "mutation_ns_per_operation")}
        sym = {k: avg("symbolic", k) for k in geo}
        out[str(scale)] = {
            "all_performance_equivalent": all(r["performance_equivalent"] for r in group),
            "all_post_mutation_digests_equal": all(r["post_mutation_digest_equal"] for r in group),
            "source_encoding_bytes_mean": mean(r["source_encoding_bytes"] for r in group),
            "cost_means": {
                "geo": geo,
                "symbolic": sym,
                "geo_over_symbolic": {k: geo[k] / sym[k] for k in geo},
            },
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--scales", type=int, nargs="+", default=[32, 128, 512, 2048])
    parser.add_argument("--repetitions", type=int, default=5000)
    parser.add_argument("--build-repetitions", type=int, default=250)
    parser.add_argument("--performance-tolerance", type=float, default=0.0)
    parser.add_argument("--out", default="experiments/geometric_si/results/GEOMETRIC-SI-04.json")
    args = parser.parse_args()
    if args.seeds <= 0 or args.repetitions <= 0 or args.build_repetitions <= 0:
        raise SystemExit("seeds/repetitions/build-repetitions must be positive")
    if args.performance_tolerance < 0 or any(s < 16 for s in args.scales):
        raise SystemExit("invalid tolerance or scale")

    started = time.time()
    runs = [one_run(scale, seed, args.repetitions, args.build_repetitions, args.performance_tolerance)
            for scale in args.scales for seed in range(args.seeds)]
    evidence = {
        "experiment": "GEOMETRIC-SI-04",
        "execution_requirement": "LOCAL EXECUTION REQUIRED",
        "git_head": git_head(),
        "parameters": {
            "seeds": list(range(args.seeds)), "scales": args.scales,
            "query_repetitions_per_seed_scale": args.repetitions,
            "build_repetitions_per_seed_scale": args.build_repetitions,
            "performance_tolerance": args.performance_tolerance,
        },
        "runtime": {
            "python": platform.python_version(), "platform": platform.platform(),
            "machine": platform.machine(), "processor": platform.processor(),
        },
        "elapsed_seconds": time.time() - started,
        "summary": summarize(runs, args.scales),
        "runs": runs,
        "interpretation_constraints": [
            "Both conditions ingest byte-identical packed source state.",
            "Source encoding bytes are an equality invariant, not an outcome metric.",
            "Cost interpretation requires performance equivalence and identical post-mutation semantic digests.",
            "tracemalloc and wall-clock values are local-runtime evidence only.",
            "No result establishes that SI is fundamentally geometric.",
        ],
    }
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(out)


if __name__ == "__main__":
    main()
