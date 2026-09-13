"""Structured analytic tradecraft gate for VAIG.

The gate evaluates the quality of represented evidence and analysis before
consequential use. It does not authorize or execute actions. REHT remains the
clearance boundary and RACS remains the receipt/enforcement contract boundary.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Sequence, Set, Tuple

from vaig.epistemic_underdetermination import AlternativeHypothesis
from vaig.evidence_intake import EvidenceIntakeState, EvidencePackageBinding


class ClaimCredibility(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PurposeRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceDisposition(str, Enum):
    CITE = "CITE"
    BACKGROUND = "BACKGROUND"
    HOLD = "HOLD"
    DISCARD = "DISCARD"


class AssumptionStatus(str, Enum):
    STRONG = "STRONG"
    QUESTIONABLE = "QUESTIONABLE"
    HIGH_RISK = "HIGH_RISK"


class TradecraftState(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    CONSTRAINED = "CONSTRAINED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    claim: str
    # --- Upstream source-of-truth binding (preferred, single source) ---
    # VAIG consumes an exact, versioned EvidencePackage owned by Verification
    # Factory. It must not re-derive provenance, independence or admissibility;
    # ``package_ref`` is immutable and ``intake_state`` is the upstream verdict.
    package_ref: Optional[EvidencePackageBinding] = None
    intake_state: Optional[EvidenceIntakeState] = None
    # --- Legacy VAIG-local source-truth fields (DEPRECATED) ---
    # Retained only for backward compatibility with pre-#141 callers. Do not use
    # for new consequential evaluation; bind an EvidencePackageBinding instead.
    provenance_known: bool = True
    first_appearance_identifiable: bool = True
    manipulation_suspected: bool = False
    claim_credibility: ClaimCredibility = ClaimCredibility.MEDIUM
    independent_corroboration_count: int = 0
    purpose_risk: PurposeRisk = PurposeRisk.LOW
    supports_hypotheses: Tuple[str, ...] = ()
    contradicts_hypotheses: Tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    @property
    def package_binding_key(self) -> Optional[Tuple[str, str, str]]:
        return self.package_ref.ref.binding_key() if self.package_ref else None

    def is_upstream_usable(self) -> Optional[bool]:
        """Return upstream usability verdict, or None if no package bound.

        VAIG consumes this; it never re-derives it. None means legacy mode.
        """
        if self.package_ref is None:
            return None
        if self.intake_state is not None:
            return self.intake_state not in {
                EvidenceIntakeState.MISSING,
                EvidenceIntakeState.MISMATCHED,
                EvidenceIntakeState.STALE,
                EvidenceIntakeState.INVALIDATED,
                EvidenceIntakeState.USE_PROHIBITED,
                EvidenceIntakeState.UNVERIFIED,
                EvidenceIntakeState.CONFLICTED,
            }
        # No explicit intake verdict: treat an invalidated package as unusable.
        return self.package_ref.invalidated_at is None


@dataclass(frozen=True)
class KeyAssumption:
    assumption_id: str
    statement: str
    supporting_evidence_refs: Tuple[str, ...] = ()
    contradicting_evidence_refs: Tuple[str, ...] = ()
    collapse_if_false: bool = False


@dataclass(frozen=True)
class EvidenceAssessment:
    evidence_id: str
    disposition: EvidenceDisposition
    rationale: Tuple[str, ...]
    package_binding_key: Optional[Tuple[str, str, str]] = None
    contradicting_evidence_refs: Tuple[str, ...] = ()
    collapse_if_false: bool = False


@dataclass(frozen=True)
class ExpectedObservation:
    observation_id: str
    description: str
    hypothesis_ids: Tuple[str, ...]
    observed: bool
    evidence_ref: str = ""


@dataclass(frozen=True)
class AssumptionAssessment:
    assumption_id: str
    status: AssumptionStatus
    rationale: Tuple[str, ...]


@dataclass(frozen=True)
class HypothesisAssessment:
    hypothesis_id: str
    supporting_evidence_refs: Tuple[str, ...]
    contradicting_evidence_refs: Tuple[str, ...]

    @property
    def support_count(self) -> int:
        return len(self.supporting_evidence_refs)

    @property
    def contradiction_count(self) -> int:
        return len(self.contradicting_evidence_refs)


@dataclass(frozen=True)
class AnalyticTradecraftAssessment:
    state: TradecraftState
    evidence: Tuple[EvidenceAssessment, ...]
    assumptions: Tuple[AssumptionAssessment, ...]
    hypotheses: Tuple[HypothesisAssessment, ...]
    least_contradicted_hypotheses: Tuple[str, ...]
    discriminating_evidence_refs: Tuple[str, ...]
    missing_expected_observations: Tuple[str, ...]
    rationale: Tuple[str, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)
    execution_authority: bool = False
    requires_reht_clearance: bool = True

    @property
    def blocks_consequential_action(self) -> bool:
        return self.state == TradecraftState.INSUFFICIENT

    @property
    def requires_human_review(self) -> bool:
        return self.state != TradecraftState.SUFFICIENT

    def to_dict(self) -> Mapping[str, object]:
        return {
            "state": self.state.value,
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "disposition": item.disposition.value,
                    "rationale": list(item.rationale),
                    "package_binding_key": list(item.package_binding_key)
                    if item.package_binding_key
                    else None,
                }
                for item in self.evidence
            ],
            "assumptions": [
                {
                    "assumption_id": item.assumption_id,
                    "status": item.status.value,
                    "rationale": list(item.rationale),
                }
                for item in self.assumptions
            ],
            "hypotheses": [
                {
                    "hypothesis_id": item.hypothesis_id,
                    "supporting_evidence_refs": list(
                        item.supporting_evidence_refs
                    ),
                    "contradicting_evidence_refs": list(
                        item.contradicting_evidence_refs
                    ),
                    "support_count": item.support_count,
                    "contradiction_count": item.contradiction_count,
                }
                for item in self.hypotheses
            ],
            "least_contradicted_hypotheses": list(
                self.least_contradicted_hypotheses
            ),
            "discriminating_evidence_refs": list(
                self.discriminating_evidence_refs
            ),
            "missing_expected_observations": list(
                self.missing_expected_observations
            ),
            "requires_human_review": self.requires_human_review,
            "blocks_consequential_action": self.blocks_consequential_action,
            "rationale": list(self.rationale),
            "metadata": dict(self.metadata),
            "execution_authority": self.execution_authority,
            "requires_reht_clearance": self.requires_reht_clearance,
        }


class AnalyticTradecraftInputError(ValueError):
    pass


class AnalyticTradecraftGate:
    """Apply source, assumption and competing-hypothesis discipline."""

    def assess(
        self,
        *,
        evidence: Sequence[EvidenceItem],
        alternatives: Sequence[AlternativeHypothesis],
        assumptions: Sequence[KeyAssumption] = (),
        expected_observations: Sequence[ExpectedObservation] = (),
        high_consequence: bool = False,
        minimum_independent_corroboration: int = 1,
        metadata: Optional[Mapping[str, object]] = None,
    ) -> AnalyticTradecraftAssessment:
        evidence_items = tuple(evidence)
        candidates = tuple(alternatives)
        key_assumptions = tuple(assumptions)
        observations = tuple(expected_observations)

        self._validate(
            evidence_items,
            candidates,
            key_assumptions,
            observations,
            minimum_independent_corroboration,
        )

        # Fail-closed for consequential evaluation: an exact upstream
        # EvidencePackage binding is mandatory. VAIG may not evaluate
        # consequential action on locally-asserted source truth.
        if high_consequence and any(
            item.package_ref is None for item in evidence_items
        ):
            return AnalyticTradecraftAssessment(
                state=TradecraftState.INSUFFICIENT,
                evidence=tuple(
                    self._assess_evidence(item, minimum_independent_corroboration)
                    for item in evidence_items
                ),
                assumptions=(),
                hypotheses=(),
                least_contradicted_hypotheses=(),
                discriminating_evidence_refs=(),
                missing_expected_observations=(),
                rationale=(
                    "Consequential evaluation requires an exact upstream "
                    "EvidencePackage binding for every evidence item; at least "
                    "one item has no package_ref.",
                ),
                metadata=dict(metadata or {}),
            )

        evidence_assessments = tuple(
            self._assess_evidence(item, minimum_independent_corroboration)
            for item in evidence_items
        )
        citable_ids = {
            item.evidence_id
            for item, assessment in zip(evidence_items, evidence_assessments)
            if assessment.disposition == EvidenceDisposition.CITE
        }

        viable = tuple(candidate for candidate in candidates if candidate.viable)
        hypothesis_ids = tuple(candidate.alternative_id for candidate in viable)
        hypothesis_assessments = tuple(
            HypothesisAssessment(
                hypothesis_id=hypothesis_id,
                supporting_evidence_refs=tuple(
                    item.evidence_id
                    for item in evidence_items
                    if item.evidence_id in citable_ids
                    and hypothesis_id in item.supports_hypotheses
                ),
                contradicting_evidence_refs=tuple(
                    item.evidence_id
                    for item in evidence_items
                    if item.evidence_id in citable_ids
                    and hypothesis_id in item.contradicts_hypotheses
                ),
            )
            for hypothesis_id in hypothesis_ids
        )

        assumption_assessments = tuple(
            self._assess_assumption(item, citable_ids)
            for item in key_assumptions
        )
        least_contradicted = self._least_contradicted(hypothesis_assessments)
        discriminating = self._discriminating_evidence(
            evidence_items,
            citable_ids,
            set(hypothesis_ids),
        )
        missing = tuple(
            item.observation_id
            for item in observations
            if not item.observed
            or (item.evidence_ref and item.evidence_ref not in citable_ids)
        )
        bearing_evidence = any(
            item.supporting_evidence_refs or item.contradicting_evidence_refs
            for item in hypothesis_assessments
        )
        high_risk_assumption = any(
            item.status == AssumptionStatus.HIGH_RISK
            for item in assumption_assessments
        )

        rationale = []
        if not viable:
            state = TradecraftState.INSUFFICIENT
            rationale.append("No viable hypothesis was supplied.")
        elif not citable_ids:
            state = TradecraftState.INSUFFICIENT
            rationale.append(
                "No evidence passed provenance, credibility and corroboration gates."
            )
        elif high_risk_assumption and high_consequence:
            state = TradecraftState.INSUFFICIENT
            rationale.append(
                "A high-risk assumption remains unresolved for a high-consequence case."
            )
        elif high_risk_assumption:
            state = TradecraftState.CONSTRAINED
            rationale.append("A high-risk assumption remains unresolved.")
        elif not bearing_evidence:
            state = TradecraftState.CONSTRAINED
            rationale.append(
                "Citable evidence exists but does not discriminate between hypotheses."
            )
        elif len(least_contradicted) != 1:
            state = TradecraftState.CONSTRAINED
            rationale.append(
                "More than one hypothesis is equally least contradicted by citable evidence."
            )
        elif missing:
            state = TradecraftState.CONSTRAINED
            rationale.append("Expected observations are missing.")
        else:
            state = TradecraftState.SUFFICIENT
            rationale.append(
                "Evidence integrity passed and one hypothesis is uniquely least contradicted."
            )

        return AnalyticTradecraftAssessment(
            state=state,
            evidence=evidence_assessments,
            assumptions=assumption_assessments,
            hypotheses=hypothesis_assessments,
            least_contradicted_hypotheses=least_contradicted,
            discriminating_evidence_refs=discriminating,
            missing_expected_observations=missing,
            rationale=tuple(rationale),
            metadata=dict(metadata or {}),
        )

    @staticmethod
    def _assess_evidence(
        item: EvidenceItem,
        minimum_independent_corroboration: int,
    ) -> EvidenceAssessment:
        rationale = []
        package_key = item.package_binding_key

        if item.package_ref is not None:
            # Consume the upstream verdict; never re-derive source truth.
            usable = item.is_upstream_usable()
            if usable is False:
                return EvidenceAssessment(
                    evidence_id=item.evidence_id,
                    disposition=EvidenceDisposition.DISCARD,
                    rationale=(
                        "Upstream EvidencePackage is not usable for this use "
                        "(stale, mismatched, invalidated, unverified or "
                        "use-prohibited).",
                    ),
                    package_binding_key=package_key,
                )
            # Usable package: apply VAIG-owned analysis gates only
            # (credibility-for-analysis and purpose risk).
            if item.claim_credibility == ClaimCredibility.LOW:
                return EvidenceAssessment(
                    evidence_id=item.evidence_id,
                    disposition=EvidenceDisposition.HOLD,
                    rationale=("Claim credibility is low.",),
                    package_binding_key=package_key,
                )
            if item.purpose_risk == PurposeRisk.HIGH:
                return EvidenceAssessment(
                    evidence_id=item.evidence_id,
                    disposition=EvidenceDisposition.BACKGROUND,
                    rationale=("Purpose or influence risk is high.",),
                    package_binding_key=package_key,
                )
            return EvidenceAssessment(
                evidence_id=item.evidence_id,
                disposition=EvidenceDisposition.CITE,
                rationale=(
                    "Upstream EvidencePackage admissible; VAIG analysis gates passed.",
                ),
                package_binding_key=package_key,
            )

        # Legacy path: VAIG-local source-truth fields are DEPRECATED.
        warnings.warn(
            "EvidenceItem.provenance_known / independent_corroboration_count / "
            "manipulation_suspected are deprecated; bind an EvidencePackageBinding "
            "via EvidenceItem.package_ref instead (see #141).",
            DeprecationWarning,
            stacklevel=3,
        )
        if (
            not item.provenance_known
            or not item.first_appearance_identifiable
            or item.manipulation_suspected
        ):
            if not item.provenance_known:
                rationale.append("Provenance is unknown.")
            if not item.first_appearance_identifiable:
                rationale.append("First appearance is not identifiable.")
            if item.manipulation_suspected:
                rationale.append("Manipulation or context drift is suspected.")
            return EvidenceAssessment(
                evidence_id=item.evidence_id,
                disposition=EvidenceDisposition.DISCARD,
                rationale=tuple(rationale),
                package_binding_key=package_key,
            )

        if item.claim_credibility == ClaimCredibility.LOW:
            return EvidenceAssessment(
                evidence_id=item.evidence_id,
                disposition=EvidenceDisposition.HOLD,
                rationale=("Claim credibility is low.",),
                package_binding_key=package_key,
            )

        if item.independent_corroboration_count < minimum_independent_corroboration:
            rationale.append("Independent corroboration threshold is not met.")
        if item.purpose_risk == PurposeRisk.HIGH:
            rationale.append("Purpose or influence risk is high.")
        if rationale:
            return EvidenceAssessment(
                evidence_id=item.evidence_id,
                disposition=EvidenceDisposition.BACKGROUND,
                rationale=tuple(rationale),
                package_binding_key=package_key,
            )

        return EvidenceAssessment(
            evidence_id=item.evidence_id,
            disposition=EvidenceDisposition.CITE,
            rationale=("Evidence integrity and citation gates passed.",),
            package_binding_key=package_key,
        )

    @staticmethod
    def _assess_assumption(
        item: KeyAssumption,
        citable_ids: Set[str],
    ) -> AssumptionAssessment:
        support = set(item.supporting_evidence_refs) & citable_ids
        contradiction = set(item.contradicting_evidence_refs) & citable_ids

        if item.collapse_if_false and (not support or contradiction):
            return AssumptionAssessment(
                assumption_id=item.assumption_id,
                status=AssumptionStatus.HIGH_RISK,
                rationale=(
                    "The analysis collapses if this assumption is false, "
                    "and it is not securely supported.",
                ),
            )
        if contradiction or not support:
            return AssumptionAssessment(
                assumption_id=item.assumption_id,
                status=AssumptionStatus.QUESTIONABLE,
                rationale=("The assumption is weakly supported or contradicted.",),
            )
        return AssumptionAssessment(
            assumption_id=item.assumption_id,
            status=AssumptionStatus.STRONG,
            rationale=("The assumption has citable supporting evidence.",),
        )

    @staticmethod
    def _least_contradicted(
        hypotheses: Tuple[HypothesisAssessment, ...]
    ) -> Tuple[str, ...]:
        if not hypotheses:
            return ()
        best = min(
            (item.contradiction_count, -item.support_count)
            for item in hypotheses
        )
        return tuple(
            item.hypothesis_id
            for item in hypotheses
            if (item.contradiction_count, -item.support_count) == best
        )

    @staticmethod
    def _discriminating_evidence(
        evidence: Tuple[EvidenceItem, ...],
        citable_ids: Set[str],
        hypothesis_ids: Set[str],
    ) -> Tuple[str, ...]:
        result = []
        ordered_hypotheses = tuple(sorted(hypothesis_ids))
        for item in evidence:
            if item.evidence_id not in citable_ids:
                continue
            signals = tuple(
                1
                if hypothesis_id in item.supports_hypotheses
                else -1
                if hypothesis_id in item.contradicts_hypotheses
                else 0
                for hypothesis_id in ordered_hypotheses
            )
            if signals and len(set(signals)) > 1:
                result.append(item.evidence_id)
        return tuple(dict.fromkeys(result))

    @staticmethod
    def _validate(
        evidence: Tuple[EvidenceItem, ...],
        alternatives: Tuple[AlternativeHypothesis, ...],
        assumptions: Tuple[KeyAssumption, ...],
        observations: Tuple[ExpectedObservation, ...],
        minimum_independent_corroboration: int,
    ) -> None:
        if minimum_independent_corroboration < 0:
            raise AnalyticTradecraftInputError(
                "Minimum independent corroboration cannot be negative"
            )

        def unique_nonempty(values: Sequence[str], label: str) -> None:
            if any(not value.strip() for value in values):
                raise AnalyticTradecraftInputError(
                    "{} IDs must be non-empty".format(label)
                )
            if len(values) != len(set(values)):
                raise AnalyticTradecraftInputError(
                    "{} IDs must be unique".format(label)
                )

        evidence_ids = tuple(item.evidence_id for item in evidence)
        hypothesis_ids = tuple(item.alternative_id for item in alternatives)
        assumption_ids = tuple(item.assumption_id for item in assumptions)
        observation_ids = tuple(item.observation_id for item in observations)

        unique_nonempty(evidence_ids, "Evidence")
        unique_nonempty(hypothesis_ids, "Hypothesis")
        unique_nonempty(assumption_ids, "Assumption")
        unique_nonempty(observation_ids, "Observation")

        if any(not item.claim.strip() for item in evidence):
            raise AnalyticTradecraftInputError("Evidence claims must be non-empty")
        if any(item.independent_corroboration_count < 0 for item in evidence):
            raise AnalyticTradecraftInputError(
                "Independent corroboration counts cannot be negative"
            )
        if any(not item.statement.strip() for item in assumptions):
            raise AnalyticTradecraftInputError(
                "Assumption statements must be non-empty"
            )
        if any(not item.description.strip() for item in observations):
            raise AnalyticTradecraftInputError(
                "Expected observation descriptions must be non-empty"
            )

        for item in evidence:
            overlap = set(item.supports_hypotheses) & set(
                item.contradicts_hypotheses
            )
            if overlap:
                raise AnalyticTradecraftInputError(
                    "Evidence cannot both support and contradict the same "
                    "hypothesis: {}".format(", ".join(sorted(overlap)))
                )

        known_hypotheses = set(hypothesis_ids)
        referenced_hypotheses = {
            hypothesis_id
            for item in evidence
            for hypothesis_id in (
                item.supports_hypotheses + item.contradicts_hypotheses
            )
        } | {
            hypothesis_id
            for item in observations
            for hypothesis_id in item.hypothesis_ids
        }
        unknown = referenced_hypotheses - known_hypotheses
        if unknown:
            raise AnalyticTradecraftInputError(
                "Unknown hypothesis references: {}".format(
                    ", ".join(sorted(unknown))
                )
            )


def evidence_item_from_package(
    *,
    evidence_id: str,
    claim: str,
    package: EvidencePackageBinding,
    intake_state: Optional[EvidenceIntakeState] = None,
    claim_credibility: ClaimCredibility = ClaimCredibility.MEDIUM,
    purpose_risk: PurposeRisk = PurposeRisk.LOW,
    supports_hypotheses: Tuple[str, ...] = (),
    contradicts_hypotheses: Tuple[str, ...] = (),
    metadata: Optional[Mapping[str, object]] = None,
) -> EvidenceItem:
    """Build an EvidenceItem bound to an exact upstream EvidencePackage (#141.6).

    This is the compatibility adapter for callers that hold a verified
    EvidencePackage rather than VAIG-local source-truth fields. VAIG consumes
    the package verdict; it must not re-derive provenance, independence or
    admissibility.
    """
    return EvidenceItem(
        evidence_id=evidence_id,
        claim=claim,
        package_ref=package,
        intake_state=intake_state,
        claim_credibility=claim_credibility,
        purpose_risk=purpose_risk,
        supports_hypotheses=supports_hypotheses,
        contradicts_hypotheses=contradicts_hypotheses,
        metadata=dict(metadata or {}),
    )
