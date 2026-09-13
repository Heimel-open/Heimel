from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from valo_conformance import (
    GovernedPresentationClaimV1,
    GovernedPresentationEnvelopeV1,
    SurfaceConformanceObservationV1,
    evaluate_surface_conformance,
)


def digest(char: str) -> str:
    return "sha256:" + char * 64


def test_read_only_projection_passes_and_digest_is_bound():
    now = datetime(2026, 8, 12, 5, 0, tzinfo=timezone.utc)
    claim = GovernedPresentationClaimV1(
        claim_id="fact:1", subject="customer:1", predicate="status", value="active",
        truth_status="CONFIRMED", origin="kernel_state", evidence_refs=("e:1",), provenance_refs=("p:1",),
    )
    projection = GovernedPresentationEnvelopeV1(
        tenant_id="tenant-1", surface_id="ui-1", surface_type="ui", source_state_root=digest("a"),
        projected_at=now, fresh_until=now + timedelta(minutes=5), claims=(claim,),
    )
    projection = projection.model_copy(update={"envelope_digest": projection.computed_digest})
    report = evaluate_surface_conformance(
        SurfaceConformanceObservationV1(surface_id="ui-1", surface_type="ui", used_for_execution=True, current_kernel_state_root=digest("a")),
        presentation=projection, moment=now,
    )
    assert report.passed is True
    assert report.can_issue_clearance is False
    assert report.report_digest == report.computed_digest


def test_inference_and_external_evidence_cannot_be_confirmed():
    with pytest.raises(ValidationError):
        GovernedPresentationClaimV1(claim_id="x", subject="s", predicate="p", value=True, truth_status="CONFIRMED", origin="inference", inferred_by="m", confidence=0.9)
    with pytest.raises(ValidationError):
        GovernedPresentationClaimV1(claim_id="x", subject="s", predicate="p", value=True, truth_status="CONFIRMED", origin="external_evidence", evidence_refs=("e",), provenance_refs=("p",))


def test_boundary_violations_are_reported_without_granting_authority():
    report = evaluate_surface_conformance(SurfaceConformanceObservationV1(
        surface_id="adapter", surface_type="adapter", owns_authoritative_state=True,
        writes_world_state_directly=True, creates_authority=True, external_effect_claimed=True,
    ))
    assert report.passed is False
    assert "DIRECT_WORLD_STATE_WRITE" in report.findings
    assert report.authority_effect == "NO_AUTHORITY_CREATION"
