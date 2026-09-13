#!/usr/bin/env python3
"""Frozen evaluator for SCALE-COPULA-28."""

from __future__ import annotations

import math

EXPECTED_COMPONENTS=13
EXPECTED_REPLICATES=20
EXPECTED_DRAWS=256
EXPECTED_PATTERNS=1048576
ALPHA=0.05
MAX_ERROR=1e-12


def evaluate(result):
    try:
        comps=int(result["component_count"])
        reps=int(result["replicate_count"])
        draws=int(result["scramble_draws"])
        patterns=int(result["primary_null"]["sign_patterns"])
        collapse=float(result["primary"]["mean_collapse"])
        p=float(result["primary"]["exact_p"])
        proj=float(result["integrity"]["max_projector_partition_error"])
        decomp=float(result["integrity"]["max_native_decomposition_error"])
        coupled=float(result["integrity"]["max_coupled_control_capability_error"])
        checksum=bool(result["integrity"]["all_conditional_multiset_checks_pass"])
    except (KeyError,TypeError,ValueError):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"malformed"}

    if comps!=EXPECTED_COMPONENTS or reps!=EXPECTED_REPLICATES or draws!=EXPECTED_DRAWS:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"coverage"}
    if patterns!=EXPECTED_PATTERNS:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"null_pattern_count"}
    if max(proj,decomp,coupled)>MAX_ERROR:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"integrity_failure"}
    if not checksum:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"conditional_multiset_failure"}
    if not math.isfinite(collapse) or not math.isfinite(p) or not 0<p<=1:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"invalid_statistic"}

    status=(
        "RELATIONAL_ORGANIZATION_CAUSAL"
        if collapse>0 and p<=ALPHA
        else "RELATIONAL_ORGANIZATION_NOT_DETECTED"
    )
    return {
        "status":status,
        "alpha":ALPHA,
        "mean_collapse":collapse,
        "exact_p":p,
    }
