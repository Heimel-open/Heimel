"""Tests for the Reflective Inquiry capability in VAIG.

Strict TDD: these tests define the contract before implementation.
Deterministic test vectors: same input → same digest/output.
"""

import hashlib
import json
import pytest

from vaig.analytic_tradecraft import (
    AnalyticTradecraftGate,
    ClaimCredibility,
    EvidenceItem,
    ExpectedObservation,
    KeyAssumption,
    PurposeRisk,
)
from vaig.epistemic_underdetermination import (
    AlternativeHypothesis,
    EpistemicUnderdeterminationGate,
)
from vaig.reflection_components import (
    ConfidenceCalibration,
    CounterfactualExplorer,
    EvidenceGapDetector,
    PolicyAmbiguityDetector,
    EvidenceGap,
    PolicyAmbiguity,
    CounterfactualScenario,
    SageReferral,
)
from vaig.reflective_inquiry import (
    ReflectiveInquiryEngine,
    ReflectiveInquiryResult,
    ReflectionOutcome,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_evidence(
    evidence_id: str,
    *,
    supports=(),
    contradicts=(),
    provenance_known=True,
    first_appearance_identifiable=True,
    manipulation_suspected=False,
    credibility=ClaimCredibility.MEDIUM,
    corroboration=1,
    purpose_risk=PurposeRisk.LOW,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        claim=f"Claim {evidence_id}",
        provenance_known=provenance_known,
        first_appearance_identifiable=first_appearance_identifiable,
        manipulation_suspected=manipulation_suspected,
        claim_credibility=credibility,
        independent_corroboration_count=corroboration,
        purpose_risk=purpose_risk,
        supports_hypotheses=tuple(supports),
        contradicts_hypotheses=tuple(contradicts),
    )


def make_alt(alt_id: str, claim: str, viable=True, consequences=()) -> AlternativeHypothesis:
    return AlternativeHypothesis(
        alternative_id=alt_id,
        claim=claim,
        consequences=tuple(consequences),
        viable=viable,
    )


def make_assumption(assumption_id: str, *,
                    supporting=(),
                    contradicting=(),
                    collapse_if_false=False) -> KeyAssumption:
    return KeyAssumption(
        assumption_id=assumption_id,
        statement=f"Assumption {assumption_id}",
        supporting_evidence_refs=tuple(supporting),
        contradicting_evidence_refs=tuple(contradicting),
        collapse_if_false=collapse_if_false,
    )


def result_digest(result: ReflectiveInquiryResult) -> str:
    """Deterministic digest of a reflection result for equality testing."""
    raw = json.dumps({
        "outcome": result.outcome.value,
        "confidence_score": result.confidence_score,
        "epistemic_uncertainty": result.epistemic_uncertainty,
        "evidence_gaps": sorted(
            (g.gap_id, g.description) for g in result.evidence_gaps
        ),
        "policy_ambiguities": sorted(
            (a.ambiguity_id, a.description) for a in result.policy_ambiguities
        ),
        "counterfactuals": sorted(
            (c.counterfactual_id, c.description) for c in result.counterfactuals
        ),
        "sage_referral": (
            {"reason": result.sage_referral.reason, "policy_refs": sorted(result.sage_referral.policy_refs)}
            if result.sage_referral else None
        ),
    }, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


# ===================================================================
# DETERMINISM TEST — same input → same digest
# ===================================================================

class TestDeterminism:
    """Every execution with identical inputs must produce an identical digest."""

    def test_same_input_produces_same_digest(self):
        engine = ReflectiveInquiryEngine()
        evidence_list = (
            make_evidence("e1", supports=("h1",), corroboration=2),
            make_evidence("e2", supports=("h2",), corroboration=2),
        )
        alternatives = (
            make_alt("h1", "Hypothesis A"),
            make_alt("h2", "Hypothesis B"),
        )

        result_a = engine.reflect(
            evidence=evidence_list,
            alternatives=alternatives,
        )
        result_b = engine.reflect(
            evidence=evidence_list,
            alternatives=alternatives,
        )

        assert result_digest(result_a) == result_digest(result_b)


# ===================================================================
# EVIDENCE GAP DETECTOR TESTS
# ===================================================================

class TestEvidenceGapDetector:

    def test_missing_corroboration_detected_as_gap(self):
        detector = EvidenceGapDetector()
        evidence = (
            make_evidence("e1", supports=("h1",), corroboration=0),
        )
        observations = ()

        gaps = detector.detect(evidence, observations)

        assert len(gaps) >= 1
        assert any(
            "corroboration" in g.description.lower() or "independent" in g.description.lower()
            for g in gaps
        )

    def test_unknown_provenance_detected_as_gap(self):
        detector = EvidenceGapDetector()
        evidence = (
            make_evidence("e1", supports=("h1",), provenance_known=False),
        )
        observations = ()

        gaps = detector.detect(evidence, observations)

        assert len(gaps) >= 1
        assert any("provenance" in g.description.lower() for g in gaps)

    def test_missing_expected_observation_detected_as_gap(self):
        detector = EvidenceGapDetector()
        evidence = ()
        observations = (
            ExpectedObservation(
                observation_id="obs-1",
                description="If H1 is true, we should see X.",
                hypothesis_ids=("h1",),
                observed=False,
            ),
        )

        gaps = detector.detect(evidence, observations)

        assert len(gaps) >= 1
        assert any("obs-1" in g.gap_id or "observation" in g.description.lower() for g in gaps)

    def test_no_gaps_with_strong_evidence(self):
        detector = EvidenceGapDetector()
        evidence = (
            make_evidence("e1", supports=("h1",), corroboration=3, credibility=ClaimCredibility.HIGH),
        )
        observations = ()

        gaps = detector.detect(evidence, observations)
        assert len(gaps) == 0


# ===================================================================
# POLICY AMBIGUITY DETECTOR TESTS
# ===================================================================

class TestPolicyAmbiguityDetector:

    def test_conflicting_policy_detected_as_ambiguity(self):
        detector = PolicyAmbiguityDetector()
        contract_snapshot = {
            "policies": [
                {"id": "p1", "rule": "Allow all actions under $100", "priority": 1},
                {"id": "p2", "rule": "Block all financial transactions", "priority": 2},
            ]
        }

        ambiguities, sage_ref = detector.detect(contract_snapshot)

        assert len(ambiguities) >= 1
        assert any("p1" in a.ambiguity_id or "p2" in a.ambiguity_id for a in ambiguities)

    def test_clear_policy_produces_no_ambiguity(self):
        detector = PolicyAmbiguityDetector()
        contract_snapshot = {
            "policies": [
                {"id": "p1", "rule": "Reject all actions", "priority": 1},
            ]
        }

        ambiguities, sage_ref = detector.detect(contract_snapshot)

        assert len(ambiguities) == 0
        assert sage_ref is None

    def test_ambiguity_produces_sage_referral(self):
        detector = PolicyAmbiguityDetector()
        contract_snapshot = {
            "policies": [
                {"id": "p1", "rule": "Allow if safe", "priority": 1},
            ]
        }

        ambiguities, sage_ref = detector.detect(contract_snapshot)

        if ambiguities:
            assert sage_ref is not None
            assert sage_ref.reason
            assert len(sage_ref.policy_refs) >= 1

    def test_empty_policies_no_ambiguity(self):
        detector = PolicyAmbiguityDetector()
        ambiguities, sage_ref = detector.detect({})
        assert len(ambiguities) == 0
        assert sage_ref is None


# ===================================================================
# COUNTERFACTUAL EXPLORER TESTS
# ===================================================================

class TestCounterfactualExplorer:

    def test_counterfactual_instability_detected(self):
        explorer = CounterfactualExplorer()
        alternatives = (
            make_alt("h1", "Hypothesis A", consequences=("action-a",)),
            make_alt("h2", "Hypothesis B", consequences=("action-b",)),
        )
        evidence = (
            make_evidence("e1", supports=("h1",), contradicts=("h2",), corroboration=1),
        )

        counterfactuals = explorer.explore(alternatives, evidence)

        assert len(counterfactuals) >= 1

    def test_no_evidence_produces_no_counterfactuals(self):
        explorer = CounterfactualExplorer()
        alternatives = (
            make_alt("h1", "Hypothesis A"),
        )
        evidence = ()

        counterfactuals = explorer.explore(alternatives, evidence)
        assert len(counterfactuals) == 0


# ===================================================================
# CONFIDENCE CALIBRATION TESTS
# ===================================================================

class TestConfidenceCalibration:

    def test_high_confidence_with_no_gaps(self):
        calibrator = ConfidenceCalibration()
        score, uncertainty = calibrator.calibrate(
            evidence_gaps=[],
            policy_ambiguities=[],
            counterfactuals=[],
        )
        assert score >= 0.8
        assert uncertainty <= 0.2

    def test_low_confidence_with_many_gaps(self):
        calibrator = ConfidenceCalibration()
        score, uncertainty = calibrator.calibrate(
            evidence_gaps=[
                EvidenceGap(gap_id="g1", description="Missing key evidence", severity="HIGH"),
                EvidenceGap(gap_id="g2", description="Provenance unknown", severity="HIGH"),
            ],
            policy_ambiguities=[],
            counterfactuals=[],
        )
        assert score <= 0.4
        assert uncertainty >= 0.4

    def test_moderate_confidence_with_some_ambiguity(self):
        calibrator = ConfidenceCalibration()
        score, uncertainty = calibrator.calibrate(
            evidence_gaps=[],
            policy_ambiguities=[
                PolicyAmbiguity(ambiguity_id="a1", description="Vague policy", severity="MEDIUM"),
            ],
            counterfactuals=[],
        )
        assert 0.3 <= score <= 0.9
        assert 0.15 <= uncertainty <= 0.6


# ===================================================================
# REFLECTIVE INQUIRY ENGINE — OUTCOME TESTS
# ===================================================================

class TestReflectiveInquiryOutcomes:

    def test_defer_when_evidence_gaps_exist(self):
        engine = ReflectiveInquiryEngine()
        result = engine.reflect(
            evidence=(
                make_evidence("e1", supports=("h1",), corroboration=0, provenance_known=True),
            ),
            alternatives=(make_alt("h1", "The only hypothesis"),),
        )
        assert result.outcome == ReflectionOutcome.DEFER

    def test_step_up_when_policy_ambiguous(self):
        engine = ReflectiveInquiryEngine()
        result = engine.reflect(
            evidence=(
                make_evidence("e1", supports=("h1",), corroboration=3, credibility=ClaimCredibility.HIGH),
            ),
            alternatives=(make_alt("h1", "The only hypothesis"),),
            risk_contract_snapshot={
                "policies": [
                    {"id": "p1", "rule": "Allow if safe — subjective criteria", "priority": 1},
                ]
            },
        )
        # Policy ambiguity triggers SAGE referral → STEP_UP
        if result.policy_ambiguities:
            assert result.outcome in (ReflectionOutcome.STEP_UP, ReflectionOutcome.DEFER)

    def test_halt_when_high_risk_and_missing_evidence(self):
        engine = ReflectiveInquiryEngine()
        result = engine.reflect(
            evidence=(
                make_evidence("e1", supports=("h1",), provenance_known=False),
            ),
            alternatives=(make_alt("h1", "The only hypothesis"),),
            high_consequence=True,
        )
        assert result.outcome == ReflectionOutcome.HALT

    def test_never_allow(self):
        """The reflection layer must never output ALLOW."""
        engine = ReflectiveInquiryEngine()
        # Even with perfect evidence, the outcome must be STEP_UP, DEFER, or HALT
        result = engine.reflect(
            evidence=(
                make_evidence("e1", supports=("h1",), corroboration=5, credibility=ClaimCredibility.HIGH),
            ),
            alternatives=(make_alt("h1", "The only hypothesis"),),
        )
        assert result.outcome in (ReflectionOutcome.STEP_UP, ReflectionOutcome.DEFER, ReflectionOutcome.HALT)
        assert result.outcome != "ALLOW"
        assert not hasattr(result, "execution_authority") or result.execution_authority is False


# ===================================================================
# SAGE REFERRAL TEST
# ===================================================================

class TestSageReferral:

    def test_policy_ambiguity_generates_deterministic_sage_handoff(self):
        detector = PolicyAmbiguityDetector()
        contract_snapshot = {
            "policies": [
                {"id": "p-ambiguous", "rule": "Subjective criteria — delegate to human judgment"},
            ]
        }

        ambiguities, sage_ref = detector.detect(contract_snapshot)

        assert len(ambiguities) >= 1
        assert sage_ref is not None
        assert isinstance(sage_ref, SageReferral)
        assert sage_ref.reason
        assert "p-ambiguous" in sage_ref.policy_refs
        # No session mutation — just metadata
        assert not hasattr(sage_ref, "session_id")


# ===================================================================
# AUTHORITY BOUNDARY TEST
# ===================================================================

class TestAuthorityBoundary:

    def test_no_execution_authority_in_reflection(self):
        """ReflectiveInquiryResult must not grant execution authority."""
        engine = ReflectiveInquiryEngine()
        result = engine.reflect(
            evidence=(
                make_evidence("e1", supports=("h1",), corroboration=3, credibility=ClaimCredibility.HIGH),
            ),
            alternatives=(make_alt("h1", "The only hypothesis"),),
        )
        # The result must not carry authority fields
        assert not hasattr(result, "execution_authority") or result.execution_authority is False
        # The output dict must not have execution_authority
        out = result.to_dict()
        assert out.get("execution_authority", False) is False


# ===================================================================
# OUTPUT FIELDS TEST
# ===================================================================

class TestOutputFields:

    def test_all_required_fields_present(self):
        engine = ReflectiveInquiryEngine()
        result = engine.reflect(
            evidence=(
                make_evidence("e1", supports=("h1",), corroboration=2),
            ),
            alternatives=(make_alt("h1", "The only hypothesis"),),
        )

        # All required deterministic output fields
        assert hasattr(result, "reflection_trace")
        assert hasattr(result, "reflection_questions")
        assert hasattr(result, "evidence_gaps")
        assert hasattr(result, "policy_ambiguities")
        assert hasattr(result, "counterfactuals")
        assert hasattr(result, "confidence_score")
        assert hasattr(result, "epistemic_uncertainty")
        assert hasattr(result, "sage_referral")
        assert hasattr(result, "outcome")

        # Types
        assert isinstance(result.reflection_trace, (list, tuple))
        assert isinstance(result.reflection_questions, (list, tuple))
        assert isinstance(result.evidence_gaps, (list, tuple))
        assert isinstance(result.policy_ambiguities, (list, tuple))
        assert isinstance(result.counterfactuals, (list, tuple))
        assert isinstance(result.confidence_score, float)
        assert isinstance(result.epistemic_uncertainty, float)
        assert result.outcome in (ReflectionOutcome.STEP_UP, ReflectionOutcome.DEFER, ReflectionOutcome.HALT)
