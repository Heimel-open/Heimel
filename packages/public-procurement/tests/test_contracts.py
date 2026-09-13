import pytest

from valo_public_procurement import AwardRecommendation, ProcurementProcedure, Tender


def test_procedure_is_immutable_and_versioned():
    procedure = ProcurementProcedure("proc-1", "tenant-1", "OPEN_PROCEDURE", "PUBLISHED")
    assert procedure.schema_version == "v1"
    with pytest.raises(AttributeError):
        procedure.status = "AWARDED"


def test_digest_binds_domain_state():
    first = ProcurementProcedure("proc-1", "tenant-1", "OPEN_PROCEDURE", "PUBLISHED", policy_version="v1")
    second = ProcurementProcedure("proc-1", "tenant-1", "OPEN_PROCEDURE", "PUBLISHED", policy_version="v2")
    assert first.computed_digest != second.computed_digest


def test_recommendation_and_tender_preserve_provenance_without_authority():
    tender = Tender("t-1", "proc-1", "supplier-1", 100.0, "sri:t-1", "2026-01-01T00:00:00Z")
    recommendation = AwardRecommendation("r-1", "proc-1", tender.tender_id, "score", "criteria-v1", tender.computed_digest, "evaluator", "2026-01-02T00:00:00Z")
    assert recommendation.evaluation_digest == tender.computed_digest
    assert not hasattr(recommendation, "grants_authority")
