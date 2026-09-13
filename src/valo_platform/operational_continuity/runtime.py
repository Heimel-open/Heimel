"""Live fail-closed Operational Continuity runtime wiring.

The runtime reads concrete policy, mandate, evidence and target-state sources,
builds an attributed snapshot of the five canonical current decision
fingerprints, submits one complete revalidation request to VAIG and then invokes
the canonical REHT continuity evaluator.

It produces evidence and a clearance-validity decision only. It does not mint a
GovernanceClearance, issue a CommitToken, call a provider or enforce a RACS
outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from src.valo_platform.action_envelope.models import ClearanceState
from src.valo_platform.action_envelope.transition_models import TargetStateBinding
from src.valo_platform.decision_governance.continuity import (
    ContinuityBasisSnapshot,
    ContinuityContractError,
    ContinuityImpactAssessment,
    canonical_digest,
)

from .fingerprint_snapshot import (
    CurrentDecisionFingerprintProvider,
    CurrentDecisionFingerprintSnapshot,
)
from .registered_policy_source import RegisteredPublicationPolicySourceAdapter
from .revalidation import (
    ContinuityRevalidationRequest,
    ContinuityRevalidationResult,
    build_revalidation_request,
    evaluate_revalidation_request,
    validate_vaig_assessment,
)
from .source_adapters import (
    ContinuitySourceBundle,
    ContinuitySourceDomain,
    ContinuitySourceObservation,
    EvidenceStoreSourceAdapter,
    MandateRegistrySourceAdapter,
    PublicationPolicySourceAdapter,
    SourceObservationError,
    TargetStateSourceAdapter,
    build_source_bundle,
)
from .source_baselines import (
    ContinuitySourceBaseline,
    ContinuitySourceBaselineEntry,
)


class OperationalContinuityRuntimeError(RuntimeError):
    """Raised when live revalidation cannot be completed deterministically."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise OperationalContinuityRuntimeError(
            "CONTINUITY_RUNTIME_TIME_MUST_BE_AWARE"
        )
    return value.astimezone(timezone.utc)


class VaigContinuityAssessmentPort(Protocol):
    """Configured VAIG boundary used by the live runtime."""

    def assess(
        self,
        request: ContinuityRevalidationRequest,
        *,
        assessed_at: datetime,
    ) -> ContinuityImpactAssessment:
        ...


@dataclass(frozen=True)
class CallableVaigContinuityAssessmentPort:
    """Adapt a concrete VAIG client/function to the runtime port."""

    assessor: Callable[
        [ContinuityRevalidationRequest, datetime],
        ContinuityImpactAssessment,
    ]

    def assess(
        self,
        request: ContinuityRevalidationRequest,
        *,
        assessed_at: datetime,
    ) -> ContinuityImpactAssessment:
        return self.assessor(request, assessed_at)


