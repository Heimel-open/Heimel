from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import (
    ActionDecision,
    ClearanceState,
)
from src.valo_platform.action_envelope.transition_models import (
    RevisionType,
    TargetStateBinding,
)
from src.valo_platform.decision_governance.continuity import (
    ContinuityBasisSnapshot,
    ContinuityImpactAssessment,
    ContinuityMateriality,
    ContinuitySeverity,
    ContinuityTriggerKind,
)
from src.valo_platform.operational_continuity.fingerprint_snapshot import (
    CallableDecisionFingerprintReader,
    CompositeCurrentDecisionFingerprintProvider,
    DecisionFingerprintKind,
    DecisionFingerprintObservation,
)
from src.valo_platform.operational_continuity.observers import (
    FingerprintObserver,
    ObservationBinding,
)
from src.valo_platform.operational_continuity.runtime import (
    CallableVaigContinuityAssessmentPort,
    OperationalContinuityRuntime,
    OperationalContinuityRuntimeError,
    RuntimeContinuitySourceHandle,
    target_state_runtime_source,
)
from src.valo_platform.operational_continuity.source_adapters import (
    ContinuitySourceDomain,
    ContinuitySourceObservation,
    TargetStateSourceAdapter,
    target_state_fingerprint,
)
from src.valo_platform.operational_continuity.source_baselines import (
    ContinuitySourceBaseline,
    ContinuitySourceBaselineEntry,
)


NOW = datetime(2026, 8, 1, 15, 20, tzinfo=timezone.utc)
CURRENT = {
    "authority": "sha256:authority",
    "policy": "sha256:policy",
    "context": "sha256:context",
    "state": "sha256:case",
    "evidence": "sha256:evidence",
}
SOURCE_REF = "publication-policy-registry:tenant-1:policy-1:1"
SOURCE_FINGERPRINT = "sha256:source-policy"


def observation_binding() -> ObservationBinding:
    return ObservationBinding(
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash=CURRENT["state"],
        clearance_ref="clearance-1",
        observer_ref="runtime:commit-boundary",
    )


def basis() -> ContinuityBasisSnapshot:
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
        purpose_binding_ref="purpose-binding-1",
        valid_until=NOW + timedelta(hours=1),
    )


def baseline() -> ContinuitySourceBaseline:
    captured_at = NOW - timedelta(minutes=10)
    return ContinuitySourceBaseline(
        binding=observation_binding(),
        captured_at=captured_at,
        entries=(
            ContinuitySourceBaselineEntry(
                domain=ContinuitySourceDomain.POLICY,
                source_ref=SOURCE_REF,
                fingerprint=SOURCE_FINGERPRINT,
                evidence_refs=("policy-registry:event-1",),
                captured_at=captured_at,
            ),
        ),
    )


def stable_source() -> RuntimeContinuitySourceHandle:
    def read(expected: str, observed_at: datetime) -> ContinuitySourceObservation:
        return ContinuitySourceObservation(
            domain=ContinuitySourceDomain.POLICY,
            source_ref=SOURCE_REF,
            expected_fingerprint=expected,
            current_fingerprint=expected,
            observed_at=observed_at,
            evidence_refs=("policy-registry:event-1",),
        )

    return RuntimeContinuitySourceHandle(
        domain=ContinuitySourceDomain.POLICY,
        source_ref=SOURCE_REF,
        reader=read,
    )


def changed_source() -> RuntimeContinuitySourceHandle:
    current = "sha256:changed-source-policy"

    def read(expected: str, observed_at: datetime) -> ContinuitySourceObservation:
        trigger = FingerprintObserver(
            binding=observation_binding(),
            source_ref=SOURCE_REF,
            trigger_kind=ContinuityTriggerKind.POLICY_CHANGED,
            severity=ContinuitySeverity.HIGH,
        ).observe(
            previous_fingerprint=expected,
            current_fingerprint=current,
            observed_at=observed_at,
            changed_fields=("registered_policy_snapshot",),
            evidence_refs=("policy-registry:event-2",),
        )
        return ContinuitySourceObservation(
            domain=ContinuitySourceDomain.POLICY,
            source_ref=SOURCE_REF,
            expected_fingerprint=expected,
            current_fingerprint=current,
            observed_at=observed_at,
            changed_fields=("registered_policy_snapshot",),
            evidence_refs=("policy-registry:event-2",),
            trigger=trigger,
        )

    return RuntimeContinuitySourceHandle(
        domain=ContinuitySourceDomain.POLICY,
        source_ref=SOURCE_REF,
        reader=read,
    )


