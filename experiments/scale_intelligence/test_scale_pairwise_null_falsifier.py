from scale_pairwise_null_falsifier import evaluate

def base():
    return {
        "pair_count":465,
        "replicate_count":10,
        "max_numerical_error":0.0,
        "discovery_vector_hash":"sha256:0c89e1c7d3b39c93abb03ac3a7bbee0d9079afb3c23ec5697b7839e659568132",
        "primary_null":{"permutations":100000,"rng_seed":210021},
        "top5_null":{"rng_seed":210022},
        "primary":{"spearman_rho":0.2,"empirical_p":0.01},
    }

def test_predictive():
    assert evaluate(base())["status"]=="PREDICTIVE_AGAINST_NULL"

def test_not_predictive():
    d=base(); d["primary"]["empirical_p"]=0.3
    assert evaluate(d)["status"]=="NOT_PREDICTIVE_AGAINST_NULL"

def test_no_effect_floor():
    d=base(); d["primary"]["spearman_rho"]=1e-6; d["primary"]["empirical_p"]=0.04
    assert evaluate(d)["status"]=="PREDICTIVE_AGAINST_NULL"

def test_hash_failure():
    d=base(); d["discovery_vector_hash"]="bad"
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"

def test_coverage_failure():
    d=base(); d["pair_count"]=464
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"
