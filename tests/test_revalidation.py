from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import ActionDecision, ClearanceState
from src.valo_platform.decision_governance.continuity import (
    ContinuityBasisSnapshot,
    ContinuityContractError,
    ContinuityImpactAssessment,
    ContinuityIntegrityStatus,
    ContinuityMateriality,
    ContinuitySeverity,
    ContinuityTrigger,
    ContinuityTriggerKind,
)
from src.valo_platform.operational_continuity.observers import ObservationBinding
from src.valo_platform.operational_continuity.revalidation import (
    ContinuityCurrentFingerprints,
    build_revalidation_request,
    evaluate_revalidation_request,
    validate_vaig_assessment,
)
from src.valo_platform.operational_continuity.source_adapters import (
    ContinuitySourceBundle,
    ContinuitySourceDomain,
    ContinuitySourceObservation,
)
from src.valo_platform.operational_continuity.source_baselines import (
    ContinuitySourceBaseline,
    ContinuitySourceBaselineEntry,
)


NOW = datetime(2026, 8, 1, 13, 0, tzinfo=timezone.utc)
CURRENT = {
    "authority": "sha256:authority",
    "policy": "sha256:policy",
    "context": "sha256:context",
    "state": "sha256:case",
    "evidence": "sha256:evidence",
}


def observation_binding(**updates):
    data = dict(
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash=CURRENT["state"],
        clearance_ref="clearance-1",
        observer_ref="observer:pre-commit",
    )
    data.update(updates)
    return ObservationBinding(**data)


def basis():
    return ContinuityBasisSnapshot(
        snapshot_id="basis-1",
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash=CURRENT["state"],
        clearance_ref="clearance-1",
        observed_at=NOW - timedelta(minutes=10),
        authority_fingerprint=CURRENT["authority"],
        policy_fingerprint=CURRENT["policy"],
        evidence_fingerprint=CURRENT["evidence"],
        context_fingerprint=CURRENT["context"],
        state_fingerprint=CURRENT["state"],
        purpose_binding_ref="purpose:1",
        valid_until=NOW + timedelta(hours=1),
    )


def baseline_entry(
    domain=ContinuitySourceDomain.POLICY,
    source_ref="source:policy",
    fingerprint="sha256:source-policy",
):
    return ContinuitySourceBaselineEntry(
        domain=domain,
        source_ref=source_ref,
        fingerprint=fingerprint,
        evidence_refs=(f"evidence:{source_ref}",),
        captured_at=NOW - timedelta(minutes=11),
    )


def source_baseline(entries=None, binding=None):
    return ContinuitySourceBaseline(
        binding=binding or observation_binding(),
        captured_at=NOW - timedelta(minutes=10),
        entries=tuple(entries or (baseline_entry(),)),
    )


def source_observation(
    *,
    domain=ContinuitySourceDomain.POLICY,
    source_ref="source:policy",
    expected="sha256:source-policy",
    current="sha256:source-policy",
    integrity="verified",
    trigger=None,
):
    return ContinuitySourceObservation(
        domain=domain,
        source_ref=source_ref,
        expected_fingerprint=expected,
        current_fingerprint=current,
        observed_at=NOW - timedelta(seconds=5),
        changed_fields=trigger.changed_fields if trigger is not None else (),
        evidence_refs=(f"evidence:{source_ref}",),
        integrity_status=integrity,
        trigger=trigger,
    )


def source_bundle(observations=None, binding=None):
    return ContinuitySourceBundle(
        binding=binding or observation_binding(),
        observed_at=NOW - timedelta(seconds=4),
        observations=tuple(observations or (source_observation(),)),
    )


def request(*, baseline=None, bundle=None, current=None):
    return build_revalidation_request(
        request_id="revalidation-1",
        requester_ref="execution-gateway:1",
        basis=basis(),
        source_baseline=baseline or source_baseline(),
        source_bundle=bundle or source_bundle(),
        current_fingerprints=current or CURRENT,
        requested_at=NOW,
    )


def assessment(current_request, **updates):
    data = dict(
        assessment_id="assessment-1",
        tenant_id="tenant-1",
        trigger_refs=tuple(
            trigger.trigger_id for trigger in current_request.triggers
        ),
        action_case_id="case-1",
        action_case_hash=CURRENT["state"],
        clearance_ref="clearance-1",
        materiality=ContinuityMateriality.NO_MATERIAL_CHANGE,
        impact_dimensions=("operational_continuity",),
        reason_codes=("all_sources_revalidated",),
        evidence_refs=(current_request.evidence_ref,),
        assessor_refs=("vaig:continuity",),
        confidence=1.0,
        assessed_at=NOW + timedelta(seconds=1),
    )
    data.update(updates)
    return ContinuityImpactAssessment(**data)


def test_stable_sources_create_explicit_checkpoint_and_allow_after_vaig():
    current_request = request()
    assert len(current_request.triggers) == 1
    checkpoint = current_request.triggers[0]
    assert checkpoint.trigger_kind == ContinuityTriggerKind.REVALIDATION_CHECKPOINT
    assert checkpoint.severity == ContinuitySeverity.INFO
    assert checkpoint.integrity_status == ContinuityIntegrityStatus.VERIFIED
    assert checkpoint.previous_fingerprint == checkpoint.current_fingerprint

    result = evaluate_revalidation_request(
        request=current_request,
        assessment=assessment(current_request),
        clearance_state=ClearanceState.ACTIVE,
        now=NOW + timedelta(seconds=2),
        decider_ref="reht:continuity",
        decision_authority_ref="authority:reht",
    )
    assert result.decision.racs_outcome == ActionDecision.ALLOW
    assert current_request.evidence_ref in result.decision.evidence_refs


