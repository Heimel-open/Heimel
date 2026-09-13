"""Normative-independence gate for the VAIG -> REHT boundary.

Research Factory owns the underlying research artifacts. This module binds their
exact digests, evaluates whether the research may support consequential use, and
emits only a bounded AARM recommendation. It never grants authority or clearance.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable

from vaig.aarm import AARMVerdict


_DIGEST_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


class NormativeSensitivity(str, Enum):
    GENERAL = "GENERAL"
    POLITICAL = "POLITICAL"
    IDEOLOGICAL = "IDEOLOGICAL"
    MORAL = "MORAL"
    CULTURAL = "CULTURAL"
    STATE_SENSITIVE = "STATE_SENSITIVE"


class ConsequenceClass(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResearchGateDecision(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    ACCEPTED = "ACCEPTED"
    DEFER = "DEFER"


class EvaluatorCorrelationRisk(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NormativeHandoffDisposition(str, Enum):
    """A normative gate can restrict AARM, but cannot produce ALLOW/MODIFY."""

    NO_OVERRIDE = "NO_OVERRIDE"
    DEFER = "DEFER"
    STEP_UP = "STEP_UP"

    @property
    def aarm_verdict(self) -> AARMVerdict | None:
        if self is NormativeHandoffDisposition.DEFER:
            return AARMVerdict.DEFER
        if self is NormativeHandoffDisposition.STEP_UP:
            return AARMVerdict.STEP_UP
        return None


@dataclass(frozen=True)
class NormativeArtifactBindingsV1:
    """Exact Research Factory artifacts used by the normative gate."""

    research_report_ref: str
    research_report_digest: str
    model_power_shadow_profile_digest: str
    normative_scorecard_digest: str
    normative_influence_profile_digests: tuple[str, ...]
    counterposition_bundle_digest: str | None = None
    adversarial_evaluation_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.research_report_ref.strip():
            raise ValueError("research_report_ref must not be empty")
        for name in (
            "research_report_digest",
            "model_power_shadow_profile_digest",
            "normative_scorecard_digest",
        ):
            object.__setattr__(self, name, _normalize_digest(getattr(self, name)))
        for name in (
            "counterposition_bundle_digest",
            "adversarial_evaluation_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _normalize_digest(value))
        normalized_profiles = tuple(
            dict.fromkeys(_normalize_digest(item) for item in self.normative_influence_profile_digests)
        )
        if not normalized_profiles:
            raise ValueError("at least one normative influence profile digest is required")
        object.__setattr__(self, "normative_influence_profile_digests", normalized_profiles)


@dataclass(frozen=True)
class NormativeResearchSignalsV1:
    """Declared decisions from Research Factory Slices 1-4."""

    sensitivity: NormativeSensitivity
    consequence_class: ConsequenceClass
    counterposition_required: bool
    counterposition_decision: ResearchGateDecision
    adversarial_evaluation_decision: ResearchGateDecision
    scorecard_decision: ResearchGateDecision
    evaluator_correlation_risk: EvaluatorCorrelationRisk
    independent_evaluator_present: bool
    unresolved_normative_conflict: bool = False
    material_perspective_gap: bool = False
    required_authority_class: str | None = None

    def __post_init__(self) -> None:
        if self.required_authority_class is not None and not self.required_authority_class.strip():
            raise ValueError("required_authority_class must not be blank")

    @property
    def sensitive(self) -> bool:
        return self.sensitivity is not NormativeSensitivity.GENERAL


@dataclass(frozen=True)
class NormativeGovernanceHandoffV1:
    """Replayable VAIG restriction handed to REHT.

    `NO_OVERRIDE` means this gate found no additional normative restriction. It
    does not mean ALLOW. `DEFER` and `STEP_UP` are canonical AARM verdicts and
    block ordinary GovernanceClearance.
    """

    report_id: str
    source_evaluation_report_ref: str
    source_evaluation_report_digest: str
    disposition: NormativeHandoffDisposition
    reason_codes: tuple[str, ...]
    artifact_bindings: NormativeArtifactBindingsV1
    sensitivity: NormativeSensitivity
    consequence_class: ConsequenceClass
    required_authority_class: str | None = None
    schema_version: str = "1.0.0"
    execution_authority: bool = False
    requires_reht_clearance: bool = True

    def __post_init__(self) -> None:
        for name in ("report_id", "source_evaluation_report_ref"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        object.__setattr__(
            self,
            "source_evaluation_report_digest",
            _normalize_digest(self.source_evaluation_report_digest),
        )
        object.__setattr__(self, "reason_codes", _clean_tuple(self.reason_codes))
        if self.schema_version != "1.0.0":
            raise ValueError("unsupported normative handoff schema_version")
        if self.execution_authority:
            raise ValueError("VAIG normative handoffs cannot grant execution authority")
        if not self.requires_reht_clearance:
            raise ValueError("VAIG normative handoffs must require REHT clearance")
        if self.disposition is NormativeHandoffDisposition.NO_OVERRIDE:
            if self.reason_codes:
                raise ValueError("NO_OVERRIDE cannot carry blocking reason codes")
            if self.required_authority_class is not None:
                raise ValueError("NO_OVERRIDE cannot require step-up authority")
        else:
            if not self.reason_codes:
                raise ValueError("restrictive dispositions require reason codes")
        if self.disposition is NormativeHandoffDisposition.STEP_UP:
            if not self.required_authority_class:
                raise ValueError("STEP_UP requires required_authority_class")
        elif self.required_authority_class is not None:
            raise ValueError("required_authority_class is only valid for STEP_UP")

    @property
    def recommended_aarm_verdict(self) -> AARMVerdict | None:
        return self.disposition.aarm_verdict

    @property
    def blocks_clearance(self) -> bool:
        return self.disposition in {
            NormativeHandoffDisposition.DEFER,
            NormativeHandoffDisposition.STEP_UP,
        }

    @property
    def requires_human_review(self) -> bool:
        return self.blocks_clearance

    def canonical_payload(self) -> dict[str, Any]:
        payload = _jsonable(asdict(self))
        payload.update(
            {
                "recommended_aarm_verdict": (
                    self.recommended_aarm_verdict.value
                    if self.recommended_aarm_verdict is not None
                    else None
                ),
                "blocks_clearance": self.blocks_clearance,
                "requires_human_review": self.requires_human_review,
            }
        )
        return payload

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def handoff_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def receipt_binding(self) -> dict[str, Any]:
        return {
            "handoff_ref": self.report_id,
            "handoff_digest": self.handoff_digest(),
            "source_evaluation_report_ref": self.source_evaluation_report_ref,
            "source_evaluation_report_digest": self.source_evaluation_report_digest,
            "disposition": self.disposition.value,
            "recommended_aarm_verdict": (
                self.recommended_aarm_verdict.value
                if self.recommended_aarm_verdict is not None
                else None
            ),
            "reason_codes": list(self.reason_codes),
            "required_authority_class": self.required_authority_class,
            "artifact_bindings": _jsonable(asdict(self.artifact_bindings)),
            "execution_authority": False,
            "requires_reht_clearance": True,
            "blocks_clearance": self.blocks_clearance,
        }


class NormativeGovernanceGateV1:
    """Map Research Factory controls to a bounded VAIG restriction."""

    def evaluate(
        self,
        *,
        report_id: str,
        source_evaluation_report_ref: str,
        source_evaluation_report_digest: str,
        artifact_bindings: NormativeArtifactBindingsV1,
        signals: NormativeResearchSignalsV1,
    ) -> NormativeGovernanceHandoffV1:
        defer_reasons = self._defer_reasons(artifact_bindings, signals)
        if defer_reasons:
            return self._handoff(
                report_id=report_id,
                source_evaluation_report_ref=source_evaluation_report_ref,
                source_evaluation_report_digest=source_evaluation_report_digest,
                artifact_bindings=artifact_bindings,
                signals=signals,
                disposition=NormativeHandoffDisposition.DEFER,
                reason_codes=defer_reasons,
            )

        if (
            signals.unresolved_normative_conflict
            and signals.consequence_class
            in {ConsequenceClass.MEDIUM, ConsequenceClass.HIGH, ConsequenceClass.CRITICAL}
        ):
            return self._handoff(
                report_id=report_id,
                source_evaluation_report_ref=source_evaluation_report_ref,
                source_evaluation_report_digest=source_evaluation_report_digest,
                artifact_bindings=artifact_bindings,
                signals=signals,
                disposition=NormativeHandoffDisposition.STEP_UP,
                reason_codes=("UNRESOLVED_NORMATIVE_CONFLICT",),
                required_authority_class=(
                    signals.required_authority_class
                    or _default_authority_class(signals.consequence_class)
                ),
            )

        return self._handoff(
            report_id=report_id,
            source_evaluation_report_ref=source_evaluation_report_ref,
            source_evaluation_report_digest=source_evaluation_report_digest,
            artifact_bindings=artifact_bindings,
            signals=signals,
            disposition=NormativeHandoffDisposition.NO_OVERRIDE,
            reason_codes=(),
        )

    @staticmethod
    def _defer_reasons(
        artifacts: NormativeArtifactBindingsV1,
        signals: NormativeResearchSignalsV1,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if signals.sensitive and artifacts.adversarial_evaluation_digest is None:
            reasons.append("ADVERSARIAL_EVALUATION_BINDING_MISSING")
        if signals.counterposition_required:
            if artifacts.counterposition_bundle_digest is None:
                reasons.append("COUNTERPOSITION_BINDING_MISSING")
            if signals.counterposition_decision is not ResearchGateDecision.ACCEPTED:
                reasons.append("COUNTERPOSITION_NOT_ACCEPTED")
        if signals.adversarial_evaluation_decision is ResearchGateDecision.DEFER:
            reasons.append("ADVERSARIAL_EVALUATION_DEFERRED")
        if signals.scorecard_decision is ResearchGateDecision.DEFER:
            reasons.append("NORMATIVE_SCORECARD_DEFERRED")
        if not signals.independent_evaluator_present:
            reasons.append("INDEPENDENT_EVALUATOR_MISSING")
        if signals.evaluator_correlation_risk in {
            EvaluatorCorrelationRisk.HIGH,
            EvaluatorCorrelationRisk.CRITICAL,
        }:
            reasons.append("EVALUATOR_CORRELATION_RISK_TOO_HIGH")
        if signals.material_perspective_gap:
            reasons.append("MATERIAL_PERSPECTIVE_GAP")
        return _clean_tuple(reasons)

    @staticmethod
    def _handoff(
        *,
        report_id: str,
        source_evaluation_report_ref: str,
        source_evaluation_report_digest: str,
        artifact_bindings: NormativeArtifactBindingsV1,
        signals: NormativeResearchSignalsV1,
        disposition: NormativeHandoffDisposition,
        reason_codes: Iterable[str],
        required_authority_class: str | None = None,
    ) -> NormativeGovernanceHandoffV1:
        return NormativeGovernanceHandoffV1(
            report_id=report_id,
            source_evaluation_report_ref=source_evaluation_report_ref,
            source_evaluation_report_digest=source_evaluation_report_digest,
            disposition=disposition,
            reason_codes=tuple(reason_codes),
            artifact_bindings=artifact_bindings,
            sensitivity=signals.sensitivity,
            consequence_class=signals.consequence_class,
            required_authority_class=required_authority_class,
        )


def _default_authority_class(consequence: ConsequenceClass) -> str:
    if consequence is ConsequenceClass.CRITICAL:
        return "HUMAN_RISK_OWNER"
    if consequence is ConsequenceClass.HIGH:
        return "HUMAN_ACCOUNTABLE_OWNER"
    return "HUMAN_DELEGATED_AUTHORITY"


def _normalize_digest(value: str) -> str:
    normalized = str(value).strip().lower()
    if not _DIGEST_RE.fullmatch(normalized):
        raise ValueError("digest must be a SHA-256 hex digest")
    return normalized if normalized.startswith("sha256:") else "sha256:" + normalized


def _clean_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
