import pytest
from valo_platform.mentor_ai.mentor_models import ScrambledCaseV1
from valo_platform.mentor_ai.mentor_runtime import MentorAIRuntime, MentorMode


def make_scrambled_case():
    return ScrambledCaseV1(
        scrambled_case_id="scram-101",
        original_case_id="case-101",
        domain="tax_audit",
        scrambled_scenario_text="Company Alpha reviewed...",
        evidence_digests=("sha256:ev1",),
        scrambled_entity_mapping_digest="sha256:map1",
    )


def test_mentor_socratic_probing():
    runtime = MentorAIRuntime(mode=MentorMode.GUIDED)
    case = make_scrambled_case()

    # Response missing evidence justification and overconfident
    response = "I am 100% certain the tax adjustment should be denied."
    feedback = runtime.generate_feedback(case, response)

    assert any("Socratic Challenge" in f for f in feedback)
    assert any("Uncertainty Calibration" in f for f in feedback)


def test_mentor_observer_only_mode():
    runtime = MentorAIRuntime(mode=MentorMode.OBSERVER_ONLY)
    case = make_scrambled_case()

    feedback = runtime.generate_feedback(case, "Weak answer")
    assert len(feedback) == 0
