from vaig.agent_loop import AgentLoop, LoopStep
from vaig.agent_loop.drift import DriftSignal, cumulative_drift, score_drift


def test_drift_by_small_steps_halts_when_cumulative_meaning_is_lost():
    loop = AgentLoop(original_intent="Summarize project risks")
    result = loop.run(
        [
            LoopStep(event_type="plan", current_frame="Summarize project risks", drift_score=0.10),
            LoopStep(event_type="observation", current_frame="Discuss unrelated staffing", drift_score=0.45),
            LoopStep(event_type="action", current_frame="Send staffing recommendation", drift_score=0.75),
        ]
    )

    assert result.halted is True
    assert result.decisions[-1].decision == "halt"
    assert "semantic drift" in result.decisions[-1].reason


def test_symbolic_drift_score_detects_unverified_observation_and_domain_change():
    score = score_drift(
        DriftSignal(
            changed_domain=True,
            unverified_observation_as_fact=True,
        )
    )

    assert score >= 0.40


def test_cumulative_drift_accumulates_without_exceeding_one():
    score = cumulative_drift(
        DriftSignal(changed_object=True),
        DriftSignal(changed_domain=True),
        DriftSignal(changed_external_consequence=True),
        DriftSignal(unverified_observation_as_fact=True),
    )

    assert 0.0 < score <= 1.0
    assert score >= 0.50
