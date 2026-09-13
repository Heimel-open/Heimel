"""Evidence-relative underdetermination assessment for VAIG.

The assessment is epistemic evidence only. It does not authorize or execute actions.
Consequential use remains behind REHT clearance and RACS receipts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Optional, Sequence, Tuple


class EpistemicState(str, Enum):
    DETERMINED = "DETERMINED"
    UNDERDETERMINED = "UNDERDETERMINED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class UnderdeterminationKind(str, Enum):
    NONE = "NONE"
    HOLIST = "HOLIST"
    CONTRASTIVE = "CONTRASTIVE"
    MIXED = "MIXED"


@dataclass(frozen=True)
class AlternativeHypothesis:
    alternative_id: str
    claim: str
    evidence_refs: Tuple[str, ...] = ()
    auxiliary_assumptions: Tuple[str, ...] = ()
    discriminating_tests: Tuple[str, ...] = ()
    consequences: Tuple[str, ...] = ()
    viable: bool = True


@dataclass(frozen=True)
class UnderdeterminationAssessment:
    epistemic_state: EpistemicState
    kind: UnderdeterminationKind
    surviving_alternatives: Tuple[AlternativeHypothesis, ...]
    shared_evidence_refs: Tuple[str, ...]
    revision_targets: Tuple[str, ...]
    discriminating_tests: Tuple[str, ...]
    unconceived_alternative_risk: bool
    consequence_divergence: bool
    rationale: Tuple[str, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)
    execution_authority: bool = False
    requires_reht_clearance: bool = True

    @property
    def requires_human_review(self) -> bool:
        return (
            self.epistemic_state == EpistemicState.UNDERDETERMINED
            and self.consequence_divergence
        )

    @property
    def common_bounded_action_possible(self) -> bool:
        return (
            self.epistemic_state != EpistemicState.INSUFFICIENT_EVIDENCE
            and not self.consequence_divergence
        )

    def to_dict(self) -> Mapping[str, object]:
        return {
            "epistemic_state": self.epistemic_state.value,
            "kind": self.kind.value,
            "surviving_alternatives": [
                {
                    "alternative_id": alternative.alternative_id,
                    "claim": alternative.claim,
                    "evidence_refs": list(alternative.evidence_refs),
                    "auxiliary_assumptions": list(alternative.auxiliary_assumptions),
                    "discriminating_tests": list(alternative.discriminating_tests),
                    "consequences": list(alternative.consequences),
                    "viable": alternative.viable,
                }
                for alternative in self.surviving_alternatives
            ],
            "shared_evidence_refs": list(self.shared_evidence_refs),
            "revision_targets": list(self.revision_targets),
            "discriminating_tests": list(self.discriminating_tests),
            "unconceived_alternative_risk": self.unconceived_alternative_risk,
            "consequence_divergence": self.consequence_divergence,
            "requires_human_review": self.requires_human_review,
            "common_bounded_action_possible": self.common_bounded_action_possible,
            "rationale": list(self.rationale),
            "metadata": dict(self.metadata),
            "execution_authority": self.execution_authority,
            "requires_reht_clearance": self.requires_reht_clearance,
        }


class UnderdeterminationInputError(ValueError):
    pass


class EpistemicUnderdeterminationGate:
    """Classify non-uniqueness without manufacturing consensus."""

    def assess(
        self,
        *,
        alternatives: Sequence[AlternativeHypothesis],
        shared_evidence_refs: Sequence[str],
        failed_prediction: bool = False,
        revision_targets: Sequence[str] = (),
        unconceived_alternative_risk: bool = False,
        consequence_divergence: Optional[bool] = None,
        metadata: Optional[Mapping[str, object]] = None,
    ) -> UnderdeterminationAssessment:
        candidates = tuple(alternatives)
        self._validate_alternatives(candidates)

        surviving = tuple(candidate for candidate in candidates if candidate.viable)
        evidence = self._deduplicate(shared_evidence_refs)
        revisions = self._deduplicate(revision_targets)
        tests = self._deduplicate(
            test
            for candidate in surviving
            for test in candidate.discriminating_tests
        )

        if not surviving:
            return UnderdeterminationAssessment(
                epistemic_state=EpistemicState.INSUFFICIENT_EVIDENCE,
                kind=UnderdeterminationKind.NONE,
                surviving_alternatives=(),
                shared_evidence_refs=evidence,
                revision_targets=revisions,
                discriminating_tests=(),
                unconceived_alternative_risk=unconceived_alternative_risk,
                consequence_divergence=bool(consequence_divergence),
                rationale=("No viable alternative was supplied.",),
                metadata=dict(metadata or {}),
            )

        if not evidence:
            return UnderdeterminationAssessment(
                epistemic_state=EpistemicState.INSUFFICIENT_EVIDENCE,
                kind=UnderdeterminationKind.NONE,
                surviving_alternatives=surviving,
                shared_evidence_refs=(),
                revision_targets=revisions,
                discriminating_tests=tests,
                unconceived_alternative_risk=unconceived_alternative_risk,
                consequence_divergence=bool(consequence_divergence),
                rationale=("No shared evidence was supplied.",),
                metadata=dict(metadata or {}),
            )

        holist = failed_prediction and len(revisions) > 1
        contrastive = len(surviving) > 1

        if holist and contrastive:
            kind = UnderdeterminationKind.MIXED
        elif holist:
            kind = UnderdeterminationKind.HOLIST
        elif contrastive:
            kind = UnderdeterminationKind.CONTRASTIVE
        else:
            kind = UnderdeterminationKind.NONE

        state = (
            EpistemicState.DETERMINED
            if kind == UnderdeterminationKind.NONE
            else EpistemicState.UNDERDETERMINED
        )

        divergent = (
            self._infer_consequence_divergence(surviving)
            if consequence_divergence is None
            else consequence_divergence
        )

        rationale = []
        if holist:
            rationale.append(
                "The failed prediction leaves multiple defensible revision targets."
            )
        if contrastive:
            rationale.append(
                "Multiple materially distinct alternatives survive the shared evidence."
            )
        if unconceived_alternative_risk:
            rationale.append(
                "The considered alternatives may not exhaust the credible hypothesis space."
            )
        if state == EpistemicState.DETERMINED:
            rationale.append(
                "At most one viable alternative remains and no holist blame ambiguity was supplied."
            )

        return UnderdeterminationAssessment(
            epistemic_state=state,
            kind=kind,
            surviving_alternatives=surviving,
            shared_evidence_refs=evidence,
            revision_targets=revisions,
            discriminating_tests=tests,
            unconceived_alternative_risk=unconceived_alternative_risk,
            consequence_divergence=divergent,
            rationale=tuple(rationale),
            metadata=dict(metadata or {}),
        )

    @staticmethod
    def _validate_alternatives(
        alternatives: Tuple[AlternativeHypothesis, ...]
    ) -> None:
        ids = [alternative.alternative_id for alternative in alternatives]
        if any(not alternative_id.strip() for alternative_id in ids):
            raise UnderdeterminationInputError("Alternative IDs must be non-empty")
        if len(ids) != len(set(ids)):
            raise UnderdeterminationInputError("Alternative IDs must be unique")
        if any(not alternative.claim.strip() for alternative in alternatives):
            raise UnderdeterminationInputError("Alternative claims must be non-empty")

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> Tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                str(value).strip() for value in values if str(value).strip()
            )
        )

    @staticmethod
    def _infer_consequence_divergence(
        alternatives: Tuple[AlternativeHypothesis, ...]
    ) -> bool:
        consequence_sets = {
            tuple(sorted(alternative.consequences))
            for alternative in alternatives
            if alternative.consequences
        }
        return len(consequence_sets) > 1
