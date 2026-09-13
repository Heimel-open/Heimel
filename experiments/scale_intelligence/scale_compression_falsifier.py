#!/usr/bin/env python3
"""Frozen evaluator for SCALE-COMPRESSION-07."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

SCALES = (1, 2, 4, 8, 16)
CANDIDATE_SCALE = 8
MIN_REPLICATES = 5
MIN_SUFFICIENT_GAIN_LOW = 0.05
MIN_SUFFICIENT_GAIN_HIGH = 0.03
MIN_DECODABILITY_GAIN_LOW = 0.05
MIN_DECODABILITY_GAIN_HIGH = 0.03
MIN_NUISANCE_COMPRESSION_GAIN_LOW = 0.10
MIN_PAIRED_WINS = 4


def _aggregate(trials: list[dict[str, object]], metric: str) -> dict[int, float]:
    by_scale: dict[int, list[float]] = defaultdict(list)
    for trial in trials:
        by_scale[int(trial["interaction_scale"])].append(float(trial[metric]))
    return {scale: mean(values) for scale, values in by_scale.items()}


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    expected_invariants = trials[0].get("invariants")
    if any(trial.get("invariants") != expected_invariants for trial in trials):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invariant_drift"}

    by_scale: dict[int, list[dict[str, object]]] = defaultdict(list)
    for trial in trials:
        scale = int(trial["interaction_scale"])
        if scale not in SCALES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unexpected_scale"}
        by_scale[scale].append(trial)

    if set(by_scale) != set(SCALES):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "missing_scale"}
    if any(len(by_scale[scale]) < MIN_REPLICATES for scale in SCALES):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "insufficient_replicates"}

    decodability = _aggregate(trials, "target_decodability")
    compression = _aggregate(trials, "nuisance_compression")
    sufficient = _aggregate(trials, "sufficient_compression")

    paired_wins = 0
    by_rep_scale: dict[tuple[int, int], float] = {}
    for trial in trials:
        key = (int(trial["replicate"]), int(trial["interaction_scale"]))
        by_rep_scale[key] = float(trial["sufficient_compression"])
    replicate_ids = sorted({int(trial["replicate"]) for trial in trials})
    for replicate in replicate_ids:
        required = [(replicate, scale) for scale in (1, CANDIDATE_SCALE, 16)]
        if all(key in by_rep_scale for key in required):
            candidate = by_rep_scale[(replicate, CANDIDATE_SCALE)]
            if candidate > by_rep_scale[(replicate, 1)] and candidate > by_rep_scale[(replicate, 16)]:
                paired_wins += 1

    gates = {
        "sufficient_gain_vs_scale1": sufficient[CANDIDATE_SCALE] - sufficient[1] >= MIN_SUFFICIENT_GAIN_LOW,
        "sufficient_gain_vs_scale16": sufficient[CANDIDATE_SCALE] - sufficient[16] >= MIN_SUFFICIENT_GAIN_HIGH,
        "decodability_gain_vs_scale1": decodability[CANDIDATE_SCALE] - decodability[1] >= MIN_DECODABILITY_GAIN_LOW,
        "decodability_gain_vs_scale16": decodability[CANDIDATE_SCALE] - decodability[16] >= MIN_DECODABILITY_GAIN_HIGH,
        "nuisance_compression_gain_vs_scale1": compression[CANDIDATE_SCALE] - compression[1] >= MIN_NUISANCE_COMPRESSION_GAIN_LOW,
        "paired_wins": paired_wins >= MIN_PAIRED_WINS,
    }

    return {
        "status": "NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA",
        "candidate_scale": CANDIDATE_SCALE,
        "target_decodability_by_scale": decodability,
        "nuisance_compression_by_scale": compression,
        "sufficient_compression_by_scale": sufficient,
        "paired_wins": paired_wins,
        "gates": gates,
        "thresholds": {
            "min_sufficient_gain_vs_scale1": MIN_SUFFICIENT_GAIN_LOW,
            "min_sufficient_gain_vs_scale16": MIN_SUFFICIENT_GAIN_HIGH,
            "min_decodability_gain_vs_scale1": MIN_DECODABILITY_GAIN_LOW,
            "min_decodability_gain_vs_scale16": MIN_DECODABILITY_GAIN_HIGH,
            "min_nuisance_compression_gain_vs_scale1": MIN_NUISANCE_COMPRESSION_GAIN_LOW,
            "min_paired_wins": MIN_PAIRED_WINS,
            "min_replicates": MIN_REPLICATES,
        },
    }
