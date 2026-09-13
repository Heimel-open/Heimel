from seed_falsifier import METRICS, evaluate


def trial(seed_size, condition, value, replicate=0):
    return {
        "seed_size": seed_size,
        "condition": condition,
        "replicate": replicate,
        "phenotype": {metric: value for metric in METRICS},
    }


def test_finds_smallest_relation_specific_seed():
    trials = []
    for replicate, value in enumerate((0.30, 0.40, 0.20)):
        trials.append(trial(1, "intact", value, replicate))
    for replicate, value in enumerate((0.75, 0.72, 0.76)):
        trials.append(trial(2, "intact", value, replicate))
    for replicate, value in enumerate((0.80, 0.82, 0.79)):
        trials.append(trial(3, "intact", value, replicate))
    for replicate, value in enumerate((0.40, 0.45, 0.50)):
        trials.append(trial(2, "shuffled", value, replicate))

    result = evaluate(trials)

    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["s_star"] == 2
    assert result["relation_margin_observed"] >= 0.15


def test_shuffle_that_preserves_phenotype_falsifies_relation_specific_claim():
    trials = []
    for replicate, value in enumerate((0.80, 0.82, 0.79)):
        trials.append(trial(2, "intact", value, replicate))
    for replicate, value in enumerate((0.75, 0.77, 0.76)):
        trials.append(trial(2, "shuffled", value, replicate))

    result = evaluate(trials)

    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["s_star"] == 2


def test_missing_shuffle_is_insufficient_not_positive():
    trials = [
        trial(2, "intact", 0.80, 0),
        trial(2, "intact", 0.82, 1),
        trial(2, "intact", 0.79, 2),
    ]

    result = evaluate(trials)

    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["s_star"] == 2


def test_no_recovering_seed_falsifies_tested_range():
    trials = []
    for replicate, value in enumerate((0.30, 0.40, 0.20)):
        trials.append(trial(1, "intact", value, replicate))
    for replicate, value in enumerate((0.50, 0.55, 0.60)):
        trials.append(trial(2, "intact", value, replicate))

    result = evaluate(trials)

    assert result["status"] == "FALSIFIED_BY_DATA"
    assert "no tested intact seed size" in result["reason"]
