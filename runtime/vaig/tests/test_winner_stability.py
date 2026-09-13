from vaig.evaluation.winner_stability import audit_winner_stability


def test_metric_change_degrades_claim():
    result = audit_winner_stability(
        "A",
        source_winners=["A"],
        rerun_winners=["A", "A"],
        metric_winners={"mean": "A", "worst_case": "B"},
        budget_winners={"small": "A", "large": "A"},
    )
    assert result.stable is False
    assert result.classification == "CONDITIONAL_OR_UNSTABLE"
    assert result.changed_dimensions == ("metric",)


def test_missing_dimensions_are_not_treated_as_pass():
    result = audit_winner_stability("A", source_winners=["A"])
    assert result.stable is False
    assert result.classification == "INSUFFICIENT_STABILITY_EVIDENCE"


def test_all_dimensions_preserve_winner():
    result = audit_winner_stability(
        "A",
        source_winners=["A"],
        rerun_winners=["A"],
        metric_winners={"m1": "A", "m2": "A"},
        budget_winners={"b1": "A", "b2": "A"},
    )
    assert result.stable is True
    assert result.classification == "STABLE_ACROSS_TESTED_DIMENSIONS"


def test_mechanism_is_not_inferred_from_rank_change():
    result = audit_winner_stability(
        "A",
        source_winners=["B"],
        rerun_winners=["A"],
        metric_winners={"m": "A"},
        budget_winners={"b": "A"},
    )
    assert result.mechanism_identifiable is False
