from scale_pairwise_falsifier import evaluate

def synthetic(top=0.0015, other=0.0002, native=0.035):
    rows=[]
    top_pairs={(6,7),(4,6),(3,4),(3,5),(7,8)}
    for r in range(5):
        for j in range(31):
            for k in range(j+1,31):
                rows.append({"replicate":r,"j":j,"k":k,"differential":top if (j,k) in top_pairs else other})
    return {"native_advantages":[native]*5,"pair_trials":rows,"max_numerical_error":0.0}

def test_survives():
    assert evaluate(synthetic())["status"]=="NOT_FALSIFIED_BY_DATA"

def test_native_missing_is_insufficient():
    assert evaluate(synthetic(native=0.005))["status"]=="INSUFFICIENT_EVIDENCE"

def test_weak_pairs_falsify():
    assert evaluate(synthetic(top=0.0005,other=0.0004))["status"]=="FALSIFIED_BY_DATA"

def test_numerical_failure_is_insufficient():
    d=synthetic(); d["max_numerical_error"]=1e-6
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"

def test_pair_coverage_failure():
    d=synthetic(); d["pair_trials"].pop()
    assert evaluate(d)["status"]=="INSUFFICIENT_EVIDENCE"
