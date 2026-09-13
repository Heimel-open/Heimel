"""Reflection components for the Reflective Inquiry capability in VAIG.

Individual analytic building blocks that feed into the ReflectiveInquiryEngine:
- EvidenceGapDetector: identifies gaps in the evidence base
- PolicyAmbiguityDetector: flags ambiguous or conflicting policy rules
- CounterfactualExplorer: examines what changes if key evidence shifts
- ConfidenceCalibration: synthesises all signals into calibrated confidence

All components are deterministric: same inputs always produce the same outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from vaig.analytic_tradecraft import (
    EvidenceDisposition,
    EvidenceItem,
    ExpectedObservation,
)
from vaig.epistemic_underdetermination import AlternativeHypothesis


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceGap:
    """A specific gap in the evidence base identified during reflection."""
    gap_id: str
    description: str
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    evidence_refs: Tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyAmbiguity:
    """An ambiguity or conflict in policy rules detected during reflection."""
    ambiguity_id: str
    description: str
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    policy_refs: Tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CounterfactualScenario:
    """A counterfactual scenario explored during reflection."""
    counterfactual_id: str
    description: str
    antecedent: str
    consequent: str
    severity: str = "MEDIUM"
    hypothesis_refs: Tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SageReferral:
    """Structured handoff metadata for SAGE escalation — never mutates sessions.

    Generated deterministically when policy ambiguity is detected. Contains
    only the context needed for SAGE to make an informed ruling, without
    accessing or modifying any session state.
    """
    reason: str
    policy_refs: Tuple[str, ...] = ()
    context: Mapping[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# EvidenceGapDetector
# ---------------------------------------------------------------------------

class EvidenceGapDetector:
    """Identifies gaps in the evidence base.

    Checks:
    - Evidence with insufficient independent corroboration
    - Evidence with unknown provenance
    - Evidence flagged as manipulated
    - Expected observations that were not observed
    """

    def detect(
        self,
        evidence: Sequence[EvidenceItem],
        observations: Sequence[ExpectedObservation],
        tradecraft_assessment: Optional[Mapping[str, object]] = None,
    ) -> Tuple[EvidenceGap, ...]:
        """Run gap detection and return a deterministic tuple of gaps."""
        gaps: List[EvidenceGap] = []

        # Check each evidence item for quality flags
        for item in evidence:
            if item.independent_corroboration_count == 0:
                gaps.append(EvidenceGap(
                    gap_id=f"gap-corroboration-{item.evidence_id}",
                    description=(
                        f"Evidence '{item.evidence_id}' has zero independent "
                        f"corroboration sources."
                    ),
                    severity="HIGH",
                    evidence_refs=(item.evidence_id,),
                ))
            elif item.independent_corroboration_count == 1:
                gaps.append(EvidenceGap(
                    gap_id=f"gap-corroboration-weak-{item.evidence_id}",
                    description=(
                        f"Evidence '{item.evidence_id}' has only "
                        f"{item.independent_corroboration_count} independent "
                        f"corroboration source(s)."
                    ),
                    severity="MEDIUM",
                    evidence_refs=(item.evidence_id,),
                ))
            if not item.provenance_known:
                gaps.append(EvidenceGap(
                    gap_id=f"gap-provenance-{item.evidence_id}",
                    description=(
                        f"Provenance of evidence '{item.evidence_id}' is unknown."
                    ),
                    severity="HIGH",
                    evidence_refs=(item.evidence_id,),
                ))
            if not item.first_appearance_identifiable:
                gaps.append(EvidenceGap(
                    gap_id=f"gap-first-appearance-{item.evidence_id}",
                    description=(
                        f"First appearance of evidence '{item.evidence_id}' "
                        f"is not identifiable."
                    ),
                    severity="HIGH",
                    evidence_refs=(item.evidence_id,),
                ))
            if item.manipulation_suspected:
                gaps.append(EvidenceGap(
                    gap_id=f"gap-manipulation-{item.evidence_id}",
                    description=(
                        f"Manipulation or context drift is suspected for "
                        f"evidence '{item.evidence_id}'."
                    ),
                    severity="HIGH",
                    evidence_refs=(item.evidence_id,),
                ))

        # Check for missing expected observations
        for obs in observations:
            if not obs.observed:
                gaps.append(EvidenceGap(
                    gap_id=f"gap-observation-{obs.observation_id}",
                    description=(
                        f"Expected observation '{obs.observation_id}' "
                        f"({obs.description}) was not observed."
                    ),
                    severity="MEDIUM",
                    evidence_refs=(obs.evidence_ref,) if obs.evidence_ref else (),
                ))

        # Sort for determinism
        gaps.sort(key=lambda g: g.gap_id)
        return tuple(gaps)


# ---------------------------------------------------------------------------
# PolicyAmbiguityDetector
# ---------------------------------------------------------------------------

class PolicyAmbiguityDetector:
    """Detects ambiguous or conflicting policies.

    Rules of thumb for detecting ambiguity:
    - Vague or subjective language ('safe', 'reasonable', 'appropriate')
    - Conflicting rules (overlapping scope with different outcomes)
    - Empty or underspecified policies
    - Overlapping priorities without clear resolution
    """

    _VAGUE_TERMS = frozenset({
        "safe", "reasonable", "appropriate", "as needed", "if appropriate",
        "subject to", "as necessary", "adequate", "sufficient",
        "acceptable", "as determined", "at discretion", "when possible",
        "subjective", "human judgment", "delegate",
    })

    def detect(
        self,
        risk_contract_snapshot: Mapping[str, object],
    ) -> Tuple[Tuple[PolicyAmbiguity, ...], Optional[SageReferral]]:
        """Analyse policies and return ambiguities + optional SAGE referral.

        Returns:
            (ambiguities, sage_referral) where sage_referral is populated
            when any ambiguity is detected.
        """
        ambiguities: List[PolicyAmbiguity] = []
        policies = risk_contract_snapshot.get("policies", [])
        if not isinstance(policies, (list, tuple)):
            return (), None

        policy_ids: List[str] = []
        rule_texts: List[str] = []

        for idx, policy in enumerate(policies):
            if not isinstance(policy, dict):
                continue
            pid = str(policy.get("id", f"policy-{idx}"))
            rule = str(policy.get("rule", ""))
            policy_ids.append(pid)
            rule_texts.append(rule)

        # Phase 1: check for vague/subjective language
        for idx, (pid, rule) in enumerate(zip(policy_ids, rule_texts)):
            lower_rule = rule.lower()
            vague_matches = [t for t in self._VAGUE_TERMS if t in lower_rule]
            if vague_matches:
                ambiguities.append(PolicyAmbiguity(
                    ambiguity_id=f"ambiguity-vague-{pid}",
                    description=(
                        f"Policy '{pid}' uses vague language that requires "
                        f"subjective interpretation: {', '.join(vague_matches)}."
                    ),
                    severity="MEDIUM",
                    policy_refs=(pid,),
                ))

        # Phase 2: detect structural conflicts between policies
        # When two or more policies have distinct rule texts with overlapping
        # scope (same or similar priorities), a structural conflict exists.
        if len(policies) >= 2:
            for i in range(len(policies)):
                pid_i = policy_ids[i]
                rule_i = rule_texts[i].strip().lower()
                for j in range(i + 1, len(policies)):
                    pid_j = policy_ids[j]
                    rule_j = rule_texts[j].strip().lower()
                    if rule_i == rule_j:
                        continue  # exact duplicates are not conflicts
                    # Check for conflicting directionality
                    # (one allows, another blocks — same or similar scope)
                    conflict_found = False
                    i_allows = any(t in rule_i for t in ("allow", "permit", "accept", "approve"))
                    i_blocks = any(t in rule_i for t in ("block", "deny", "reject", "forbid", "refuse"))
                    j_allows = any(t in rule_j for t in ("allow", "permit", "accept", "approve"))
                    j_blocks = any(t in rule_j for t in ("block", "deny", "reject", "forbid", "refuse"))
                    conflict_found = (i_allows and j_blocks) or (i_blocks and j_allows)

                    # Also detect scope overlap (one allows on condition,
                    # another blocks on a broader condition)
                    if not conflict_found:
                        # Check for contextual overlap — e.g. "financial" vs "$"
                        scope_terms_i = set(t for t in rule_i.split() if len(t) > 3)
                        scope_terms_j = set(t for t in rule_j.split() if len(t) > 3)
                        shared_scope = scope_terms_i & scope_terms_j
                        # Check for threshold/amount terms
                        has_amount_i = "$" in rule_i or "€" in rule_j or any(c.isdigit() for c in rule_i)
                        has_amount_j = "$" in rule_j or "€" in rule_j or any(c.isdigit() for c in rule_j)
                        if has_amount_i and has_amount_j and shared_scope:
                            conflict_found = True

                    if conflict_found:
                        ambiguities.append(PolicyAmbiguity(
                            ambiguity_id=f"ambiguity-conflict-{pid_i}-vs-{pid_j}",
                            description=(
                                f"Policy '{pid_i}' conflicts with policy "
                                f"'{pid_j}' — rules have overlapping scope "
                                f"but contradictory direction."
                            ),
                            severity="HIGH",
                            policy_refs=(pid_i, pid_j),
                        ))

        # Sort for determinism
        ambiguities.sort(key=lambda a: a.ambiguity_id)

        # Generate SAGE referral if any ambiguity found
        sage_ref: Optional[SageReferral] = None
        if ambiguities:
            involved_pids = tuple(sorted(set(
                pid for a in ambiguities for pid in a.policy_refs
            )))
            sage_ref = SageReferral(
                reason=(
                    f"Policy ambiguity detected across {len(involved_pids)} "
                    f"policy rule(s). Reflection-layer escalation to SAGE is "
                    f"required for authoritative interpretation before "
                    f"proceeding."
                ),
                policy_refs=involved_pids,
                context={
                    "ambiguity_count": len(ambiguities),
                    "ambiguity_ids": [a.ambiguity_id for a in ambiguities],
                },
            )

        return tuple(ambiguities), sage_ref


# ---------------------------------------------------------------------------
# CounterfactualExplorer
# ---------------------------------------------------------------------------

class CounterfactualExplorer:
    """Explores counterfactual scenarios — what would change if key evidence or
    assumptions were different.

    Uses existing AlternativeHypothesis contracts from the epistemic
    underdetermination gate.
    """

    def explore(
        self,
        alternatives: Sequence[AlternativeHypothesis],
        evidence: Sequence[EvidenceItem],
        tradecraft_assessment: Optional[Mapping[str, object]] = None,
    ) -> Tuple[CounterfactualScenario, ...]:
        """Generate counterfactual scenarios.

        Explores:
        - What if key supporting evidence were absent?
        - What if contradictory evidence were present instead?
        - What if a non-viable alternative were viable?
        """
        scenarios: List[CounterfactualScenario] = []
        candidates = tuple(alternatives)

        if not evidence:
            return ()

        for item in evidence:
            # Counterfactual: key evidence is absent
            if item.supports_hypotheses or item.contradicts_hypotheses:
                hypo_ids = item.supports_hypotheses + item.contradicts_hypotheses
                scenarios.append(CounterfactualScenario(
                    counterfactual_id=f"cf-evidence-absent-{item.evidence_id}",
                    description=(
                        f"If evidence '{item.evidence_id}' were absent, "
                        f"hypotheses {hypo_ids} would lose supporting or "
                        f"contradicting signal."
                    ),
                    antecedent=f"Evidence '{item.evidence_id}' is unavailable",
                    consequent=(
                        f"Hypotheses {hypo_ids} lose a discriminating signal"
                    ),
                    severity="LOW" if item.independent_corroboration_count > 1 else "MEDIUM",
                    hypothesis_refs=tuple(hypo_ids),
                ))

        # Sort for determinism
        scenarios.sort(key=lambda s: s.counterfactual_id)
        return tuple(scenarios)


# ---------------------------------------------------------------------------
# ConfidenceCalibration
# ---------------------------------------------------------------------------

class ConfidenceCalibration:
    """Calibrates confidence and epistemic uncertainty from all signals.

    The calibration is a deterministic function of:
    - number and severity of evidence gaps
    - number and severity of policy ambiguities
    - number and severity of counterfactual scenarios

    Baseline confidence = 1.0. Each signal reduces it.
    """

    def calibrate(
        self,
        evidence_gaps: Sequence[EvidenceGap],
        policy_ambiguities: Sequence[PolicyAmbiguity],
        counterfactuals: Sequence[CounterfactualScenario],
    ) -> Tuple[float, float]:
        """Return (confidence_score, epistemic_uncertainty).

        Both values are 0.0–1.0 floats.
        confidence_score + epistemic_uncertainty is not constrained to sum
        to 1.0 — they capture different dimensions of the same assessment.
        """
        confidence = 1.0
        uncertainty = 0.0

        # Penalty per evidence gap
        for gap in evidence_gaps:
            severity_factor = {"LOW": 0.05, "MEDIUM": 0.15, "HIGH": 0.30}.get(gap.severity, 0.10)
            confidence -= severity_factor
            uncertainty += severity_factor * 0.8

        # Penalty per policy ambiguity
        for amb in policy_ambiguities:
            severity_factor = {"LOW": 0.05, "MEDIUM": 0.15, "HIGH": 0.25}.get(amb.severity, 0.10)
            confidence -= severity_factor
            uncertainty += severity_factor * 1.2

        # Penalty per counterfactual
        for cf in counterfactuals:
            severity_factor = {"LOW": 0.03, "MEDIUM": 0.08, "HIGH": 0.15}.get(cf.severity, 0.08)
            confidence -= severity_factor
            uncertainty += severity_factor * 0.5

        # Clamp
        confidence = max(0.0, min(1.0, confidence))
        uncertainty = max(0.0, min(1.0, uncertainty))

        return round(confidence, 4), round(uncertainty, 4)
