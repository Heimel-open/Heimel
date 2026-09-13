import pytest
from valo_platform.mentor_ai.mentor_models import KnownOutcomeV1, HistoricalCaseV1, ScrambledCaseV1


def test_historical_case_immutability():
    outcome = KnownOutcomeV1(
        actual_outcome_summary="Tax audit approved with NOK 450k adjustment",
        expert_decision_rationale="Accepted transfer pricing methodology after documentation review",
        acceptable_alternatives=("ALLOW_WITH_REVISED_BENCHMARK",),
    )
    case = HistoricalCaseV1(
        case_id="hist-case-101",
        tenant_id="ten-audit-01",
        domain="tax_audit",
        raw_content_digest="sha256:raw123",
        known_outcome=outcome,
        legal_basis_approved=True,
    )

    assert case.case_id == "hist-case-101"
    assert case.known_outcome.actual_outcome_summary.startswith("Tax audit approved")

    with pytest.raises(AttributeError):
        case.legal_basis_approved = False


def test_scrambled_case_canonical_digest():
    scrambled = ScrambledCaseV1(
        scrambled_case_id="scram-101",
        original_case_id="hist-case-101",
        domain="tax_audit",
        scrambled_scenario_text="Company Alpha AS reviewed for fiscal period 2024...",
        evidence_digests=("sha256:ev1", "sha256:ev2"),
        scrambled_entity_mapping_digest="sha256:map123",
    )

    digest = scrambled.computed_digest
    assert isinstance(digest, str)
    assert len(digest) == 64
