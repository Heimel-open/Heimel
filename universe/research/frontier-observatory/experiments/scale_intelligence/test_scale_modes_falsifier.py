from scale_modes_falsifier import evaluate, SCALES, CONDITIONS, TASKS

SEEDS=(1,2,3,4,5)

def synthetic(offset=0):
    rows=[]
    for c in CONDITIONS:
        for ti,t in enumerate(TASKS):
            peak=5+(ti%6)
            for s in SCALES:
                for r,seed in enumerate(SEEDS):
                    rows.append({
                        "boundary_condition":c,
                        "task_id":t,
                        "interaction_scale":s,
                        "replicate":r,
                        "seed":seed,
                        "condition_invariants":{"condition":c},
                        "mode_harm_target_fraction":max(0.0,1.0-0.02*abs(s-peak)),
                        "capability":max(0.0,1.0-0.02*abs(s-(peak+offset))),
                        "effective_harmful_mode_count":2.0,
                        "top1_harmful_share":0.5,
                        "top3_harmful_share":0.8,
                        "svd_reconstruction_max_error":0.0,
                        "modal_output_reconstruction_max_error":0.0,
                        "state_decomposition_max_error":0.0,
                    })
    return rows

def test_matching_survives():
    assert evaluate(synthetic())["status"]=="NOT_FALSIFIED_BY_DATA"

def test_large_offset_falsifies():
    assert evaluate(synthetic(offset=3))["status"]=="FALSIFIED_BY_DATA"

def test_reconstruction_failure_is_insufficient():
    rows=synthetic()
    rows[0]["svd_reconstruction_max_error"]=1e-6
    assert evaluate(rows)["status"]=="INSUFFICIENT_EVIDENCE"

def test_missing_condition_is_insufficient():
    rows=[x for x in synthetic() if x["boundary_condition"]=="reflected"]
    assert evaluate(rows)["status"]=="INSUFFICIENT_EVIDENCE"

def test_invariant_drift_is_insufficient():
    rows=synthetic()
    rows[0]["condition_invariants"]={"condition":"drift"}
    assert evaluate(rows)["status"]=="INSUFFICIENT_EVIDENCE"
