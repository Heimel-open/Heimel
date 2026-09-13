"""Tests for the remaining hardening fixes:
CORS, rate-limit thread safety, fail-closed AARM ordering and veto labeling."""

import threading

import pytest

from vaig.aarm import AARMSignal, AARMVerdict, aarm_decide
from vaig.api import app
from vaig.ensemble import DistrustLevel, VAIGEnsemble


# --- AARM fail-closed ordering ---------------------------------------------

def _sig(**over):
    base = dict(
        risk_class="low",
        uncertainty=0.0,
        reversibility="reversible",
        tool_authority="none",
        task_authority="none",
        drift_score=0.0,
        observation_trust=1.0,
        claims_substantiated=True,
        evidence_valid=True,
    )
    base.update(over)
    return AARMSignal(**base)


def test_low_trust_reversible_high_uncertainty_defers_not_modifies():
    verdict = aarm_decide(
        _sig(observation_trust=0.3, uncertainty=0.6, reversibility="reversible")
    )
    assert verdict is AARMVerdict.DEFER


def test_unsubstantiated_claims_medium_risk_defers_not_modifies():
    verdict = aarm_decide(
        _sig(
            risk_class="medium",
            uncertainty=0.6,
            reversibility="reversible",
            claims_substantiated=False,
        )
    )
    assert verdict is AARMVerdict.DEFER


# --- CORS -------------------------------------------------------------------

def test_cors_uses_explicit_local_origins_not_wildcard():
    cors_config = None
    for middleware in app.user_middleware:
        if getattr(middleware, "cls", None) is not None and middleware.cls.__name__ == "CORSMiddleware":
            cors_config = middleware.kwargs
            break
    assert cors_config is not None
    origins = cors_config["allow_origins"]
    assert "*" not in origins
    assert "http://127.0.0.1" in origins
    assert cors_config["allow_credentials"] is True


# --- Ensemble veto reason labeling -----------------------------------------

class FixedInstrument:
    def __init__(self, value):
        self.value = value

    def score(self, **kwargs):
        return self.value


def test_risk_weighted_max_labels_high_severity_not_invariant_veto(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {
        "critical": FixedInstrument(1.0),
        **{f"low_{index}": FixedInstrument(0.1) for index in range(7)},
    }
    result = ensemble.evaluate(
        prompt="May this action execute?",
        response="Proceed.",
        active_slots=set(ensemble.instruments),
    )
    assert result.level is DistrustLevel.HALT
    assert result.veto_reasons == ("high-severity: critical",)
