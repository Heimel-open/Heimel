from scale_interference_falsifier import evaluate, SCALES, CONDITIONS, TASKS

SEEDS=(1,2,3,4,5)


def synthetic(native_hi=0.83, native_lo=0.79, scr_hi=0.80, scr_lo=0.80, key_drop=0.03):
    rows=[]
    for c in CONDITIONS:
        for task in TASKS:
            for s in SCALES:
                for r,seed in enumerate(SEEDS):
                    native=0.75
                    scrambled=0.75
                    if c=="self_padded" and task=="seg_b13" and s==7:
                        native=native_lo
                        scrambled=scr_lo
                    elif c=="self_padded" and task=="seg_b13" and s==13:
                        native=native_hi
                        scrambled=scr_hi
                    elif c=="self_padded" and task=="seg_b7" and s==7:
                        native=0.80
                        scrambled=0.80
                    elif c=="self_padded" and task=="seg_b10" and s==9:
                        native=0.81
                        scrambled=0.81
                    rows.append({
                        "boundary_condition":c,
                        "task_id":task,
                        "interaction_scale":s,
                        "replicate":r,
                        "seed":seed,
                        "condition_invariants":{"condition":c},
                        "native_capability":native,
                        "scrambled_capability":scrambled,
                        "svd_reconstruction_max_error":0.0,
                        "modal_output_reconstruction_max_error":0.0,
                        "state_decomposition_max_error":0.0,
                        "scramble_energy_max_error":0.0,
                    })
    return rows


def test_interference_survives():
    assert evaluate(synthetic())["status"]=="NOT_FALSIFIED_BY_DATA"


def test_no_native_replication_is_insufficient():
    assert evaluate(synthetic(native_hi=0.80,native_lo=0.79))["status"]=="INSUFFICIENT_EVIDENCE"


def test_scramble_does_not_collapse_falsifies():
    assert evaluate(synthetic(scr_hi=0.83,scr_lo=0.79))["status"]=="FALSIFIED_BY_DATA"


def test_energy_failure_is_insufficient():
    rows=synthetic()
    rows[0]["scramble_energy_max_error"]=1e-6
    assert evaluate(rows)["status"]=="INSUFFICIENT_EVIDENCE"


def test_missing_condition_is_insufficient():
    rows=[x for x in synthetic() if x["boundary_condition"]=="reflected"]
    assert evaluate(rows)["status"]=="INSUFFICIENT_EVIDENCE"
