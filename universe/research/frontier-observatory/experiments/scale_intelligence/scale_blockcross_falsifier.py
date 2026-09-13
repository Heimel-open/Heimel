#!/usr/bin/env python3
"""Frozen evaluator for SCALE-BLOCKCROSS-26."""

from __future__ import annotations

import math

EXPECTED_BLOCKS=12
EXPECTED_PAIRS=66
EXPECTED_REPLICATES=20
EXPECTED_SIGN_PATTERNS=1048576
MAX_ERROR=1e-12
ALPHA=0.05


def evaluate(result):
    try:
        blocks=int(result["block_count"])
        pairs=int(result["pair_count"])
        reps=int(result["replicate_count"])
        patterns=int(result["familywise_null"]["sign_patterns"])
        max_proj=float(result["integrity"]["max_projector_error"])
        max_rot=float(result["integrity"]["max_internal_rotation_projector_error"])
        max_d=float(result["integrity"]["max_internal_rotation_D_error"])
        rows=list(result["pair_results"])
    except (KeyError,TypeError,ValueError):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"malformed"}

    if blocks!=EXPECTED_BLOCKS or pairs!=EXPECTED_PAIRS or reps!=EXPECTED_REPLICATES:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"coverage"}
    if patterns!=EXPECTED_SIGN_PATTERNS:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"null_pattern_count"}
    if max(max_proj,max_rot,max_d)>MAX_ERROR:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"basis_invariance_failure"}
    if len(rows)!=EXPECTED_PAIRS:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"pair_result_coverage"}

    detected=[]
    for row in rows:
        try:
            mean_d=float(row["mean_D"])
            p=float(row["fwer_p"])
        except (KeyError,TypeError,ValueError):
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"invalid_pair_result"}
        if not math.isfinite(mean_d) or not math.isfinite(p) or not 0<p<=1:
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"invalid_pair_statistic"}
        if mean_d>0 and p<=ALPHA:
            detected.append(row["pair"])

    status=(
        "INVARIANT_BLOCK_RELATIONS_DETECTED"
        if detected else
        "NO_INVARIANT_BLOCK_RELATION_DETECTED"
    )
    return {
        "status":status,
        "alpha":ALPHA,
        "detected_count":len(detected),
        "detected_pairs":detected,
    }
