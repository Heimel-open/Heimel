from scale_crossprojector_falsifier import evaluate


def base():
    return {
        "fresh_seed_count":10,
        "null":{"draws":1000,"rng_seed":250025},
        "primary":{"target_delta_cross":0.01,"empirical_p":0.01},
        "integrity":{
            "max_projector_error":1e-15,
            "max_decomposition_error":1e-15,
            "max_internal_rotation_projector_error":1e-15,
        },
    }


def test_outlier():
    assert evaluate(base())["status"]=="CROSSPROJECTOR_OUTLIER_AGAINST_NULL"


def test_not_outlier():
    d=base(); d["primary"]["empirical_p"]=0.2
    assert evaluate(d)["status"]=="NOT_CROSSPROJECTOR_OUTLIER_AGAINST_NULL"


def test_no_effect_floor():
    d=base(); d["primary"]["target_delta_cross"]=1e-10; d["primary"]["empirical_p"]=0.04
    assert evaluate(d)["status"]=="CROSSPROJECTOR_OUTLIER_AGAINST_NULL"


def test_integrity_failure():
    d=base(); d["integrity"]["max_decomposition_error"]=1e-6
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"