def current_provider():
    readers = []
    for kind in DecisionFingerprintKind:
        def read(binding, observed_at, kind=kind):
            return DecisionFingerprintObservation(
                binding=binding,
                kind=kind,
                fingerprint=CURRENT[kind.value],
                source_ref=f"{kind.value}-owner:tenant-1",
                reader_ref=f"{kind.value}-reader:1",
                evidence_refs=(f"evidence:{kind.value}",),
                observed_at=observed_at,
            )

        readers.append(
            CallableDecisionFingerprintReader(
                kind=kind,
                reader=read,
            )
        )
    return CompositeCurrentDecisionFingerprintProvider(tuple(readers))


class RecordingVaig:
    def __init__(
        self,
        materiality: ContinuityMateriality = ContinuityMateriality.NO_MATERIAL_CHANGE,
        *,
        bind_request: bool = True,
    ) -> None:
        self.materiality = materiality
        self.bind_request = bind_request
        self.requests = []

    def assess(self, request, *, assessed_at):
        self.requests.append(request)
        evidence_refs = (
            (request.evidence_ref,)
            if self.bind_request
            else ("evidence:unbound",)
        )
        return ContinuityImpactAssessment(
            assessment_id=f"assessment-{len(self.requests)}",
            tenant_id=request.basis.tenant_id,
            trigger_refs=tuple(trigger.trigger_id for trigger in request.triggers),
            action_case_id=request.basis.action_case_id,
            action_case_hash=request.basis.action_case_hash,
            clearance_ref=request.basis.clearance_ref,
            materiality=self.materiality,
            impact_dimensions=("operational_continuity",),
            reason_codes=(self.materiality.value,),
            evidence_refs=evidence_refs,
            assessor_refs=("vaig:continuity-runtime",),
            confidence=1.0,
            assessed_at=assessed_at,
        )


def runtime(source, vaig, *, provider=None) -> OperationalContinuityRuntime:
    return OperationalContinuityRuntime(
        basis=basis(),
        source_baseline=baseline(),
        sources=(source,),
        current_fingerprint_provider=provider or current_provider(),
        vaig=vaig,
        requester_ref="execution-gateway:content",
        decider_ref="reht:continuity",
        decision_authority_ref="authority:reht",
    )


def test_live_runtime_collects_sources_fingerprints_vaig_and_reht():
    vaig = RecordingVaig()
    cycle = runtime(stable_source(), vaig).revalidate(
        request_id="request-1",
        clearance_state=ClearanceState.ACTIVE,
        now=NOW,
    )

    assert len(vaig.requests) == 1
    assert cycle.request.source_bundle.bundle_digest == cycle.source_bundle.bundle_digest
    assert cycle.request.triggers[0].trigger_kind is ContinuityTriggerKind.REVALIDATION_CHECKPOINT
    assert cycle.assessment.evidence_refs == (cycle.request.evidence_ref,)
    assert cycle.fingerprint_snapshot.as_mapping() == CURRENT
    assert cycle.fingerprint_snapshot.evidence_ref in cycle.request.evidence_refs
    assert set(cycle.fingerprint_snapshot.evidence_refs).issubset(
        set(cycle.request.evidence_refs)
    )
    assert cycle.request.current_fingerprints.fingerprint_digest == (
        cycle.fingerprint_snapshot.fingerprint_digest
    )
    assert cycle.result.decision.racs_outcome is ActionDecision.ALLOW
    assert cycle.result.decision.requires_new_clearance is False
    assert cycle.cycle_digest.startswith("sha256:")


def test_live_runtime_preserves_source_drift_for_vaig_and_reht():
    vaig = RecordingVaig(ContinuityMateriality.MATERIAL_CHANGE)
    cycle = runtime(changed_source(), vaig).revalidate(
        request_id="request-2",
        clearance_state=ClearanceState.ACTIVE,
        now=NOW,
    )

    assert len(cycle.request.triggers) == 1
    assert cycle.request.triggers[0].trigger_kind is ContinuityTriggerKind.POLICY_CHANGED
    assert cycle.request.triggers[0].current_fingerprint == "sha256:changed-source-policy"
    assert cycle.result.decision.racs_outcome is ActionDecision.DEFER
    assert cycle.result.decision.requires_new_action_case is True
    assert cycle.result.decision.requires_new_clearance is True


