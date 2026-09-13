#!/usr/bin/env python3
"""Frozen evaluator for SCALE-CROSSPROJECTOR-25."""

from __future__ import annotations

import math

NULL_DRAWS=1000
NULL_SEED=250025
MAX_ERROR=1e-12
ALPHA=0.05


def evaluate(result):
    try:
        draws=int(result["null"]["draws"])
        seed=int(result["null"]["rng_seed"])
        fresh_count=int(result["fresh_seed_count"])
        delta=float(result["primary"]["target_delta_cross"])
        p=float(result["primary"]["empirical_p"])
        proj_err=float(result["integrity"]["max_projector_error"])
        decomp_err=float(result["integrity"]["max_decomposition_error"])
        rot_err=float(result["integrity"]["max_internal_rotation_projector_error"])
    except (KeyError,TypeError,ValueError):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"malformed"}

    if draws!=NULL_DRAWS or seed!=NULL_SEED or fresh_count!=10:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"coverage_or_null_config"}
    if max(proj_err,decomp_err,rot_err)>MAX_ERROR:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"integrity_failure"}
    if not math.isfinite(delta) or not math.isfinite(p) or not 0<p<=1:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"invalid_statistic"}

    status=(
        "CROSSPROJECTOR_OUTLIER_AGAINST_NULL"
        if delta>0 and p<=ALPHA
        else "NOT_CROSSPROJECTOR_OUTLIER_AGAINST_NULL"
    )
    return {
        "status":status,
        "alpha":ALPHA,
        "target_delta_cross":delta,
        "empirical_p":p,
    }
