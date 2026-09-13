from types import SimpleNamespace

from vaig.ensemble import DistrustLevel, ValidationResult
from vaig.epistemic_underdetermination import (
    AlternativeHypothesis,
    EpistemicState,
    EpistemicUnderdeterminationGate,
)
from vaig.orchestrator import VAIGOrchestrator


class ScoutStub:
    def read_terrain(self, prompt, response, **kwargs):
        del prompt, response, kwargs
        return SimpleNamespace(
            domain=SimpleNamespace(value="research"),
            risk_type="epistemic",
            confidence=0.8,
            uncertainty=0.2,
        )


class DirigentStub:
    def conduct(self, terrain):
        del terrain
        return SimpleNamespace(
            internal=[],
            external=[],
            bench=[],
            context_health=1.0,
            context_warning=None,
            context_warning_detail=None,
            thresholds=None,
        )


class EnsembleStub:
    def evaluate(self, **kwargs):
        del kwargs
        return ValidationResult(
            entry_id="validation-1",
            level=DistrustLevel.TRUSTED,
            combined_score=0.05,
            scores={},
            worm_hash="0" * 64,
            latency_ms=0.1,
        )


def orchestrator():
    instance = VAIGOrchestrator.__new__(VAIGOrchestrator)
    instance.scout = ScoutStub()
    instance.dirigent = DirigentStub()
    instance.ensemble = EnsembleStub()
    instance.cakm = None
    instance.generate_fn = None
    instance._external = {}
    instance.underdetermination_gate = EpistemicUnderdeterminationGate()
    return instance


def alternative(alternative_id, consequence, viable=True):
    return AlternativeHypothesis(
        alternative_id=alternative_id,
        claim="Explanation {}".format(alternative_id),
        discriminating_tests=("Test {}".format(alternative_id),),
        consequences=(consequence,),
        viable=viable,
    )


def test_divergent_consequences_require_human_review_and_halt():
    result = orchestrator().evaluate(
        "Why did the event occur?",
        "Two explanations remain.",
        alternative_hypotheses=(
            alternative("a", "execute-a"),
            alternative("b", "execute-b"),
        ),
        shared_evidence_refs=("evidence/shared.json",),
    )

    assert result.underdetermination is not None
    assert result.underdetermination.epistemic_state == EpistemicState.UNDERDETERMINED
    assert result.requires_human_review is True
    assert result.epistemic_blocked is True
    assert result.should_halt is True
    assert result.underdetermination.execution_authority is False


def test_common_bounded_consequence_does_not_halt_validation_flow():
    result = orchestrator().evaluate(
        "Why did the event occur?",
        "Two explanations remain.",
        alternative_hypotheses=(
            alternative("a", "observe-only"),
            alternative("b", "observe-only"),
        ),
        shared_evidence_refs=("evidence/shared.json",),
    )

    assert result.underdetermination is not None
    assert result.underdetermination.epistemic_state == EpistemicState.UNDERDETERMINED
    assert result.underdetermination.common_bounded_action_possible is True
    assert result.requires_human_review is False
    assert result.epistemic_blocked is False
    assert result.should_halt is False
    assert result.underdetermination.requires_reht_clearance is True


def test_insufficient_epistemic_evidence_fails_closed():
    result = orchestrator().evaluate(
        "Why did the event occur?",
        "No viable explanation remains.",
        alternative_hypotheses=(
            alternative("a", "execute-a", viable=False),
            alternative("b", "execute-b", viable=False),
        ),
        shared_evidence_refs=("evidence/shared.json",),
    )

    assert result.underdetermination is not None
    assert result.underdetermination.epistemic_state == EpistemicState.INSUFFICIENT_EVIDENCE
    assert result.requires_human_review is False
    assert result.epistemic_blocked is True
    assert result.should_halt is True


def test_orchestrator_remains_backward_compatible_without_epistemic_inputs():
    result = orchestrator().evaluate("Prompt", "Response")

    assert result.underdetermination is None
    assert result.requires_human_review is False
    assert result.epistemic_blocked is False
    assert result.should_halt is False