def test_live_runtime_fails_closed_when_vaig_output_is_not_request_bound():
    vaig = RecordingVaig(bind_request=False)
    with pytest.raises(
        OperationalContinuityRuntimeError,
        match="CONTINUITY_VAIG_ASSESSMENT_BINDING_INVALID",
    ):
        runtime(stable_source(), vaig).revalidate(
            request_id="request-3",
            clearance_state=ClearanceState.ACTIVE,
            now=NOW,
        )


def test_live_runtime_fails_closed_when_vaig_dependency_raises():
    def fail(request, assessed_at):
        raise OSError("VAIG unavailable")

    vaig = CallableVaigContinuityAssessmentPort(fail)
    with pytest.raises(
        OperationalContinuityRuntimeError,
        match="CONTINUITY_VAIG_ASSESSMENT_FAILED",
    ):
        runtime(stable_source(), vaig).revalidate(
            request_id="request-4",
            clearance_state=ClearanceState.ACTIVE,
            now=NOW,
        )


def test_live_runtime_requires_exact_source_coverage_before_observation():
    with pytest.raises(
        OperationalContinuityRuntimeError,
        match="CONTINUITY_RUNTIME_SOURCE_COVERAGE_MISMATCH",
    ):
        OperationalContinuityRuntime(
            basis=basis(),
            source_baseline=baseline(),
            sources=(),
            current_fingerprint_provider=current_provider(),
            vaig=RecordingVaig(),
            requester_ref="execution-gateway:content",
            decider_ref="reht:continuity",
            decision_authority_ref="authority:reht",
        )


def test_live_runtime_rejects_unstructured_fingerprint_callable():
    with pytest.raises(
        OperationalContinuityRuntimeError,
        match="CONTINUITY_CURRENT_FINGERPRINT_PROVIDER_INVALID",
    ):
        OperationalContinuityRuntime(
            basis=basis(),
            source_baseline=baseline(),
            sources=(stable_source(),),
            current_fingerprint_provider=lambda observed_at: dict(CURRENT),
            vaig=RecordingVaig(),
            requester_ref="execution-gateway:content",
            decider_ref="reht:continuity",
            decision_authority_ref="authority:reht",
        )


def test_live_runtime_wraps_fingerprint_provider_failure():
    class BrokenProvider:
        def snapshot(self, *, binding, observed_at):
            raise OSError("authority source unavailable")

    with pytest.raises(
        OperationalContinuityRuntimeError,
        match="CONTINUITY_CURRENT_FINGERPRINT_READ_FAILED",
    ):
        runtime(
            stable_source(),
            RecordingVaig(),
            provider=BrokenProvider(),
        ).revalidate(
            request_id="request-broken-fingerprint",
            clearance_state=ClearanceState.ACTIVE,
            now=NOW,
        )


def test_live_runtime_wraps_concrete_source_read_failure():
    def fail(expected: str, observed_at: datetime):
        raise OSError("registry unavailable")

    source = RuntimeContinuitySourceHandle(
        domain=ContinuitySourceDomain.POLICY,
        source_ref=SOURCE_REF,
        reader=fail,
    )
    with pytest.raises(
        OperationalContinuityRuntimeError,
        match="CONTINUITY_SOURCE_OBSERVATION_FAILED:policy",
    ):
        runtime(source, RecordingVaig()).revalidate(
            request_id="request-5",
            clearance_state=ClearanceState.ACTIVE,
            now=NOW,
        )


def test_target_state_runtime_source_reads_live_state_at_checkpoint_time():
    expected = TargetStateBinding(
        system_id="sanity",
        object_id="document-1",
        revision_type=RevisionType.VERSION,
        revision_value="7",
        observed_at=NOW - timedelta(minutes=10),
        current_state_hash="sha256:document-v7",
        state_witness_ref="witness:7",
    )
    current = expected.model_copy(update={"observed_at": NOW})
    adapter = TargetStateSourceAdapter(
        binding=observation_binding(),
        expected_state=expected,
    )
    source = target_state_runtime_source(
        adapter,
        current_state_reader=lambda observed_at: current,
    )

    observation = source.observe(
        expected_fingerprint=target_state_fingerprint(expected),
        observed_at=NOW,
    )

    assert observation.current_fingerprint == target_state_fingerprint(current)
    assert observation.trigger is None
    assert observation.observed_at == NOW
