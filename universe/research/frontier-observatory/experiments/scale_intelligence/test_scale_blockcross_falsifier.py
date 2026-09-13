from scale_blockcross_falsifier import evaluate


def base():
    rows=[]
    for i in range(66):
        rows.append({
            "pair":[i//11,(i//11)+1],
            "mean_D":0.001 if i==0 else 0.0,
            "fwer_p":0.01 if i==0 else 1.0,
        })
    return {
        "block_count":12,
        "pair_count":66,
        "replicate_count":20,
        "familywise_null":{"sign_patterns":1048576},
        "integrity":{
            "max_projector_error":1e-15,
            "max_internal_rotation_projector_error":1e-15,
            "max_internal_rotation_D_error":0.0,
        },
        "pair_results":rows,
    }


def test_detected():
    assert evaluate(base())["status"]=="INVARIANT_BLOCK_RELATIONS_DETECTED"


def test_no_detection():
    d=base()
    d["pair_results"][0]["fwer_p"]=0.2
    assert evaluate(d)["status"]=="NO_INVARIANT_BLOCK_RELATION_DETECTED"


def test_no_effect_floor():
    d=base()
    d["pair_results"][0]["mean_D"]=1e-12
    assert evaluate(d)["status"]=="INVARIANT_BLOCK_RELATIONS_DETECTED"


def test_null_count_failure():
    d=base()
    d["familywise_null"]["sign_patterns"]=100000
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"


def test_basis_failure():
    d=base()
    d["integrity"]["max_internal_rotation_projector_error"]=1e-6
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"
