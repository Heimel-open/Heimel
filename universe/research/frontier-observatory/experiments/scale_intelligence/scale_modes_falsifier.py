#!/usr/bin/env python3
"""Frozen evaluator for SCALE-MODES-18."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, median

SCALES = tuple(range(4, 16))
CONDITIONS = ("reflected", "self_padded")
TASKS = (
    "seg_b7", "seg_b10", "seg_b13",
    "markov_b3_l8", "markov_b3_l11", "markov_b3_l14",
    "markov_b6_l8", "markov_b6_l11", "markov_b6_l14",
)
REPLICATES = 5
MAX_NUMERICAL_ERROR = 1e-12
MIN_MEDIAN_WITHIN_ONE = 15
MAX_ALL_MEDIAN_ERROR = 2.0
MIN_REPLICATE_WITHIN_TWO = 75
MIN_MEDIAN_SPEARMAN = 0.85
MIN_CURVE_SPEARMAN = 0.80
MIN_CURVE_CELLS = 16
MAX_BOUNDARY_DELTA_ERROR = 1.0
MIN_BOUNDARY_DELTA_TASKS = 8


def _peak(scores):
    maximum = max(scores.values())
    tied = [s for s in SCALES if scores[s] == maximum]
    return mean(tied)


def _ranks(values):
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def _spearman(a, b):
    if len(a) != len(b) or len(a) < 2:
        return float("nan")
    ra = _ranks(a)
    rb = _ranks(b)
    ma, mb = mean(ra), mean(rb)
    da = sum((x-ma)**2 for x in ra)
    db = sum((x-mb)**2 for x in rb)
    if da == 0 or db == 0:
        return 1.0 if ra == rb else 0.0
    return sum((x-ma)*(y-mb) for x,y in zip(ra,rb)) / math.sqrt(da*db)


def evaluate(trials):
    if not trials:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"no_trials"}

    by_cell = defaultdict(list)
    invariant_sets = defaultdict(set)
    seed_map = defaultdict(set)
    max_error = 0.0

    for t in trials:
        try:
            condition = str(t["boundary_condition"])
            task = str(t["task_id"])
            scale = int(t["interaction_scale"])
            replicate = int(t["replicate"])
            seed = int(t["seed"])
            predictor = float(t["mode_harm_target_fraction"])
            capability = float(t["capability"])
            err = max(
                float(t["svd_reconstruction_max_error"]),
                float(t["modal_output_reconstruction_max_error"]),
                float(t["state_decomposition_max_error"]),
            )
            invariants = tuple(sorted(dict(t["condition_invariants"]).items()))
        except (KeyError, TypeError, ValueError):
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"malformed_trial"}

        if condition not in CONDITIONS or task not in TASKS or scale not in SCALES or not 0 <= replicate < REPLICATES:
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"unexpected_condition"}
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (predictor, capability)):
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"invalid_score"}
        if not math.isfinite(err) or err < 0:
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"invalid_numerical_error"}

        max_error = max(max_error, err)
        by_cell[(condition,task,scale)].append(t)
        invariant_sets[condition].add(invariants)
        seed_map[(condition,replicate)].add(seed)

    if max_error > MAX_NUMERICAL_ERROR:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"numerical_reconstruction_failed","max_numerical_error":max_error}
    if any(len(invariant_sets[c]) != 1 for c in CONDITIONS):
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"invariant_drift"}
    for r in range(REPLICATES):
        ss=[seed_map[(c,r)] for c in CONDITIONS]
        if any(len(x)!=1 for x in ss):
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"seed_pairing"}
        if len({next(iter(x)) for x in ss}) != 1:
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"cross_condition_seed_mismatch"}

    expected={(c,t,s) for c in CONDITIONS for t in TASKS for s in SCALES}
    if set(by_cell)!=expected:
        return {"status":"INSUFFICIENT_EVIDENCE","reason":"condition_coverage"}
    for cell in expected:
        rows=by_cell[cell]
        if len(rows)!=REPLICATES or sorted(int(x["replicate"]) for x in rows)!=list(range(REPLICATES)):
            return {"status":"INSUFFICIENT_EVIDENCE","reason":"replicate_coverage"}

    metrics=("mode_harm_target_fraction","capability")
    rep_peaks={m:{c:{t:[] for t in TASKS} for c in CONDITIONS} for m in metrics}
    med_peaks={m:{c:{} for c in CONDITIONS} for m in metrics}
    curves={c:{t:{} for t in TASKS} for c in CONDITIONS}

    for c in CONDITIONS:
        for task in TASKS:
            for s in SCALES:
                rows=by_cell[(c,task,s)]
                curves[c][task][s]={
                    "mode_harm_target_fraction":mean(float(x["mode_harm_target_fraction"]) for x in rows),
                    "capability":mean(float(x["capability"]) for x in rows),
                    "effective_harmful_mode_count":mean(float(x["effective_harmful_mode_count"]) for x in rows),
                    "top1_harmful_share":mean(float(x["top1_harmful_share"]) for x in rows),
                    "top3_harmful_share":mean(float(x["top3_harmful_share"]) for x in rows),
                }
            for m in metrics:
                peaks=[]
                for r in range(REPLICATES):
                    scores={
                        s:float(next(x for x in by_cell[(c,task,s)] if int(x["replicate"])==r)[m])
                        for s in SCALES
                    }
                    peaks.append(_peak(scores))
                rep_peaks[m][c][task]=peaks
                med_peaks[m][c][task]=median(peaks)

    within1=0
    all_within2=True
    rep_within2=0
    pm=[]; cm=[]
    curve_rho={c:{} for c in CONDITIONS}
    curve_pass=0
    errors={c:{} for c in CONDITIONS}

    for c in CONDITIONS:
        for task in TASKS:
            p=med_peaks["mode_harm_target_fraction"][c][task]
            q=med_peaks["capability"][c][task]
            e=abs(p-q)
            errors[c][task]=e
            within1 += int(e<=1)
            all_within2 = all_within2 and e<=MAX_ALL_MEDIAN_ERROR
            pm.append(p); cm.append(q)
            rep_within2 += sum(
                abs(a-b)<=2 for a,b in zip(
                    rep_peaks["mode_harm_target_fraction"][c][task],
                    rep_peaks["capability"][c][task],
                )
            )
            xs=[curves[c][task][s]["mode_harm_target_fraction"] for s in SCALES]
            ys=[curves[c][task][s]["capability"] for s in SCALES]
            rho=_spearman(xs,ys)
            curve_rho[c][task]=rho
            curve_pass += int(rho>=MIN_CURVE_SPEARMAN)

    median_rho=_spearman(pm,cm)

    boundary={}
    boundary_pass=0
    for task in TASKS:
        pd=med_peaks["mode_harm_target_fraction"]["self_padded"][task]-med_peaks["mode_harm_target_fraction"]["reflected"][task]
        cd=med_peaks["capability"]["self_padded"][task]-med_peaks["capability"]["reflected"][task]
        e=abs(pd-cd)
        boundary[task]={"predictor_delta":pd,"capability_delta":cd,"absolute_error":e}
        boundary_pass += int(e<=MAX_BOUNDARY_DELTA_ERROR)

    gates={
        "numerical_reconstruction":max_error<=MAX_NUMERICAL_ERROR,
        "median_within_one_15_of_18":within1>=MIN_MEDIAN_WITHIN_ONE,
        "all_medians_within_two":all_within2,
        "replicate_within_two_75_of_90":rep_within2>=MIN_REPLICATE_WITHIN_TWO,
        "median_peak_spearman_ge_0_85":median_rho>=MIN_MEDIAN_SPEARMAN,
        "curve_spearman_16_of_18":curve_pass>=MIN_CURVE_CELLS,
        "boundary_delta_prediction_8_of_9":boundary_pass>=MIN_BOUNDARY_DELTA_TASKS,
    }

    return {
        "status":"NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA",
        "max_numerical_error":max_error,
        "median_peaks":med_peaks,
        "replicate_peaks":rep_peaks,
        "median_peak_errors":errors,
        "median_within_one_cells":within1,
        "replicate_within_two_pairs":rep_within2,
        "median_peak_spearman":median_rho,
        "curve_spearman":curve_rho,
        "curve_spearman_pass_cells":curve_pass,
        "boundary_delta_errors":boundary,
        "boundary_delta_pass_tasks":boundary_pass,
        "aggregate_curves":curves,
        "gates":gates,
    }
