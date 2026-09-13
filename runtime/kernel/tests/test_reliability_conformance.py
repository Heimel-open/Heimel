import pytest
from pydantic import ValidationError

from valo_kernel.reliability import (
    HEALTHCARE_RELIABILITY_PACK_V1,
    ReliabilityObservation,
    ReliabilityOutcome,
    ReliabilityScenario,
    ReliabilityScenarioKind,
    evaluate_reliability,
)


def _observation(scenario: ReliabilityScenario) -> ReliabilityObservation:
    transitioned = dict(scenario.baseline_state)
    transitioned.update(scenario.controlled_change)
    return ReliabilityObservation(
        scenario_id=scenario.scenario_id,
        baseline_state=scenario.baseline_state,
        transitioned_state=transitioned,
        observed_behavior=scenario.expected_behavior,
        evidence={key: {"present": True} for key in scenario.required_evidence},
    )


@pytest.mark.parametrize("scenario", HEALTHCARE_RELIABILITY_PACK_V1.scenarios)
def test_healthcare_profile_passes_expected_behavior(
    scenario: ReliabilityScenario,
) -> None:
    first = evaluate_reliability(scenario, _observation(scenario))
    second = evaluate_reliability(scenario, _observation(scenario))

    assert first.outcome is ReliabilityOutcome.PASS
    assert first.eligible_for_separate_authorization is True
    assert first.authorization_effect == "NO_AUTHORITY_CREATION"
    assert first == second


def test_stale_behavior_fails_without_creating_authority() -> None:
    scenario = HEALTHCARE_RELIABILITY_PACK_V1.scenarios[0]
    observation = _observation(scenario).model_copy(
        update={
            "observed_behavior": {
                "recommend_medication": True,
                "request_review": False,
            }
        }
    )

    report = evaluate_reliability(scenario, observation)

    assert report.outcome is ReliabilityOutcome.FAIL
    assert report.eligible_for_separate_authorization is False
    assert report.authorization_effect == "NO_AUTHORITY_CREATION"
    assert report.findings[0].code == "EXPECTED_BEHAVIOR_MISMATCH"


def test_missing_evidence_is_insufficient_not_pass() -> None:
    scenario = HEALTHCARE_RELIABILITY_PACK_V1.scenarios[1]
    observation = _observation(scenario).model_copy(update={"evidence": {}})

    report = evaluate_reliability(scenario, observation)

    assert report.outcome is ReliabilityOutcome.INSUFFICIENT_EVIDENCE
    assert report.eligible_for_separate_authorization is False
    assert report.findings[0].code == "MISSING_EVIDENCE"


def test_uncontrolled_second_change_fails() -> None:
    scenario = HEALTHCARE_RELIABILITY_PACK_V1.scenarios[2]
    observation = _observation(scenario).model_copy(
        update={
            "transitioned_state": {
                "transfer_status": "COMPLETED",
                "untracked_summary": "changed",
            }
        }
    )

    report = evaluate_reliability(scenario, observation)

    assert report.outcome is ReliabilityOutcome.FAIL
    assert report.findings[0].code == "UNCONTROLLED_STATE_TRANSITION"


def test_scenario_rejects_more_than_one_controlled_change() -> None:
    with pytest.raises(ValidationError):
        ReliabilityScenario(
            scenario_id="invalid",
            profile_id="test",
            kind=ReliabilityScenarioKind.STATE_CHANGE,
            invariant="only one condition changes",
            baseline_state={"a": 1, "b": 1},
            controlled_change={"a": 2, "b": 2},
            expected_behavior={"safe": True},
        )
