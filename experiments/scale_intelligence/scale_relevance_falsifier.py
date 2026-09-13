#!/usr/bin/env python3
"""Evaluate the preregistered SCALE-RELEVANCE-06 gates."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

REQUIRED_INVARIANTS = (
    "node_set",
    "topology",
    "initial_state",
    "taskset",
    "compute_budget",
    "update_rule",
)


def _invariant_signature(trial: dict) -> tuple:
    invariants = trial.get("invariants", {})
    return tuple((key, invariants.get(key)) for key in REQUIRED_INVARIANTS)


def evaluate(
    trials: list[dict],
    *,
    capability_margin: float = 0.05,
    min_auc: float = 0.60,
    auc_margin_over_high_scale: float = 0.03,
    min_margin_score: float = 0.03,
    margin_score_over_high_scale: float = 0.01,
    min_paired_wins: int = 4,
    min_replicates: int = 5,
) -> dict:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no trials"}

    signatures = {_invariant_signature(trial) for trial in trials}
    if len(signatures) != 1:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "non-scale invariants changed across trials",
        }

    grouped: dict[int, list[dict]] = defaultdict(list)
    for trial in trials:
        grouped[int(trial["interaction_scale"])].append(trial)

    required_scales = (1, 2, 4, 8, 16)
    if any(len(grouped[scale]) < min_replicates for scale in required_scales):
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "insufficient paired replicates at one or more frozen scales",
        }

    aggregates = {}
    for scale in required_scales:
        rows = grouped[scale]
        aggregates[scale] = {
            "capability": mean(float(row["capability"]) for row in rows),
            "task_relevant_auc": mean(float(row["task_relevant_auc"]) for row in rows),
            "task_relevant_margin": mean(float(row["task_relevant_margin"]) for row in rows),
            "integration": mean(float(row["integration"]) for row in rows),
        }

    candidate_scale = max((2, 4, 8), key=lambda scale: aggregates[scale]["capability"])
    candidate = aggregates[candidate_scale]
    low = aggregates[1]
    high = aggregates[16]

    by_key = {}
    for scale in required_scales:
        by_key[scale] = {
            (int(row["replicate"]), int(row["seed"])): row for row in grouped[scale]
        }

    paired_keys = set(by_key[1]) & set(by_key[16]) & set(by_key[candidate_scale])
    capability_wins = sum(
        float(by_key[candidate_scale][key]["capability"])
        > max(float(by_key[1][key]["capability"]), float(by_key[16][key]["capability"]))
        for key in paired_keys
    )
    relevance_wins = sum(
        float(by_key[candidate_scale][key]["task_relevant_auc"])
        > float(by_key[16][key]["task_relevant_auc"])
        for key in paired_keys
    )

    gates = {
        "capability_over_scale_1": candidate["capability"] - low["capability"] >= capability_margin,
        "capability_over_scale_16": candidate["capability"] - high["capability"] >= capability_margin,
        "candidate_auc_floor": candidate["task_relevant_auc"] >= min_auc,
        "candidate_auc_over_scale_16": candidate["task_relevant_auc"] - high["task_relevant_auc"] >= auc_margin_over_high_scale,
        "candidate_margin_floor": candidate["task_relevant_margin"] >= min_margin_score,
        "candidate_margin_over_scale_16": candidate["task_relevant_margin"] - high["task_relevant_margin"] >= margin_score_over_high_scale,
        "paired_capability_wins": capability_wins >= min_paired_wins,
        "paired_relevance_wins": relevance_wins >= min_paired_wins,
    }

    status = "NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA"
    failed = [name for name, passed in gates.items() if not passed]
    return {
        "status": status,
        "reason": "all preregistered gates passed" if not failed else "failed gates: " + ", ".join(failed),
        "candidate_scale": candidate_scale,
        "aggregates": aggregates,
        "capability_wins": capability_wins,
        "relevance_wins": relevance_wins,
        "gates": gates,
        "thresholds": {
            "capability_margin": capability_margin,
            "min_auc": min_auc,
            "auc_margin_over_high_scale": auc_margin_over_high_scale,
            "min_margin_score": min_margin_score,
            "margin_score_over_high_scale": margin_score_over_high_scale,
            "min_paired_wins": min_paired_wins,
            "min_replicates": min_replicates,
        },
    }
