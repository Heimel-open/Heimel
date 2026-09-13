#!/usr/bin/env python3
"""Frozen evaluator for SCALE-BOUNDARY-12."""

from __future__ import annotations

from copy import deepcopy

from scale_peak_falsifier import evaluate as peak_evaluate

CAPABILITY_RELATED_GATES = (
    "capability_strict_order",
    "minimum_small_large_shift",
    "within_geometry_alignment",
    "paired_capability_outward",
)


def _project(trials: list[dict[str, object]], region: str) -> list[dict[str, object]]:
    projected = []
    for trial in trials:
        try:
            row = {
                "task_block": trial["task_block"],
                "interaction_scale": trial["interaction_scale"],
                "replicate": trial["replicate"],
                "seed": trial["seed"],
                "non_geometry_invariants": deepcopy(trial["non_geometry_invariants"]),
                "information_efficiency": trial[f"{region}_information_efficiency"],
                "capability": trial[f"{region}_capability"],
            }
        except KeyError:
            return []
        projected.append(row)
    return projected


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    interior_trials = _project(trials, "interior")
    full_trials = _project(trials, "full")
    if not interior_trials or not full_trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "missing_region_metric"}

    interior = peak_evaluate(interior_trials)
    full = peak_evaluate(full_trials)

    if interior["status"] == "INSUFFICIENT_EVIDENCE":
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "interior_" + str(interior.get("reason", "invalid")),
            "interior": interior,
            "full": full,
        }
    if full["status"] == "INSUFFICIENT_EVIDENCE":
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "full_" + str(full.get("reason", "invalid")),
            "interior": interior,
            "full": full,
        }

    full_capability_failures = [
        gate
        for gate in CAPABILITY_RELATED_GATES
        if full["gates"].get(gate) is False
    ]
    boundary_specificity = bool(full_capability_failures)
    interior_pass = interior["status"] == "NOT_FALSIFIED_BY_DATA"

    return {
        "status": (
            "NOT_FALSIFIED_BY_DATA"
            if interior_pass and boundary_specificity
            else "FALSIFIED_BY_DATA"
        ),
        "interior": interior,
        "full": full,
        "boundary_specificity": boundary_specificity,
        "full_capability_gate_failures": full_capability_failures,
        "gates": {
            "interior_peak_relation": interior_pass,
            "boundary_specificity": boundary_specificity,
        },
    }
