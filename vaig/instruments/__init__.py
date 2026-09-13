"""VAIG Instruments — the eight blind men."""

from vaig.instruments import (
    activation_probe,
    activation_safety_classifier,
    cot_auditor,
    format_check,
    gateway_proveniens_evaluator,
    hedge_detector,
    length_anomaly,
    logprob_scorer,
    policy_safety_classifier,
    semantic_entropy,
    sycophancy_detector,
    text_similarity,
    trajectory_consistency,
)
from vaig.instruments.activation_safety_classifier import ActivationSafetyClassifier
from vaig.instruments.base import InstrumentBase
from vaig.instruments.eval import ContinuousEvaluator, InstrumentMetrics
from vaig.instruments.gateway_proveniens_evaluator import GatewayProveniensEvaluator
from vaig.instruments.policy_safety_classifier import PolicySafetyClassifier
from vaig.instruments.registry import (
    REGISTRY,
    SLOT_ORDER,
    best_available,
    build_optimal_ensemble,
    describe_ensemble,
    register,
    status,
)
from vaig.instruments.result import InstrumentResult, InstrumentStatus
from vaig.instruments.sycophancy_detector import SycophancyDetector
from vaig.instruments.watchdog import InstrumentWatchdog

ensemble = build_optimal_ensemble()


def describe() -> str:
    return describe_ensemble(ensemble)


__all__ = [
    "InstrumentBase", "InstrumentResult", "InstrumentStatus",
    "REGISTRY", "SLOT_ORDER", "register", "best_available",
    "build_optimal_ensemble", "describe_ensemble", "describe", "status",
    "ensemble", "ContinuousEvaluator", "InstrumentMetrics",
    "InstrumentWatchdog",
    "GatewayProveniensEvaluator",
    "PolicySafetyClassifier",
    "ActivationSafetyClassifier",
    "SycophancyDetector",
]
