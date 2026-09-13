from dataclasses import replace

import pytest

from vaig.aarm import AARMVerdict
from vaig.normative_governance import (
    ConsequenceClass,
    EvaluatorCorrelationRisk,
    NormativeArtifactBindingsV1,
    NormativeGovernanceGateV1,
    NormativeHandoffDisposition,
    NormativeResearchSignalsV1,
    NormativeSensitivity,
    ResearchGateDecision,
)


D = "a" * 64


def artifacts(**overrides):
    values = {
        "research_report_ref": "research:report:1",
        "research_report_digest": D,
        "model_power_shadow_profile_digest": "b" * 64,
        "counterposition_bundle_digest": "c" * 64,
        "adversarial_evaluation_digest": "d" * 64,
        "normative_scorecard_digest": "e" * 64,
        "normative_influence_profile_digests": ("f" * 64,),
    }
    values.update(overrides)
    return NormativeArtifactBindingsV1(**values)


def signals(**overrides):
    values = {
        "sensitivity": NormativeSensitivity.POLITICAL,
        "consequence_class": ConsequenceClass.HIGH,
        "counterposition_required": True,
        "counterposition_decision": ResearchGateDecision.ACCEPTED,
        "adversarial_evaluation_decision": ResearchGateDecision.ACCEPTED,
        "scorecard_decision": ResearchGateDecision.ACCEPTED,
        "evaluator_correlation_risk": EvaluatorCorrelationRisk.LOW,
        "independent_evaluator_present": True,
    }
    values.update(overrides)
    return NormativeResearchSignalsV1(**values)


def evaluate(*, bound=None, observed=None):
    return NormativeGovernanceGateV1().evaluate(
        report_id="normative-handoff-1",
        source_evaluation_report_ref="vaig:evaluation:1",
        source_evaluation_report_digest="1" * 64,
        artifact_bindings=bound or artifacts(),
        signals=observed or signals(),
    )


def test_accepted_controls_do_not_create_allow_authority():
    handoff = evaluate()

    assert handoff.disposition is NormativeHandoffDisposition.NO_OVERRIDE
    assert handoff.recommended_aarm_verdict is None
    assert handoff.execution_authority is False
    assert handoff.requires_reht_clearance is True
    assert handoff.blocks_clearance is False


def test_missing_required_counterposition_defers():
    handoff = evaluate(
        bound=artifacts(counterposition_bundle_digest=None),
    )

    assert handoff.recommended_aarm_verdict is AARMVerdict.DEFER
    assert "COUNTERPOSITION_BINDING_MISSING" in handoff.reason_codes
    assert handoff.blocks_clearance is True


def test_deferred_scorecard_defers():
    handoff = evaluate(
        observed=signals(scorecard_decision=ResearchGateDecision.DEFER),
    )

    assert handoff.disposition is NormativeHandoffDisposition.DEFER
    assert "NORMATIVE_SCORECARD_DEFERRED" in handoff.reason_codes


def test_missing_independent_evaluator_defers():
    handoff = evaluate(
        observed=signals(independent_evaluator_present=False),
    )

    assert handoff.recommended_aarm_verdict is AARMVerdict.DEFER
    assert "INDEPENDENT_EVALUATOR_MISSING" in handoff.reason_codes


@pytest.mark.parametrize(
    "risk",
    [EvaluatorCorrelationRisk.HIGH, EvaluatorCorrelationRisk.CRITICAL],
)
def test_correlated_evaluator_defers(risk):
    handoff = evaluate(observed=signals(evaluator_correlation_risk=risk))

    assert handoff.recommended_aarm_verdict is AARMVerdict.DEFER
    assert "EVALUATOR_CORRELATION_RISK_TOO_HIGH" in handoff.reason_codes


def test_unresolved_consequential_conflict_steps_up():
    handoff = evaluate(
        observed=signals(unresolved_normative_conflict=True),
    )

    assert handoff.recommended_aarm_verdict is AARMVerdict.STEP_UP
    assert handoff.required_authority_class == "HUMAN_ACCOUNTABLE_OWNER"
    assert handoff.reason_codes == ("UNRESOLVED_NORMATIVE_CONFLICT",)


def test_incomplete_evaluation_takes_precedence_over_step_up():
    handoff = evaluate(
        observed=signals(
            unresolved_normative_conflict=True,
            adversarial_evaluation_decision=ResearchGateDecision.DEFER,
        ),
    )

    assert handoff.recommended_aarm_verdict is AARMVerdict.DEFER
    assert handoff.required_authority_class is None


def test_low_consequence_conflict_does_not_create_step_up():
    handoff = evaluate(
        observed=signals(
            consequence_class=ConsequenceClass.LOW,
            unresolved_normative_conflict=True,
        ),
    )

    assert handoff.disposition is NormativeHandoffDisposition.NO_OVERRIDE


def test_bare_digests_are_normalized_and_invalid_digest_fails():
    bound = artifacts()
    assert bound.research_report_digest == "sha256:" + D
    assert bound.counterposition_bundle_digest == "sha256:" + "c" * 64

    with pytest.raises(ValueError, match="SHA-256"):
        artifacts(research_report_digest="not-a-digest")


def test_handoff_digest_is_replayable_and_content_bound():
    first = evaluate()
    second = evaluate()
    changed = evaluate(
        observed=replace(signals(), consequence_class=ConsequenceClass.CRITICAL)
    )

    assert first.canonical_json() == second.canonical_json()
    assert first.handoff_digest() == second.handoff_digest()
    assert first.handoff_digest() != changed.handoff_digest()
    binding = first.receipt_binding()
    assert binding["handoff_digest"] == first.handoff_digest()
    assert binding["execution_authority"] is False
