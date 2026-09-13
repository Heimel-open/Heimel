import pytest
from valo_platform.mentor_ai.mentor_models import KnownOutcomeV1, HistoricalCaseV1
from valo_platform.mentor_ai.scrambler import AnonymizationScramblingEngine, CaseIntegrityValidator
from valo_platform.mentor_ai.mentor_runtime import MentorAIRuntime, MentorMode
from valo_platform.mentor_ai.independent_judge import IndependentMentorJudge


def test_mentor_e2e_training_lifecycle():
    # 1. Historical Case Intake
    outcome = KnownOutcomeV1(
        actual_outcome_summary="Tender evaluation awarded to Vendor B based on quality criteria weighting.",
        expert_decision_rationale="Vendor B scored 92% on technical delivery risk versus Vendor A 74%.",
        acceptable_alternatives=("RE_TENDER_WITH_REVISED_SPECIFICATION",),
    )
    hist_case = HistoricalCaseV1(
        case_id="case-procurement-2025-09",
        tenant_id="ten-oslo-kommune",
        domain="public_procurement",
        raw_content_digest="sha256:procraw101",
        known_outcome=outcome,
        legal_basis_approved=True,
    )

    raw_text = "Oslo Kommune evaluated tender proposals from Equinor AS and DNB Markets regarding IT infrastructure."
    forbidden = ("Oslo Kommune", "Equinor AS", "DNB Markets")

    # 2. Anonymization & Scrambling
    scrambler = AnonymizationScramblingEngine(seed="e2e_seed_99")
    scrambled_case, mapping = scrambler.scramble(hist_case, raw_text, additional_entities=forbidden)

    # 3. Integrity Validation (no PII leak)
    validator = CaseIntegrityValidator(forbidden_terms=forbidden)
    valid, violations = validator.validate(scrambled_case)
    assert valid is True
    assert len(violations) == 0

    # 4. Mentor AI Runtime (Socratic Coaching)
    runtime = MentorAIRuntime(mode=MentorMode.GUIDED)
    junior_draft = "I think we should award Vendor B based on general intuition."
    feedback = runtime.generate_feedback(scrambled_case, junior_draft)

    assert any("Socratic Challenge" in f for f in feedback)

    # 5. Independent Judge Evaluation
    junior_final = "Following public procurement evaluation methodology and evidence document 4, we evaluate Vendor B technical risk with uncertainty bounds."
    judge = IndependentMentorJudge()
    eval_report = judge.evaluate(scrambled_case, junior_final, hist_case)

    assert eval_report.overall_score >= 0.85
    assert eval_report.method_score == 0.90
    assert eval_report.scrambled_case_id == scrambled_case.scrambled_case_id
