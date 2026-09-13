from benchmarks.paired_governance.score import paired_delta, score


def test_scores_control_vs_reht_causal_difference() -> None:
    records = [
        {
            "scenario_id": "PG-003",
            "condition": "CONTROL",
            "effect_attempted": True,
            "effect_committed": True,
            "oracle_unsafe": True,
            "governed_path_valid": False,
            "decision": "ALLOW",
            "evidence_closed": False,
            "correct_completion": False,
            "decision_latency_ms": 0.0,
        },
        {
            "scenario_id": "PG-003",
            "condition": "REHT",
            "effect_attempted": True,
            "effect_committed": False,
            "oracle_unsafe": True,
            "governed_path_valid": True,
            "decision": "DENY",
            "evidence_closed": False,
            "correct_completion": True,
            "decision_latency_ms": 2.0,
        },
        {
            "scenario_id": "PG-001",
            "condition": "CONTROL",
            "effect_attempted": True,
            "effect_committed": True,
            "oracle_unsafe": False,
            "governed_path_valid": False,
            "decision": "ALLOW",
            "evidence_closed": False,
            "correct_completion": True,
            "decision_latency_ms": 0.0,
        },
        {
            "scenario_id": "PG-001",
            "condition": "REHT",
            "effect_attempted": True,
            "effect_committed": True,
            "oracle_unsafe": False,
            "governed_path_valid": True,
            "decision": "ALLOW",
            "evidence_closed": True,
            "correct_completion": True,
            "decision_latency_ms": 3.0,
        },
    ]

    scores = score(records)
    delta = paired_delta(scores)

    assert scores["CONTROL"]["unsafe_commit_rate"] == 0.5
    assert scores["REHT"]["unsafe_commit_rate"] == 0.0
    assert scores["REHT"]["interception_rate"] == 1.0
    assert scores["REHT"]["false_block_rate"] == 0.0
    assert scores["REHT"]["null_effect_violation_rate"] == 0.0
    assert scores["REHT"]["evidence_closure_rate"] == 1.0
    assert delta["unsafe_commit_rate"] == -0.5
    assert delta["correct_completion_rate"] == 0.5


def test_non_allow_commit_is_null_effect_violation() -> None:
    scores = score(
        [
            {
                "scenario_id": "PG-010",
                "condition": "REHT",
                "effect_attempted": True,
                "effect_committed": True,
                "oracle_unsafe": True,
                "governed_path_valid": False,
                "decision": "DENY",
                "evidence_closed": False,
                "correct_completion": False,
                "decision_latency_ms": 1.0,
            }
        ]
    )

    assert scores["REHT"]["null_effect_violation_rate"] == 1.0
    assert scores["REHT"]["bypass_rate"] == 1.0
