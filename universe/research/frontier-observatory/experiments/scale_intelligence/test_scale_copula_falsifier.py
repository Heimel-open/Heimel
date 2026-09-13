from scale_copula_falsifier import evaluate


def base():
    return {
        "component_count":13,
        "replicate_count":20,
        "scramble_draws":256,
        "primary_null":{"sign_patterns":1048576},
        "primary":{"mean_collapse":0.01,"exact_p":0.01},
        "integrity":{
            "max_projector_partition_error":1e-15,
            "max_native_decomposition_error":1e-15,
            "max_coupled_control_capability_error":0.0,
            "all_conditional_multiset_checks_pass":True,
        },
    }


def test_causal():
    assert evaluate(base())["status"]=="RELATIONAL_ORGANIZATION_CAUSAL"


def test_not_detected():
    d=base(); d["primary"]["exact_p"]=0.2
    assert evaluate(d)["status"]=="RELATIONAL_ORGANIZATION_NOT_DETECTED"


def test_no_effect_floor():
    d=base(); d["primary"]["mean_collapse"]=1e-15; d["primary"]["exact_p"]=0.04
    assert evaluate(d)["status"]=="RELATIONAL_ORGANIZATION_CAUSAL"


def test_coupled_failure():
    d=base(); d["integrity"]["max_coupled_control_capability_error"]=1e-5
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"


def test_multiset_failure():
    d=base(); d["integrity"]["all_conditional_multiset_checks_pass"]=False
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"
