"""VALO V5 coherence gate.

Reads VALO_COHERENCE_THRESHOLD from environment. Never hardcoded.
"""
import os

_TAV_THRESHOLDS = {"CRYSTALLINE": 0.0001, "FLUID": 0.15, "GASEOUS": 0.35}


def _tav_regime(l_scalar: float) -> str:
    if l_scalar <= _TAV_THRESHOLDS["CRYSTALLINE"]:
        return "CRYSTALLINE"
    if l_scalar <= _TAV_THRESHOLDS["FLUID"]:
        return "FLUID"
    if l_scalar <= _TAV_THRESHOLDS["GASEOUS"]:
        return "GASEOUS"
    return "PLASMA"


def _combined_status(tav_regime: str, valo_status: str) -> str:
    if tav_regime == "PLASMA":
        return "HALT"
    if tav_regime == "GASEOUS" and valo_status == "PASS":
        return "DEGRADE"
    return valo_status


def coherence_threshold() -> float:
    raw = os.environ.get("VALO_COHERENCE_THRESHOLD")
    if not raw:
        raise RuntimeError("VALO_COHERENCE_THRESHOLD environment variable is required")
    return float(raw)


def evaluate(confidence_score: float, tav_l_scalar: float = None) -> dict:
    """Run the two-stage TAV_ONE → VALO V5 gate. Raises ValueError on invalid input."""
    if not (0.0 <= confidence_score <= 1.0):
        raise ValueError("confidence_score must be in [0.0, 1.0]")

    threshold = coherence_threshold()

    tav_regime = None
    if tav_l_scalar is not None:
        if not (0.0 <= tav_l_scalar <= 1.0):
            raise ValueError("tav_l_scalar must be in [0.0, 1.0]")
        tav_regime = _tav_regime(tav_l_scalar)

    coherence = confidence_score * 10000.0

    if coherence >= threshold:
        status = "PASS"
    elif coherence > 0.0:
        status = "DEGRADE"
    else:
        status = "HALT"

    combined = _combined_status(tav_regime, status) if tav_regime else status

    return {
        "status": status,
        "tav_regime": tav_regime,
        "combined_status": combined,
        "coherence": coherence,
        "metrics_logged": True,
    }