def test_source_drift_trigger_is_preserved_and_authority_drift_denies():
    drift_trigger = ContinuityTrigger(
        trigger_id="mandate-drift-1",
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash=CURRENT["state"],
        clearance_ref="clearance-1",
        trigger_kind=ContinuityTriggerKind.MANDATE_CHANGED,
        severity=ContinuitySeverity.HIGH,
        source_ref="source:mandate",
        observer_ref="observer:pre-commit",
        observed_at=NOW - timedelta(seconds=5),
        previous_fingerprint="sha256:source-mandate",
        current_fingerprint="sha256:source-mandate-new",
        changed_fields=("mandate",),
        source_evidence_refs=("evidence:source:mandate",),
        confidence=1.0,
        freshness=1.0,
        integrity_status=ContinuityIntegrityStatus.VERIFIED,
    )
    baseline = source_baseline(
        entries=(
            baseline_entry(
                domain=ContinuitySourceDomain.MANDATE,
                source_ref="source:mandate",
                fingerprint="sha256:source-mandate",
            ),
        )
    )
    bundle = source_bundle(
        observations=(
            source_observation(
                domain=ContinuitySourceDomain.MANDATE,
                source_ref="source:mandate",
                expected="sha256:source-mandate",
                current="sha256:source-mandate-new",
                trigger=drift_trigger,
            ),
        )
    )
    current_request = request(
        baseline=baseline,
        bundle=bundle,
        current={**CURRENT, "authority": "sha256:authority-new"},
    )
    assert current_request.triggers == (drift_trigger,)

    result = evaluate_revalidation_request(
        request=current_request,
        assessment=assessment(
            current_request,
            materiality=ContinuityMateriality.MATERIAL_CHANGE,
        ),
        clearance_state=ClearanceState.ACTIVE,
        now=NOW + timedelta(seconds=2),
        decider_ref="reht:continuity",
        decision_authority_ref="authority:reht",
    )
    assert result.decision.racs_outcome == ActionDecision.DENY


def test_failed_integrity_checkpoint_can_never_allow():
    current_request = request(
        bundle=source_bundle(
            observations=(source_observation(integrity="failed"),)
        )
    )
    checkpoint = current_request.triggers[0]
    assert checkpoint.integrity_status == ContinuityIntegrityStatus.FAILED
    assert checkpoint.freshness == 0.0

    result = evaluate_revalidation_request(
        request=current_request,
        assessment=assessment(current_request),
        clearance_state=ClearanceState.ACTIVE,
        now=NOW + timedelta(seconds=2),
        decider_ref="reht:continuity",
        decision_authority_ref="authority:reht",
    )
    assert result.decision.racs_outcome == ActionDecision.DEFER


def test_complete_source_coverage_is_required():
    baseline = source_baseline(
        entries=(
            baseline_entry(),
            baseline_entry(
                domain=ContinuitySourceDomain.EVIDENCE,
                source_ref="source:evidence",
                fingerprint="sha256:source-evidence",
            ),
        )
    )
    with pytest.raises(ContinuityContractError, match="incomplete source"):
        request(baseline=baseline)


def test_source_observation_must_bind_exact_baseline_fingerprint():
    with pytest.raises(ContinuityContractError, match="baseline fingerprint"):
        request(
            bundle=source_bundle(
                observations=(
                    source_observation(
                        expected="sha256:other-baseline",
                        current="sha256:other-baseline",
                    ),
                )
            )
        )


def test_cross_case_source_binding_is_rejected():
    foreign = observation_binding(action_case_id="other-case")
    with pytest.raises(ContinuityContractError, match="source bundle"):
        request(bundle=source_bundle(binding=foreign))


def test_vaig_assessment_must_reference_exact_request_and_trigger_set():
    current_request = request()
    missing_request_ref = assessment(
        current_request,
        evidence_refs=("evidence:other",),
    )
    with pytest.raises(ContinuityContractError, match="does not reference"):
        validate_vaig_assessment(current_request, missing_request_ref)

    wrong_trigger = assessment(current_request, trigger_refs=("trigger:other",))
    with pytest.raises(ContinuityContractError, match="trigger set"):
        validate_vaig_assessment(current_request, wrong_trigger)


def test_vaig_assessment_cannot_predate_request():
    current_request = request()
    stale = assessment(
        current_request,
        assessed_at=NOW - timedelta(seconds=1),
    )
    with pytest.raises(ContinuityContractError, match="predate"):
        validate_vaig_assessment(current_request, stale)


def test_current_fingerprint_contract_is_exact_and_complete():
    with pytest.raises(ContinuityContractError, match="missing"):
        ContinuityCurrentFingerprints.from_mapping(
            {key: value for key, value in CURRENT.items() if key != "evidence"}
        )
    with pytest.raises(ContinuityContractError, match="unknown"):
        ContinuityCurrentFingerprints.from_mapping(
            {**CURRENT, "dependency": "sha256:dependency"}
        )
