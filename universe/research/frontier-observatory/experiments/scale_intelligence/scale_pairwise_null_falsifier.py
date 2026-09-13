#!/usr/bin/env python3
"""Frozen evaluator for SCALE-PAIRWISE-NULL-21."""

from __future__ import annotations

import math

ALPHA=0.05
EXPECTED_PAIRS=465
EXPECTED_REPLICATES=10
MAX_NUMERICAL_ERROR=1e-12
EXPECTED_DISCOVERY_HASH="sha256:0c89e1c7d3b39c93abb03ac3a7bbee0d9079afb3c23ec5697b7839e659568132"
EXPECTED_PERMUTATIONS=100000
EXPECTED_PRIMARY_SEED=210021
EXPECTED_TOP5_SEED=210022


def evaluate(result):
    try:
        pair_count=int(result["pair_count"])
        replicate_count=int(result["replicate_count"])
        max_error=float(result["max_numerical_error"])
        discovery_hash=str(result["discovery_vector_hash"])
        perm_count=int(result["primary_null"]["permutations"])
        primary_seed=int(result["primary_null"]["rng_seed"])
        top5_seed=int(result["top5_null"]["rng_seed"])
        rho=float(result["primary"]["spearman_rho"])
        p=float(result["primary"]["empirical_p"])
    except (KeyError,TypeError,ValueError):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"malformed_result"}

    if pair_count!=EXPECTED_PAIRS or replicate_count!=EXPECTED_REPLICATES:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"coverage"}
    if max_error>MAX_NUMERICAL_ERROR:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"numerical_reconstruction_failed"}
    if discovery_hash!=EXPECTED_DISCOVERY_HASH:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"discovery_hash_mismatch"}
    if perm_count!=EXPECTED_PERMUTATIONS or primary_seed!=EXPECTED_PRIMARY_SEED or top5_seed!=EXPECTED_TOP5_SEED:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"null_configuration_mismatch"}
    if not math.isfinite(rho) or not math.isfinite(p) or not 0<p<=1:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"invalid_primary_statistic"}

    status="PREDICTIVE_AGAINST_NULL" if rho>0 and p<=ALPHA else "NOT_PREDICTIVE_AGAINST_NULL"
    return {
        "status":status,
        "alpha":ALPHA,
        "primary_spearman_rho":rho,
        "primary_empirical_p":p,
    }
