#!/usr/bin/env python3
"""Frozen evaluator for SCALE-PAIR-PHASE-22."""

from __future__ import annotations

import math

PAIR_COUNT = 465
REPLICATES = 10
TARGET = (6, 7)
ALPHA = 0.05
MAX_NUMERICAL_ERROR = 1e-12


def evaluate(result):
    try:
        pair_count = int(result["pair_count"])
        replicate_count = int(result["replicate_count"])
        max_error = float(result["max_numerical_error"])
        target_mean = float(result["primary"]["target_mean_delta_phase"])
        p = float(result["primary"]["exact_pair_label_p"])
        target_rank = int(result["primary"]["target_rank"])
        target_reps = list(result["primary"]["target_replicate_delta_phase"])
    except (KeyError, TypeError, ValueError):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "malformed_result"}

    if pair_count != PAIR_COUNT or replicate_count != REPLICATES:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "coverage"}
    if max_error > MAX_NUMERICAL_ERROR:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "numerical_reconstruction_failed",
        }
    if len(target_reps) != REPLICATES:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_coverage"}
    if not all(math.isfinite(float(x)) for x in target_reps):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_replicate"}
    if not (1 <= target_rank <= PAIR_COUNT):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_rank"}
    if not math.isfinite(target_mean) or not math.isfinite(p) or not (0 < p <= 1):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_statistic"}

    status = (
        "PAIR_PHASE_OUTLIER_AGAINST_NULL"
        if target_mean > 0 and p <= ALPHA
        else "NOT_PAIR_PHASE_OUTLIER_AGAINST_NULL"
    )
    return {
        "status": status,
        "alpha": ALPHA,
        "target_pair": list(TARGET),
        "target_mean_delta_phase": target_mean,
        "target_rank": target_rank,
        "exact_pair_label_p": p,
    }
