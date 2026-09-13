#!/usr/bin/env python3
"""Frozen evaluator for SCALE-BASIS-23."""

from __future__ import annotations

import math

ROTATIONS=1000
MAX_ERROR=1e-12

def evaluate(result):
    try:
        n=int(result["rotation_count"])
        max_err=float(result["max_operator_reconstruction_error"])
        native_err=float(result["max_native_state_error"])
        min_t=float(result["target_delta_phase_distribution"]["min"])
        max_t=float(result["target_delta_phase_distribution"]["max"])
        rank_upper=int(result["rank_bound"]["worst_case_rank_upper_bound"])
        native_rank=int(result["rank_bound"]["native_basis_rank"])
    except (KeyError,TypeError,ValueError):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"malformed"}

    if n!=ROTATIONS:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"rotation_coverage"}
    if max_err>MAX_ERROR or native_err>MAX_ERROR:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"operator_or_native_invariance_failed"}
    if not all(math.isfinite(v) for v in (min_t,max_t)):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"invalid_statistic"}

    sign_cross = min_t < 0.0 < max_t
    spans_top5_and_below_median = native_rank <= 23 and rank_upper > 233

    status = (
        "PAIR_LABEL_NOT_IDENTIFIABLE"
        if sign_cross or spans_top5_and_below_median
        else "PAIR_LABEL_BASIS_STABLE"
    )
    return {
        "status":status,
        "sign_crosses_zero":sign_cross,
        "native_top5":native_rank<=23,
        "below_median_possible":rank_upper>233,
    }
