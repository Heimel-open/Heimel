import pytest
from valo_platform.mentor_ai.mentor_models import ScrambledCaseV1
from valo_platform.mentor_ai.independent_judge import IndependentMentorJudge


def test_independent_judge_evaluates_methodology():
    judge = IndependentMentorJudge()
    scrambled = ScrambledCaseV1(
        scrambled_case_id="scram-101",
        original_case_id="case-101",
        domain="tax_audit",
        scrambled_scenario_text="Scenario text...",
        evidence_digests=("sha256:ev1",),
        scrambled_entity_mapping_digest="sha256:map1",
    )

    response = "Based on evidence doc A, following our audit methodology, there is uncertainty regarding risk factor 2. Escalation to senior is advised."
    report = judge.evaluate(scrambled, response)

    assert report.method_score == 0.90
    assert report.evidence_score == 0.95
    assert report.overall_score >= 0.85
    assert len(report.computed_digest) == 64
