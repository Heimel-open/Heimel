from datetime import datetime, timezone

from src.valo_platform.models.core_receipt import ExecutionDecision
from src.valo_platform.governed_newsroom import (
    build_future_newsroom_pilot,
    persist_newsroom_shadow,
)
from src.valo_platform.verification_factory import (
    ClaimDisposition,
    IntegrityPreconditionDisposition,
    SQLiteVerificationStore,
)


NOW = datetime(2026, 7, 23, 18, 30, tzinfo=timezone.utc)


def test_reviewed_study_is_modified_market_context_not_general_proof() -> None:
    pilot = build_future_newsroom_pilot(
        human_review_completed=True,
        now=NOW,
    )
    evaluation = pilot.evaluation

    assert evaluation.admissibility.disposition is ClaimDisposition.PARTIALLY_SUPPORTED
    assert evaluation.shadow_reht_recommendation is ExecutionDecision.MODIFY
    assert evaluation.claim_preconditions.ready is True
    assert set(evaluation.evidence_package.permissible_uses) == {
        "industry-context",
        "market-signal",
    }
    assert "sole-basis-for-causal-claim" in evaluation.prohibited_uses
    assert "product-effectiveness-proof" in evaluation.prohibited_uses
    assert evaluation.evidence_package.package_digest.startswith("sha256:")


def test_unreviewed_material_use_steps_up_to_accountable_editor() -> None:
    pilot = build_future_newsroom_pilot(
        human_review_completed=False,
        now=NOW,
    )
    evaluation = pilot.evaluation

    assert evaluation.shadow_reht_recommendation is ExecutionDecision.STEP_UP
    assert any(
        "Accountable editor review required" in condition
        for condition in evaluation.required_conditions
    )


def test_pilot_exposes_funding_ai_origin_and_bias_unknowns() -> None:
    pilot = build_future_newsroom_pilot(now=NOW)
    evaluation = pilot.evaluation
    source_result = next(iter(evaluation.source_preconditions.values()))
    card = evaluation.public_integrity_cards[0]

    assert source_result.disposition is IntegrityPreconditionDisposition.REVIEW
    assert {failure.code for failure in source_result.failures} == {
        "UNRESOLVED_BIAS_SIGNALS"
    }
    assert card.ai_disclosure_status.value == "UNKNOWN"
    assert card.ultimate_funder_refs == [
        "Arc XP: support disclosed, financial terms unknown"
    ]
    assert {dimension.value for dimension in card.bias_dimensions} == {
        "COMMERCIAL_INTEREST",
        "SAMPLE",
    }
    assert "trust_score" not in type(card).model_fields
    assert "bias_score" not in type(card).model_fields
    assert "conflict_score" not in type(card).model_fields


def test_shadow_output_contains_no_clearance_or_execution_authority() -> None:
    pilot = build_future_newsroom_pilot(now=NOW)
    payload = pilot.evaluation.model_dump(mode="json")

    assert "governance_clearance" not in payload
    assert "execution_authorization" not in payload
    assert "commit_token" not in payload
    assert payload["governance_inputs"]["publication_authority_ref"]["digest"].startswith(
        "sha256:"
    )


def test_pilot_persists_and_replays_after_store_restart(tmp_path) -> None:
    pilot = build_future_newsroom_pilot(now=NOW)
    db_path = tmp_path / "future-newsroom.sqlite3"
    first = SQLiteVerificationStore(db_path, tenant_id=pilot.case.tenant_id)

    receipt = persist_newsroom_shadow(
        first,
        case=pilot.case,
        evaluation=pilot.evaluation,
    )

    reopened = SQLiteVerificationStore(db_path, tenant_id=pilot.case.tenant_id)
    case_state = reopened.get_case(pilot.case.case_id)
    events = reopened.list_events(pilot.case.case_id)
    checkpoint = reopened.get_latest_checkpoint(
        pilot.case.case_id,
        "NEWSROOM_EVIDENCE_READY",
    )
    package_bytes = reopened.get_artifact(receipt["evidence_package_ref"])

    assert case_state["version"] == 2
    assert [event.event_type for event in events] == [
        "NEWSROOM_SHADOW_EVALUATED",
        "CHECKPOINT",
    ]
    assert checkpoint.state["recommendation"] == ExecutionDecision.MODIFY.value
    assert pilot.evaluation.evidence_package.package_digest.encode() in package_bytes
