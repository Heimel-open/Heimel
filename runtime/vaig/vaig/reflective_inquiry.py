"""Reflective Inquiry capability for VAIG.

The ReflectiveInquiryEngine orchestrates the existing TradecraftGate and
EpistemicUnderdeterminationGate together with reflection components to
produce a governed reflection outcome.

Key design constraints:
- Never ALLOW and never grants execution authority
- Allowed outcomes: STEP_UP, DEFER, HALT
- Policy ambiguity generates deterministic SAGE handoff metadata
- All outputs are deterministic: same input → same digest
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from vaig.analytic_tradecraft import (
    AnalyticTradecraftAssessment,
    AnalyticTradecraftGate,
    EvidenceItem,
    ExpectedObservation,
    KeyAssumption,
    TradecraftState,
)
from vaig.epistemic_underdetermination import (
    AlternativeHypothesis,
    EpistemicState,
    EpistemicUnderdeterminationGate,
    UnderdeterminationAssessment,
)
from vaig.reflection_components import (
    ConfidenceCalibration,
    CounterfactualExplorer,
    CounterfactualScenario,
    EvidenceGap,
    EvidenceGapDetector,
    PolicyAmbiguity,
    PolicyAmbiguityDetector,
    SageReferral,
)


class ReflectionOutcome(str, Enum):
    """The three allowed outcomes of the reflection layer.

    Never ALLOW — this layer is pure reflection, never authorization.
    """
    STEP_UP = "STEP_UP"
    DEFER = "DEFER"
    HALT = "HALT"


@dataclass(frozen=True)
class ReflectiveInquiryResult:
    """Deterministic output of the ReflectiveInquiryEngine.

    All fields are immutable and hashable.
    """

    outcome: ReflectionOutcome

    # --- Deterministic output fields ---
    reflection_trace: Tuple[str, ...] = ()
    """Sequential log of reasoning steps taken during reflection."""

    reflection_questions: Tuple[str, ...] = ()
    """Questions raised during the reflection process."""

    evidence_gaps: Tuple[EvidenceGap, ...] = ()
    """Identified gaps in the evidence base."""

    policy_ambiguities: Tuple[PolicyAmbiguity, ...] = ()
    """Ambiguous or conflicting policy rules."""

    counterfactuals: Tuple[CounterfactualScenario, ...] = ()
    """Counterfactual scenarios explored."""

    confidence_score: float = 0.0
    """Calibrated confidence in the assessment (0.0–1.0)."""

    epistemic_uncertainty: float = 0.0
    """Epistemic uncertainty about the situation (0.0–1.0)."""

    sage_referral: Optional[SageReferral] = None
    """Structured SAGE handoff metadata, populated when policy ambiguity
    is detected. Never mutates sessions."""

    # --- Optional gate results for receipt enrichment ---
    tradecraft_assessment: Optional[AnalyticTradecraftAssessment] = None
    underdetermination_assessment: Optional[UnderdeterminationAssessment] = None

    # --- Authority boundary ---
    execution_authority: bool = False
    """Always False for reflection-layer results."""

    # --- Metadata ---
    metadata: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "reflection_trace": list(self.reflection_trace),
            "reflection_questions": list(self.reflection_questions),
            "evidence_gaps": [
                {"gap_id": g.gap_id, "description": g.description,
                 "severity": g.severity, "evidence_refs": list(g.evidence_refs)}
                for g in self.evidence_gaps
            ],
            "policy_ambiguities": [
                {"ambiguity_id": a.ambiguity_id, "description": a.description,
                 "severity": a.severity, "policy_refs": list(a.policy_refs)}
                for a in self.policy_ambiguities
            ],
            "counterfactuals": [
                {"counterfactual_id": c.counterfactual_id,
                 "description": c.description,
                 "antecedent": c.antecedent, "consequent": c.consequent,
                 "severity": c.severity, "hypothesis_refs": list(c.hypothesis_refs)}
                for c in self.counterfactuals
            ],
            "confidence_score": self.confidence_score,
            "epistemic_uncertainty": self.epistemic_uncertainty,
            "sage_referral": (
                {
                    "reason": self.sage_referral.reason,
                    "policy_refs": list(self.sage_referral.policy_refs),
                    "context": dict(self.sage_referral.context),
                }
                if self.sage_referral else None
            ),
            "execution_authority": self.execution_authority,
        }


class ReflectiveInquiryError(ValueError):
    """Raised on invalid input to the ReflectiveInquiryEngine."""
    pass


class ReflectiveInquiryEngine:
    """Orchestrates all reflection components into a governed outcome.

    The engine:
    1. Runs the AnalyticTradecraftGate on the evidence
    2. Runs the EpistemicUnderdeterminationGate on the alternatives
    3. Runs EvidenceGapDetector on evidence + observations
    4. Runs PolicyAmbiguityDetector on the risk contract snapshot
    5. Runs CounterfactualExplorer on alternatives + evidence
    6. Runs ConfidenceCalibration on all signals
    7. Produces a deterministic outcome: STEP_UP, DEFER, or HALT
    8. Generates SAGE referral metadata when policy ambiguity is found

    Never outputs ALLOW and never grants execution authority.
    """

    def __init__(
        self,
        tradecraft_gate: Optional[AnalyticTradecraftGate] = None,
        underdetermination_gate: Optional[EpistemicUnderdeterminationGate] = None,
        gap_detector: Optional[EvidenceGapDetector] = None,
        ambiguity_detector: Optional[PolicyAmbiguityDetector] = None,
        counterfactual_explorer: Optional[CounterfactualExplorer] = None,
        calibrator: Optional[ConfidenceCalibration] = None,
    ):
        self._tradecraft = tradecraft_gate or AnalyticTradecraftGate()
        self._underdetermination = underdetermination_gate or EpistemicUnderdeterminationGate()
        self._gap_detector = gap_detector or EvidenceGapDetector()
        self._ambiguity_detector = ambiguity_detector or PolicyAmbiguityDetector()
        self._counterfactual_explorer = counterfactual_explorer or CounterfactualExplorer()
        self._calibrator = calibrator or ConfidenceCalibration()

    def reflect(
        self,
        *,
        evidence: Sequence[EvidenceItem],
        alternatives: Sequence[AlternativeHypothesis],
        assumptions: Sequence[KeyAssumption] = (),
        expected_observations: Sequence[ExpectedObservation] = (),
        risk_contract_snapshot: Optional[Mapping[str, object]] = None,
        high_consequence: bool = False,
        minimum_independent_corroboration: int = 1,
        metadata: Optional[Mapping[str, object]] = None,
    ) -> ReflectiveInquiryResult:
        """Run the full reflection pipeline.

        All keyword-only arguments — same convention as existing gates.
        Returns a deterministic ReflectiveInquiryResult.
        """
        trace: List[str] = []
        questions: List[str] = []

        # --- Step 1: Run AnalyticTradecraftGate ---
        trace.append("Running AnalyticTradecraftGate on evidence and alternatives.")
        tradecraft_result = self._tradecraft.assess(
            evidence=evidence,
            alternatives=alternatives,
            assumptions=assumptions,
            expected_observations=expected_observations,
            high_consequence=high_consequence,
            minimum_independent_corroboration=minimum_independent_corroboration,
            metadata=metadata,
        )

        if tradecraft_result.state == TradecraftState.INSUFFICIENT:
            questions.append(
                "Tradecraft assessment is INSUFFICIENT — can the evidence base "
                "be strengthened or the analysis be restructured?"
            )

        # --- Step 2: Run EpistemicUnderdeterminationGate ---
        trace.append("Running EpistemicUnderdeterminationGate on alternatives.")
        underdetermination_result = self._underdetermination.assess(
            alternatives=alternatives,
            shared_evidence_refs=[
                item.evidence_id for item in evidence
            ],
        )

        if underdetermination_result.epistemic_state == EpistemicState.UNDERDETERMINED:
            questions.append(
                "Epistemic underdetermination detected — do the surviving "
                "alternatives have sufficiently divergent consequences?"
            )

        # --- Step 3: Evidence Gap Detection ---
        trace.append("Running EvidenceGapDetector.")
        evidence_gaps = self._gap_detector.detect(
            evidence, expected_observations,
        )

        # --- Step 4: Policy Ambiguity Detection ---
        trace.append("Running PolicyAmbiguityDetector.")
        policies = dict(risk_contract_snapshot) if risk_contract_snapshot else {}
        policy_ambiguities, sage_ref = self._ambiguity_detector.detect(policies)

        if policy_ambiguities:
            questions.append(
                "Policy ambiguity detected — has SAGE been notified for "
                "authoritative interpretation?"
            )

        # --- Step 5: Counterfactual Exploration ---
        trace.append("Running CounterfactualExplorer.")
        counterfactuals = self._counterfactual_explorer.explore(
            alternatives, evidence,
        )

        # --- Step 6: Confidence Calibration ---
        trace.append("Running ConfidenceCalibration.")
        confidence, uncertainty = self._calibrator.calibrate(
            evidence_gaps=evidence_gaps,
            policy_ambiguities=policy_ambiguities,
            counterfactuals=counterfactuals,
        )
        trace.append(
            f"Confidence: {confidence:.4f}, "
            f"Epistemic uncertainty: {uncertainty:.4f}."
        )

        # --- Step 7: Determine outcome ---
        outcome = self._determine_outcome(
            tradecraft_result=tradecraft_result,
            underdetermination_result=underdetermination_result,
            evidence_gaps=evidence_gaps,
            policy_ambiguities=policy_ambiguities,
            counterfactuals=counterfactuals,
            confidence=confidence,
            uncertainty=uncertainty,
            high_consequence=high_consequence,
            sage_ref=sage_ref,
        )
        trace.append(f"Outcome determined: {outcome.value}.")

        # Sort all lists for determinism
        return ReflectiveInquiryResult(
            outcome=outcome,
            reflection_trace=tuple(trace),
            reflection_questions=tuple(questions),
            evidence_gaps=tuple(sorted(evidence_gaps, key=lambda g: g.gap_id)),
            policy_ambiguities=tuple(sorted(policy_ambiguities, key=lambda a: a.ambiguity_id)),
            counterfactuals=tuple(sorted(counterfactuals, key=lambda c: c.counterfactual_id)),
            confidence_score=confidence,
            epistemic_uncertainty=uncertainty,
            sage_referral=sage_ref,
            tradecraft_assessment=tradecraft_result,
            underdetermination_assessment=underdetermination_result,
            execution_authority=False,
            metadata=dict(metadata or {}),
        )

    def _determine_outcome(
        self,
        *,
        tradecraft_result: AnalyticTradecraftAssessment,
        underdetermination_result: UnderdeterminationAssessment,
        evidence_gaps: Tuple[EvidenceGap, ...],
        policy_ambiguities: Tuple[PolicyAmbiguity, ...],
        counterfactuals: Tuple[CounterfactualScenario, ...],
        confidence: float,
        uncertainty: float,
        high_consequence: bool,
        sage_ref: Optional[SageReferral] = None,
    ) -> ReflectionOutcome:
        """Deterministic outcome function.

        Severity ladder (highest wins):
        1. HALT — critical risk, high-consequence + insufficient evidence
        2. STEP_UP — policy ambiguity requiring SAGE
        3. DEFER — evidence gaps or epistemic uncertainty
        4. DEFER (default) — conservative baseline

        Never ALLOW.
        """
        # HALT triggers
        if high_consequence and tradecraft_result.state != TradecraftState.SUFFICIENT:
            return ReflectionOutcome.HALT

        if high_consequence and any(
            g.severity == "HIGH" for g in evidence_gaps
        ):
            return ReflectionOutcome.HALT

        # STEP_UP triggers
        if policy_ambiguities and sage_ref is not None:
            return ReflectionOutcome.STEP_UP

        # DEFER triggers
        if evidence_gaps:
            return ReflectionOutcome.DEFER

        if uncertainty > 0.5:
            return ReflectionOutcome.DEFER

        if confidence < 0.6:
            return ReflectionOutcome.DEFER

        if underdetermination_result.epistemic_state == EpistemicState.UNDERDETERMINED:
            return ReflectionOutcome.DEFER

        if tradecraft_result.state == TradecraftState.CONSTRAINED:
            return ReflectionOutcome.DEFER

        # Default: conservative defer
        return ReflectionOutcome.DEFER
