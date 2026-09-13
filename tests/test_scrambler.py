import pytest
from valo_platform.mentor_ai.mentor_models import KnownOutcomeV1, HistoricalCaseV1, ScrambledCaseV1
from valo_platform.mentor_ai.scrambler import AnonymizationScramblingEngine, CaseIntegrityValidator


def make_historical_case():
    outcome = KnownOutcomeV1(
        actual_outcome_summary="Audit approved",
        expert_decision_rationale="Methodology accepted",
        acceptable_alternatives=(),
    )
    return HistoricalCaseV1(
        case_id="case-equinor-2024",
        tenant_id="ten-audit",
        domain="tax_audit",
        raw_content_digest="sha256:raw999",
        known_outcome=outcome,
        legal_basis_approved=True,
    )


def test_scrambling_engine_replaces_entities():
    engine = AnonymizationScramblingEngine(seed="seed123")
    case = make_historical_case()
    raw_text = "Equinor was audited regarding transfer pricing for Kari Nordmann."

    scrambled_case, mapping = engine.scramble(case, raw_text)

    assert "Equinor" not in scrambled_case.scrambled_scenario_text
    assert "Kari Nordmann" not in scrambled_case.scrambled_scenario_text
    assert "Energy Corp" in scrambled_case.scrambled_scenario_text


def test_case_integrity_validator_detects_leaks():
    validator = CaseIntegrityValidator(forbidden_terms=("Equinor", "Norsk Hydro", "Kari Nordmann"))

    # Construct a scrambled case where an un-anonymized term leaked
    leaky_scrambled_case = ScrambledCaseV1(
        scrambled_case_id="scram-101",
        original_case_id="case-equinor-2024",
        domain="tax_audit",
        scrambled_scenario_text="Norsk Hydro provided financial statements for the case.",
        evidence_digests=("sha256:ev1",),
        scrambled_entity_mapping_digest="sha256:map1",
    )

    valid, violations = validator.validate(leaky_scrambled_case)
    assert valid is False
    assert any("Norsk Hydro" in v for v in violations)
