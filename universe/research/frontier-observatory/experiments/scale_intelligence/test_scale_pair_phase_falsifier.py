from scale_pair_phase_falsifier import evaluate


def base():
    return {
        "pair_count": 465,
        "replicate_count": 10,
        "max_numerical_error": 0.0,
        "primary": {
            "target_mean_delta_phase": 0.01,
            "exact_pair_label_p": 1/465,
            "target_rank": 1,
            "target_replicate_delta_phase": [0.01] * 10,
        },
    }


def test_positive_outlier():
    assert evaluate(base())["status"] == "PAIR_PHASE_OUTLIER_AGAINST_NULL"


def test_not_outlier():
    d = base()
    d["primary"]["exact_pair_label_p"] = 0.2
    assert evaluate(d)["status"] == "NOT_PAIR_PHASE_OUTLIER_AGAINST_NULL"


def test_no_effect_floor():
    d = base()
    d["primary"]["target_mean_delta_phase"] = 1e-9
    d["primary"]["exact_pair_label_p"] = 0.04
    assert evaluate(d)["status"] == "PAIR_PHASE_OUTLIER_AGAINST_NULL"


def test_numerical_failure():
    d = base()
    d["max_numerical_error"] = 1e-6
    assert evaluate(d)["status"] == "INSUFFICIENT_EVIDENCE"


def test_bad_coverage():
    d = base()
    d["pair_count"] = 464
    assert evaluate(d)["status"] == "INSUFFICIENT_EVIDENCE"
