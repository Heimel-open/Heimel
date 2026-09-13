from valo_insurance_pack.contracts.assurance_profile import (
    ConsequenceClass,
)
from valo_insurance_pack.contracts.evaluation import (
    AssuranceResult,
    CommitAssuranceEvaluationV1,
)
from valo_insurance_pack.contracts.source_evidence import SourceAssuranceEvidenceV1
from valo_insurance_pack.telemetry.underwriting_telemetry import (
    UnderwritingTelemetryCollector,
)
from valo_insurance_pack.utils.crypto import utcnow


def test_telemetry_aggregation():
    collector = UnderwritingTelemetryCollector()
    now = utcnow()

    # Evaluation 1: Satisfied (High)
    e1 = CommitAssuranceEvaluationV1(
        action_ref="act-1",
        profile_ref="prof-1",
        assurance_result=AssuranceResult.SATISFIED,
        consequence_class=ConsequenceClass.HIGH.value,
        evaluated_at=now,
    )
    ev1 = SourceAssuranceEvidenceV1(
        source_id="entra_id",
        subject="user:1",
        observed_at=now,
        attestation_type="OIDC_FIDO2",
        provenance={"assurance_level": "HIGH_HARDWARE"},
    )
    collector.record_evaluation(e1, source_evidences=[ev1])

    # Evaluation 2: Step Up (High)
    e2 = CommitAssuranceEvaluationV1(
        action_ref="act-2",
        profile_ref="prof-1",
        assurance_result=AssuranceResult.STEP_UP_REQUIRED,
        unmet_requirements=["stale_evidence: budget age exceeds limit"],
        consequence_class=ConsequenceClass.HIGH.value,
        evaluated_at=now,
    )
    collector.record_evaluation(e2)

    # Evaluation 3: Denied (Critical)
    e3 = CommitAssuranceEvaluationV1(
        action_ref="act-3",
        profile_ref="prof-2",
        assurance_result=AssuranceResult.UNMET,
        unmet_requirements=["missing_required_source: compliance gate missing"],
        consequence_class=ConsequenceClass.CRITICAL.value,
        evaluated_at=now,
    )
    collector.record_evaluation(e3)

    # Incident
    collector.record_incident(
        incident_id="inc-1",
        action_ref="act-2",
        severity="LOW",
        details={"reason": "audit check"},
    )

    snapshot = collector.snapshot(now=now)

    assert snapshot.total_evaluations == 3
    assert snapshot.clearance_rate == round(1 / 3, 4)
    assert snapshot.step_up_rate == round(1 / 3, 4)
    assert snapshot.deny_rate == round(1 / 3, 4)
    assert snapshot.stale_evidence_rate == round(1 / 3, 4)
    assert snapshot.missing_evidence_rate == round(1 / 3, 4)
    assert snapshot.consequence_exposure[ConsequenceClass.HIGH.value] == 2
    assert snapshot.consequence_exposure[ConsequenceClass.CRITICAL.value] == 1
    assert len(snapshot.incidents_correlated_to_assurance_state) == 1
    # Check that no pricing fields exist
    assert not hasattr(snapshot, "premium")
    assert not hasattr(snapshot, "price")


def test_telemetry_counts_revoked_evidence():
    """P1 test: revoked_evidence_rate reflects revoked_or_unverified_evidence findings."""
    collector = UnderwritingTelemetryCollector()
    now = utcnow()

    e1 = CommitAssuranceEvaluationV1(
        action_ref="act-r1",
        profile_ref="prof-1",
        assurance_result=AssuranceResult.STEP_UP_REQUIRED,
        unmet_requirements=[
            "revoked_or_unverified_evidence: source 'entra_id' status is REVOKED"
        ],
        consequence_class=ConsequenceClass.HIGH.value,
        evaluated_at=now,
    )
    collector.record_evaluation(e1)

    snapshot = collector.snapshot(now=now)
    assert snapshot.revoked_evidence_rate == 1.0
