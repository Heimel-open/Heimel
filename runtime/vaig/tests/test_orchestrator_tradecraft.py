from types import SimpleNamespace

from vaig.analytic_tradecraft import (
    AnalyticTradecraftGate,
    EvidenceItem,
    TradecraftState,
)
from vaig.ensemble import DistrustLevel, ValidationResult
from vaig.epistemic_underdetermination import (
    AlternativeHypothesis,
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
    instance.tradecraft_gate = AnalyticTradecraftGate()
    return instance


def alternative(alternative_id):
    return AlternativeHypothesis(
        alternative_id=alternative_id,
        claim="Explanation {}".format(alternative_id),
    )


def evidence(evidence_id, *, supports=(), contradicts=(), provenance=True):
    return EvidenceItem(
        evidence_id=evidence_id,
        claim="Claim {}".format(evidence_id),
        provenance_known=provenance,
        first_appearance_identifiable=provenance,
        independent_corroboration_count=1,
        supports_hypotheses=tuple(supports),
        contradicts_hypotheses=tuple(contradicts),
    )


def test_sufficient_tradecraft_does_not_halt_validation_flow():
    result = orchestrator().evaluate(
        "Why did the event occur?",
        "Evidence favors h2.",
        alternative_hypotheses=(alternative("h1"), alternative("h2")),
        tradecraft_evidence=(
            evidence("e1", supports=("h2",), contradicts=("h1",)),
        ),
    )

    assert result.tradecraft is not None
    assert result.tradecraft.state == TradecraftState.SUFFICIENT
    assert result.tradecraft_blocked is False
    assert result.requires_human_review is False
    assert result.should_halt is False


def test_insufficient_tradecraft_fails_closed_at_orchestrator_boundary():
    result = orchestrator().evaluate(
        "Why did the event occur?",
        "The only source has unknown provenance.",
        alternative_hypotheses=(alternative("h1"),),
        tradecraft_evidence=(
            evidence("e1", supports=("h1",), provenance=False),
        ),
    )

    assert result.tradecraft is not None
    assert result.tradecraft.state == TradecraftState.INSUFFICIENT
    assert result.tradecraft_blocked is True
    assert result.requires_human_review is True
    assert result.should_halt is True
    assert result.tradecraft.execution_authority is False


def test_constrained_tradecraft_steps_up_without_claiming_execution_authority():
    result = orchestrator().evaluate(
        "Why did the event occur?",
        "Evidence does not distinguish h1 from h2.",
        alternative_hypotheses=(alternative("h1"), alternative("h2")),
        tradecraft_evidence=(
            evidence("e1", supports=("h1", "h2")),
        ),
    )

    assert result.tradecraft is not None
    assert result.tradecraft.state == TradecraftState.CONSTRAINED
    assert result.tradecraft_blocked is False
    assert result.requires_human_review is True
    assert result.should_halt is False
    assert result.tradecraft.requires_reht_clearance is True


def test_orchestrator_remains_backward_compatible_without_tradecraft_inputs():
    result = orchestrator().evaluate("Prompt", "Response")

    assert result.tradecraft is None
    assert result.tradecraft_blocked is False
    assert result.requires_human_review is False
    assert result.should_halt is False
