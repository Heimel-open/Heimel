from scale_basis_falsifier import evaluate

def base():
    return {
        "rotation_count":1000,
        "max_operator_reconstruction_error":1e-15,
        "max_native_state_error":1e-15,
        "target_delta_phase_distribution":{"min":0.001,"max":0.01},
        "rank_bound":{"native_basis_rank":4,"worst_case_rank_upper_bound":197},
    }

def test_stable():
    assert evaluate(base())["status"]=="PAIR_LABEL_BASIS_STABLE"

def test_sign_cross_not_identifiable():
    d=base(); d["target_delta_phase_distribution"]["min"]=-0.001
    assert evaluate(d)["status"]=="PAIR_LABEL_NOT_IDENTIFIABLE"

def test_rank_span_not_identifiable():
    d=base(); d["rank_bound"]["worst_case_rank_upper_bound"]=300
    assert evaluate(d)["status"]=="PAIR_LABEL_NOT_IDENTIFIABLE"

def test_invariance_failure():
    d=base(); d["max_operator_reconstruction_error"]=1e-6
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"
