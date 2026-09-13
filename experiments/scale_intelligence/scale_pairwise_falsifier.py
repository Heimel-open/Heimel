#!/usr/bin/env python3
"""Frozen evaluator for SCALE-PAIRWISE-20."""

from __future__ import annotations

import math
from statistics import mean

TOP_PAIRS=((6,7),(4,6),(3,4),(3,5),(7,8))
REPLICATES=5
PAIR_COUNT=465
MAX_NUMERICAL_ERROR=1e-12
MIN_NATIVE_ADV=0.020
MIN_NATIVE_POSITIVE=4
MIN_TOP5_SUM=0.006
MIN_REPLICATE_TOP5_SUM=0.004
MIN_REPLICATE_TOP5_SUPPORT=4
MIN_POSITIVE_TOP_PAIRS=4
PERCENTILE_Q=0.90


def quantile(values,q):
    xs=sorted(values)
    if not xs:
        return float("nan")
    pos=(len(xs)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return xs[lo]
    w=pos-lo
    return xs[lo]*(1-w)+xs[hi]*w


def evaluate(data):
    try:
        native=list(data["native_advantages"])
        rows=list(data["pair_trials"])
        max_err=float(data["max_numerical_error"])
    except (KeyError,TypeError,ValueError):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"malformed"}

    if max_err>MAX_NUMERICAL_ERROR:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"numerical_reconstruction_failed","max_numerical_error":max_err}
    if len(native)!=REPLICATES or any(not math.isfinite(float(x)) for x in native):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"native_coverage"}

    expected={(r,j,k) for r in range(REPLICATES) for j in range(31) for k in range(j+1,31)}
    observed=set()
    pair_by_rep={}
    for row in rows:
        try:
            r=int(row["replicate"]); j=int(row["j"]); k=int(row["k"]); d=float(row["differential"])
        except (KeyError,TypeError,ValueError):
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"malformed_pair"}
        key=(r,j,k)
        if key in observed or key not in expected or not math.isfinite(d):
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"pair_coverage"}
        observed.add(key); pair_by_rep[key]=d
    if observed!=expected:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"pair_coverage"}

    native_mean=mean(native)
    native_positive=sum(x>0 for x in native)
    if native_mean<MIN_NATIVE_ADV or native_positive<MIN_NATIVE_POSITIVE:
        return {
            "status":"INSUFFICIENT_EVIDENCE",
            "reason":"native_advantage_not_reproduced",
            "native_advantage_mean":native_mean,
            "native_positive_replicates":native_positive,
        }

    pair_means={}
    for j in range(31):
        for k in range(j+1,31):
            pair_means[(j,k)]=mean(pair_by_rep[(r,j,k)] for r in range(REPLICATES))

    top5_sum=sum(pair_means[p] for p in TOP_PAIRS)
    rep_top5=[sum(pair_by_rep[(r,*p)] for p in TOP_PAIRS) for r in range(REPLICATES)]
    rep_support=sum(x>=MIN_REPLICATE_TOP5_SUM for x in rep_top5)
    positive_top=sum(pair_means[p]>0 for p in TOP_PAIRS)

    all_means=list(pair_means.values())
    p90=quantile(all_means,PERCENTILE_Q)
    top5_mean=mean(pair_means[p] for p in TOP_PAIRS)

    ranks={}
    sorted_pairs=sorted(pair_means.items(),key=lambda kv:kv[1],reverse=True)
    for rank,(p,val) in enumerate(sorted_pairs,1):
        if p in TOP_PAIRS:
            ranks[str(p)]=rank

    gates={
        "top5_sum_ge_0_006":top5_sum>=MIN_TOP5_SUM,
        "replicate_top5_support_4_of_5":rep_support>=MIN_REPLICATE_TOP5_SUPPORT,
        "positive_top_pairs_4_of_5":positive_top>=MIN_POSITIVE_TOP_PAIRS,
        "top5_mean_ge_empirical_p90":top5_mean>=p90,
    }
    status="NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA"

    return {
        "status":status,
        "native_advantage_mean":native_mean,
        "native_positive_replicates":native_positive,
        "top5_pair_means":{str(p):pair_means[p] for p in TOP_PAIRS},
        "top5_differential_sum":top5_sum,
        "replicate_top5_sums":rep_top5,
        "replicate_top5_support":rep_support,
        "positive_top_pairs":positive_top,
        "top5_mean_differential":top5_mean,
        "all_pair_mean_differential_p90":p90,
        "top5_fresh_ranks":ranks,
        "descriptive_pairwise_attribution_ratio":top5_sum/native_mean if native_mean else None,
        "fresh_top20":[{"pair":list(p),"mean_differential":v} for p,v in sorted_pairs[:20]],
        "gates":gates,
    }