class RuntimeContinuitySource(Protocol):
    """Uniform read-only runtime view over one concrete source adapter."""

    domain: ContinuitySourceDomain
    source_ref: str

    def observe(
        self,
        *,
        expected_fingerprint: str,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        ...


@dataclass(frozen=True)
class RuntimeContinuitySourceHandle:
    """Bind an existing concrete adapter to the uniform runtime source contract."""

    domain: ContinuitySourceDomain
    source_ref: str
    reader: Callable[[str, datetime], ContinuitySourceObservation]

    def observe(
        self,
        *,
        expected_fingerprint: str,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        return self.reader(expected_fingerprint, observed_at)


def publication_policy_runtime_source(
    adapter: PublicationPolicySourceAdapter,
) -> RuntimeContinuitySourceHandle:
    return RuntimeContinuitySourceHandle(
        domain=ContinuitySourceDomain.POLICY,
        source_ref=adapter.source_ref,
        reader=lambda expected, observed_at: adapter.observe(
            expected_fingerprint=expected,
            observed_at=observed_at,
        ),
    )


def registered_policy_runtime_source(
    adapter: RegisteredPublicationPolicySourceAdapter,
) -> RuntimeContinuitySourceHandle:
    return RuntimeContinuitySourceHandle(
        domain=ContinuitySourceDomain.POLICY,
        source_ref=adapter.source_ref,
        reader=lambda expected, observed_at: adapter.observe(
            expected_fingerprint=expected,
            observed_at=observed_at,
        ),
    )


def mandate_runtime_source(
    adapter: MandateRegistrySourceAdapter,
) -> RuntimeContinuitySourceHandle:
    return RuntimeContinuitySourceHandle(
        domain=ContinuitySourceDomain.MANDATE,
        source_ref=adapter.source_ref,
        reader=lambda expected, observed_at: adapter.observe(
            expected_fingerprint=expected,
            observed_at=observed_at,
        ),
    )


def evidence_runtime_source(
    adapter: EvidenceStoreSourceAdapter,
) -> RuntimeContinuitySourceHandle:
    return RuntimeContinuitySourceHandle(
        domain=ContinuitySourceDomain.EVIDENCE,
        source_ref=adapter.source_ref,
        reader=lambda expected, observed_at: adapter.observe(
            expected_fingerprint=expected,
            observed_at=observed_at,
        ),
    )


def target_state_runtime_source(
    adapter: TargetStateSourceAdapter,
    *,
    current_state_reader: Callable[[datetime], TargetStateBinding],
) -> RuntimeContinuitySourceHandle:
    """Read current target state at the same timestamp as the runtime checkpoint."""

    def _read(
        expected_fingerprint: str,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        observation = adapter.observe(
            current_state=current_state_reader(observed_at),
            observed_at=observed_at,
        )
        if observation.expected_fingerprint != expected_fingerprint:
            raise SourceObservationError(
                "target-state adapter expectation does not match frozen baseline"
            )
        return observation

    return RuntimeContinuitySourceHandle(
        domain=ContinuitySourceDomain.ASSET_STATE,
        source_ref=adapter.source_ref,
        reader=_read,
    )


def _bind_fingerprint_snapshot_evidence(
    request: ContinuityRevalidationRequest,
    snapshot: CurrentDecisionFingerprintSnapshot,
) -> ContinuityRevalidationRequest:
    """Rebuild the frozen request with the attributed fingerprint proof chain."""

    evidence_refs = tuple(
        sorted(
            set(request.evidence_refs)
            | set(snapshot.evidence_refs)
            | {snapshot.evidence_ref}
        )
    )
    return ContinuityRevalidationRequest(
        request_id=request.request_id,
        requester_ref=request.requester_ref,
        basis=request.basis,
        source_baseline=request.source_baseline,
        source_bundle=request.source_bundle,
        current_fingerprints=request.current_fingerprints,
        triggers=request.triggers,
        evidence_refs=evidence_refs,
        requested_at=request.requested_at,
    )


class LiveContinuityRevalidation(BaseModel):
    """Tamper-evident output of one complete live revalidation cycle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_bundle: ContinuitySourceBundle
    fingerprint_snapshot: CurrentDecisionFingerprintSnapshot
    request: ContinuityRevalidationRequest
    assessment: ContinuityImpactAssessment
    result: ContinuityRevalidationResult
    completed_at: datetime
    cycle_digest: str = ""

    @model_validator(mode="after")
    def _validate_cycle(self) -> "LiveContinuityRevalidation":
        if self.source_bundle.bundle_digest != self.request.source_bundle.bundle_digest:
            raise ContinuityContractError(
                "live source bundle does not match revalidation request"
            )
        expected_binding = (
            self.request.basis.tenant_id,
            self.request.basis.action_case_id,
            self.request.basis.action_case_hash,
            self.request.basis.clearance_ref,
        )
        snapshot_binding = (
            self.fingerprint_snapshot.binding.tenant_id,
            self.fingerprint_snapshot.binding.action_case_id,
            self.fingerprint_snapshot.binding.action_case_hash,
            self.fingerprint_snapshot.binding.clearance_ref,
        )
        if snapshot_binding != expected_binding:
            raise ContinuityContractError(
                "current fingerprint snapshot binding mismatch"
            )
        if self.fingerprint_snapshot.observed_at > self.completed_at:
            raise ContinuityContractError(
                "current fingerprint snapshot is newer than live cycle"
            )
        if self.fingerprint_snapshot.as_mapping() != (
            self.request.current_fingerprints.as_mapping()
        ):
            raise ContinuityContractError(
                "current fingerprint snapshot does not match request"
            )
        if (
            self.fingerprint_snapshot.fingerprint_digest
            != self.request.current_fingerprints.fingerprint_digest
        ):
            raise ContinuityContractError(
                "current fingerprint aggregate digest mismatch"
            )
        request_evidence = set(self.request.evidence_refs)
        if self.fingerprint_snapshot.evidence_ref not in request_evidence:
            raise ContinuityContractError(
                "revalidation request omits current fingerprint snapshot"
            )
        if not set(self.fingerprint_snapshot.evidence_refs).issubset(request_evidence):
            raise ContinuityContractError(
                "revalidation request omits current fingerprint source evidence"
            )
        validate_vaig_assessment(self.request, self.assessment)
        if self.result.request_ref != self.request.evidence_ref:
            raise ContinuityContractError(
                "live result does not reference the revalidation request"
            )
        if self.result.request_digest != self.request.request_digest:
            raise ContinuityContractError(
                "live result request digest mismatch"
            )
        if self.result.assessment_ref != self.assessment.assessment_id:
            raise ContinuityContractError(
                "live result does not reference the VAIG assessment"
            )
        if self.result.assessment_digest != self.assessment.assessment_digest:
            raise ContinuityContractError(
                "live result assessment digest mismatch"
            )
        if self.result.completed_at != self.completed_at:
            raise ContinuityContractError(
                "live result completion time mismatch"
            )
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"cycle_digest"})
        )
        if self.cycle_digest and self.cycle_digest != expected:
            raise ContinuityContractError(
                "cycle_digest does not match live revalidation"
            )
        if not self.cycle_digest:
            object.__setattr__(self, "cycle_digest", expected)
        return self


class OperationalContinuityRuntime:
    """Collect concrete source state and execute the VAIG -> REHT validity chain."""

    def __init__(
        self,
        *,
        basis: ContinuityBasisSnapshot,
        source_baseline: ContinuitySourceBaseline,
        sources: Sequence[RuntimeContinuitySource],
        current_fingerprint_provider: CurrentDecisionFingerprintProvider,
        vaig: VaigContinuityAssessmentPort,
        requester_ref: str,
        decider_ref: str,
        decision_authority_ref: str,
        decision_ttl: timedelta = timedelta(minutes=5),
    ) -> None:
        if not requester_ref or not decider_ref or not decision_authority_ref:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_RUNTIME_ATTRIBUTION_REQUIRED"
            )
        if decision_ttl <= timedelta(0):
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_RUNTIME_DECISION_TTL_INVALID"
            )
        if not callable(getattr(current_fingerprint_provider, "snapshot", None)):
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_CURRENT_FINGERPRINT_PROVIDER_INVALID"
            )
        self.basis = basis
        self.source_baseline = source_baseline
        self.current_fingerprint_provider = current_fingerprint_provider
        self.vaig = vaig
        self.requester_ref = requester_ref
        self.decider_ref = decider_ref
        self.decision_authority_ref = decision_authority_ref
        self.decision_ttl = decision_ttl
        self._sources = self._index_sources(sources)
        self._validate_static_binding()

    @staticmethod
    def _source_key(
        domain: ContinuitySourceDomain,
        source_ref: str,
    ) -> tuple[str, str]:
        return domain.value, source_ref

    def _index_sources(
        self,
        sources: Sequence[RuntimeContinuitySource],
    ) -> dict[tuple[str, str], RuntimeContinuitySource]:
        indexed: dict[tuple[str, str], RuntimeContinuitySource] = {}
        for source in sources:
            key = self._source_key(source.domain, source.source_ref)
            if key in indexed:
                raise OperationalContinuityRuntimeError(
                    f"CONTINUITY_RUNTIME_DUPLICATE_SOURCE:{key[0]}:{key[1]}"
                )
            indexed[key] = source
        return indexed

    def _validate_static_binding(self) -> None:
        expected_binding = (
            self.basis.tenant_id,
            self.basis.action_case_id,
            self.basis.action_case_hash,
            self.basis.clearance_ref,
        )
        baseline_binding = (
            self.source_baseline.binding.tenant_id,
            self.source_baseline.binding.action_case_id,
            self.source_baseline.binding.action_case_hash,
            self.source_baseline.binding.clearance_ref,
        )
        if baseline_binding != expected_binding:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_RUNTIME_BASELINE_BINDING_MISMATCH"
            )
        baseline_keys = {
            self._source_key(entry.domain, entry.source_ref)
            for entry in self.source_baseline.entries
        }
        runtime_keys = set(self._sources)
        if baseline_keys != runtime_keys:
            missing = sorted(baseline_keys - runtime_keys)
            extra = sorted(runtime_keys - baseline_keys)
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_RUNTIME_SOURCE_COVERAGE_MISMATCH:"
                f"missing={missing}:extra={extra}"
            )

    def _observe_entry(
        self,
        entry: ContinuitySourceBaselineEntry,
        *,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        key = self._source_key(entry.domain, entry.source_ref)
        source = self._sources[key]
        try:
            observation = source.observe(
                expected_fingerprint=entry.fingerprint,
                observed_at=observed_at,
            )
        except Exception as exc:
            raise OperationalContinuityRuntimeError(
                f"CONTINUITY_SOURCE_OBSERVATION_FAILED:{key[0]}:{key[1]}"
            ) from exc
        if observation.domain != entry.domain:
            raise OperationalContinuityRuntimeError(
                f"CONTINUITY_SOURCE_DOMAIN_MISMATCH:{key[0]}:{key[1]}"
            )
        if observation.source_ref != entry.source_ref:
            raise OperationalContinuityRuntimeError(
                f"CONTINUITY_SOURCE_REF_MISMATCH:{key[0]}:{key[1]}"
            )
        if observation.expected_fingerprint != entry.fingerprint:
            raise OperationalContinuityRuntimeError(
                f"CONTINUITY_SOURCE_BASELINE_MISMATCH:{key[0]}:{key[1]}"
            )
        if observation.observed_at > observed_at:
            raise OperationalContinuityRuntimeError(
                f"CONTINUITY_SOURCE_FROM_FUTURE:{key[0]}:{key[1]}"
            )
        return observation

    def _read_current_fingerprints(
        self,
        *,
        observed_at: datetime,
    ) -> CurrentDecisionFingerprintSnapshot:
        try:
            snapshot = self.current_fingerprint_provider.snapshot(
                binding=self.source_baseline.binding,
                observed_at=observed_at,
            )
        except Exception as exc:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_CURRENT_FINGERPRINT_READ_FAILED"
            ) from exc
        if not isinstance(snapshot, CurrentDecisionFingerprintSnapshot):
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_CURRENT_FINGERPRINT_SNAPSHOT_INVALID"
            )
        if snapshot.binding != self.source_baseline.binding:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_CURRENT_FINGERPRINT_BINDING_MISMATCH"
            )
        if snapshot.observed_at > observed_at:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_CURRENT_FINGERPRINT_SNAPSHOT_FROM_FUTURE"
            )
        return snapshot

    def revalidate(
        self,
        *,
        request_id: str,
        clearance_state: ClearanceState,
        now: datetime,
    ) -> LiveContinuityRevalidation:
        """Run one complete live checkpoint; every missing dependency fails closed."""

        observed_at = _as_utc(now)
        if not request_id:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_REVALIDATION_REQUEST_ID_REQUIRED"
            )

        observations = tuple(
            self._observe_entry(entry, observed_at=observed_at)
            for entry in self.source_baseline.entries
        )
        source_bundle = build_source_bundle(
            binding=self.source_baseline.binding,
            observed_at=observed_at,
            observations=observations,
        )
        fingerprint_snapshot = self._read_current_fingerprints(
            observed_at=observed_at
        )
        request = build_revalidation_request(
            request_id=request_id,
            requester_ref=self.requester_ref,
            basis=self.basis,
            source_baseline=self.source_baseline,
            source_bundle=source_bundle,
            current_fingerprints=fingerprint_snapshot.as_mapping(),
            requested_at=observed_at,
        )
        request = _bind_fingerprint_snapshot_evidence(
            request,
            fingerprint_snapshot,
        )

        try:
            assessment = self.vaig.assess(request, assessed_at=observed_at)
        except Exception as exc:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_VAIG_ASSESSMENT_FAILED"
            ) from exc
        if not isinstance(assessment, ContinuityImpactAssessment):
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_VAIG_ASSESSMENT_INVALID_TYPE"
            )
        try:
            validate_vaig_assessment(request, assessment)
        except Exception as exc:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_VAIG_ASSESSMENT_BINDING_INVALID"
            ) from exc

        try:
            result = evaluate_revalidation_request(
                request=request,
                assessment=assessment,
                clearance_state=clearance_state,
                now=observed_at,
                decider_ref=self.decider_ref,
                decision_authority_ref=self.decision_authority_ref,
                decision_ttl=self.decision_ttl,
            )
        except Exception as exc:
            raise OperationalContinuityRuntimeError(
                "CONTINUITY_REHT_EVALUATION_FAILED"
            ) from exc

        return LiveContinuityRevalidation(
            source_bundle=source_bundle,
            fingerprint_snapshot=fingerprint_snapshot,
            request=request,
            assessment=assessment,
            result=result,
            completed_at=observed_at,
        )


__all__ = [
    "CallableVaigContinuityAssessmentPort",
    "LiveContinuityRevalidation",
    "OperationalContinuityRuntime",
    "OperationalContinuityRuntimeError",
    "RuntimeContinuitySource",
    "RuntimeContinuitySourceHandle",
    "VaigContinuityAssessmentPort",
    "evidence_runtime_source",
    "mandate_runtime_source",
    "publication_policy_runtime_source",
    "registered_policy_runtime_source",
    "target_state_runtime_source",
]
