#!/usr/bin/env python3
"""Frozen evaluator for SCALE-DECOUPLING-14."""

from __future__ import annotations

from collections import defaultdict
from statistics import median

from scale_peak_falsifier import evaluate as peak_evaluate

CONDITIONS = ("reflected", "self_padded")
CONFIRMATORY_BLOCKS = (9, 13)
MIN_EFFICIENCY_SHIFT = 3.0
MAX_CAPABILITY_SHIFT = 1.0
MIN_PAIRED_DECOUPLED = 4


def _project(trials, condition):
    rows = []
    for t in trials:
        if t.get("boundary_condition") != condition:
            continue
        try:
            rows.append({
                "task_block": t["task_block"],
                "interaction_scale": t["interaction_scale"],
                "replicate": t["replicate"],
                "seed": t["seed"],
                "non_geometry_invariants": t["condition_invariants"],
                "information_efficiency": t["information_efficiency"],
                "capability": t["capability"],
            })
        except KeyError:
            return []
    return rows


def evaluate(trials):
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    results = {}
    for condition in CONDITIONS:
        rows = _project(trials, condition)
        if not rows:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": f"missing_{condition}"}
        results[condition] = peak_evaluate(rows)
        if results[condition]["status"] == "INSUFFICIENT_EVIDENCE":
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": f"invalid_{condition}", "conditions": results}

    # Only capability ordering is a prerequisite; efficiency ordering is the object being perturbed.
    for condition in CONDITIONS:
        c = results[condition]["median_peaks"]["capability"]
        if not (c[5] < c[9] < c[13]):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": f"capability_order_failed_{condition}", "conditions": results}

    diagnostics = {}
    material_blocks = []
    falsifying_blocks = []
    for block in (5, 9, 13):
        er = results["reflected"]["replicate_peaks"]["information_efficiency"][block]
        es = results["self_padded"]["replicate_peaks"]["information_efficiency"][block]
        cr = results["reflected"]["replicate_peaks"]["capability"][block]
        cs = results["self_padded"]["replicate_peaks"]["capability"][block]
        ed = [float(b) - float(a) for a, b in zip(er, es)]
        cd = [float(b) - float(a) for a, b in zip(cr, cs)]
        em = median(ed)
        cm = median(cd)
        paired = sum(
            abs(e) >= MIN_EFFICIENCY_SHIFT and abs(c) <= MAX_CAPABILITY_SHIFT
            for e, c in zip(ed, cd)
        )
        diagnostics[block] = {
            "efficiency_deltas": ed,
            "capability_deltas": cd,
            "median_efficiency_shift": em,
            "median_capability_shift": cm,
            "median_decoupling": abs(em - cm),
            "paired_decoupled": paired,
        }
        if block in CONFIRMATORY_BLOCKS and abs(em) >= MIN_EFFICIENCY_SHIFT:
            material_blocks.append(block)
            if abs(cm) <= MAX_CAPABILITY_SHIFT and paired >= MIN_PAIRED_DECOUPLED:
                falsifying_blocks.append(block)

    if not material_blocks:
        status = "INSUFFICIENT_EVIDENCE"
        reason = "material_efficiency_perturbation_not_reproduced"
    elif falsifying_blocks:
        status = "FALSIFIED_BY_DATA"
        reason = "efficiency_capability_necessity_broken"
    else:
        status = "NOT_FALSIFIED_BY_DATA"
        reason = "capability_moved_with_material_efficiency_shift"

    return {
        "status": status,
        "reason": reason,
        "conditions": results,
        "material_efficiency_shift_blocks": material_blocks,
        "falsifying_blocks": falsifying_blocks,
        "diagnostics": diagnostics,
    }
