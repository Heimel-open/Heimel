#!/usr/bin/env python3
"""Frozen evaluator for SCALE-BOUNDARY-DYNAMICS-13."""

from __future__ import annotations

from copy import deepcopy
from statistics import median

from scale_peak_falsifier import evaluate as peak_evaluate

CONDITIONS = ("reflected", "self_padded")
PRIMARY_BLOCK = 5
MIN_MEDIAN_SHIFT = 2.0
MIN_DIRECTIONAL_REPLICATES = 4


def _project(
    trials: list[dict[str, object]], condition: str
) -> list[dict[str, object]]:
    projected = []
    for trial in trials:
        if trial.get("boundary_condition") != condition:
            continue
        try:
            projected.append(
                {
                    "task_block": trial["task_block"],
                    "interaction_scale": trial["interaction_scale"],
                    "replicate": trial["replicate"],
                    "seed": trial["seed"],
                    "non_geometry_invariants": deepcopy(
                        trial["condition_invariants"]
                    ),
                    "information_efficiency": trial[
                        "information_efficiency"
                    ],
                    "capability": trial["capability"],
                }
            )
        except KeyError:
            return []
    return projected


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    results = {}
    for condition in CONDITIONS:
        projected = _project(trials, condition)
        if not projected:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "reason": f"missing_condition_{condition}",
            }
        results[condition] = peak_evaluate(projected)
        if results[condition]["status"] == "INSUFFICIENT_EVIDENCE":
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "reason": f"{condition}_"
                + str(results[condition].get("reason", "invalid")),
                "conditions": results,
            }

    if any(
        results[c]["status"] != "NOT_FALSIFIED_BY_DATA"
        for c in CONDITIONS
    ):
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "condition_geometry_relation_failed",
            "conditions": results,
        }

    reflected = results["reflected"]["replicate_peaks"]["capability"][
        PRIMARY_BLOCK
    ]
    self_padded = results["self_padded"]["replicate_peaks"]["capability"][
        PRIMARY_BLOCK
    ]
    deltas = [
        float(self_padded[r]) - float(reflected[r])
        for r in range(len(reflected))
    ]
    median_shift = median(deltas)
    if median_shift > 0:
        directional = sum(delta > 0 for delta in deltas)
    elif median_shift < 0:
        directional = sum(delta < 0 for delta in deltas)
    else:
        directional = 0

    material_shift = abs(median_shift) >= MIN_MEDIAN_SHIFT
    coherent_direction = directional >= MIN_DIRECTIONAL_REPLICATES

    diagnostics = {}
    for metric in ("information_efficiency", "capability"):
        diagnostics[metric] = {}
        for block in (5, 9, 13):
            a = results["reflected"]["replicate_peaks"][metric][block]
            b = results["self_padded"]["replicate_peaks"][metric][block]
            ds = [float(y) - float(x) for x, y in zip(a, b)]
            diagnostics[metric][block] = {
                "reflected_peaks": a,
                "self_padded_peaks": b,
                "paired_deltas": ds,
                "median_delta": median(ds),
            }

    return {
        "status": (
            "NOT_FALSIFIED_BY_DATA"
            if material_shift and coherent_direction
            else "FALSIFIED_BY_DATA"
        ),
        "conditions": results,
        "primary": {
            "block": PRIMARY_BLOCK,
            "metric": "capability",
            "paired_deltas_self_minus_reflected": deltas,
            "median_shift": median_shift,
            "directional_replicates": directional,
        },
        "diagnostics": diagnostics,
        "gates": {
            "reflected_geometry_relation": True,
            "self_padded_geometry_relation": True,
            "material_median_shift": material_shift,
            "coherent_direction": coherent_direction,
        },
    }
