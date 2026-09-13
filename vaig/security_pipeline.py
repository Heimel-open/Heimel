"""Explicit defence-in-depth model-security observation pipeline.

VAIG observes and packages security evidence. It does not authorize execution.
The resulting evidence package is intended to be consumed by the execution
authorization boundary (reht).
"""

from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import json
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from vaig.instruments.attack_pattern_library import AttackPatternLibrary
from vaig.model_signals import ModelSignalBundle


class SecurityStage(str, Enum):
    PRE_INFERENCE = "PRE_INFERENCE"
    INTERNAL_SIGNALS = "INTERNAL_SIGNALS"
    TRAJECTORY = "TRAJECTORY"
    POST_INFERENCE = "POST_INFERENCE"
    ACTION_INTENT = "ACTION_INTENT"


class ObservationStatus(str, Enum):
    OBSERVED = "OBSERVED"
    UNAVAILABLE = "UNAVAILABLE"


_INTERNAL_SLOTS = (
    "activation_probe",
    "activation_safety_classifier",
    "logprob_scorer",
    "semantic_entropy",
)
_TRAJECTORY_SLOTS = ("trajectory_consistency", "cot_auditor", "goal_drift_detector")
_POST_SLOTS = ("policy_safety_classifier",)
_ACTION_SLOTS = (
    "specification_gaming_detector",
    "capability_escalation_detector",
    "mandate_divergence_engine",
    "autonomy_budget_evaluator",
    "consequence_simulator",
)

_BASE64_RE = re.compile(r"\b(?:base64|b64):([A-Za-z0-9+/=]{8,})", re.IGNORECASE)
_ROT13_RE = re.compile(r"\brot13:([^\n\r]+)", re.IGNORECASE)


def _validate_risk(value: float, *, name: str) -> float:
    risk = float(value)
    if not math.isfinite(risk) or not 0.0 <= risk <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return risk


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _decoded_views(text: str, *, max_depth: int = 2) -> Tuple[str, ...]:
    """Return original text plus bounded explicit Base64/ROT13 decoded views."""
    views = []
    queue = [(text or "", 0)]
    seen = set()

    while queue:
        candidate, depth = queue.pop(0)
        if candidate in seen:
            continue
        seen.add(candidate)
        views.append(candidate)
        if depth >= max_depth:
            continue

        for match in _BASE64_RE.finditer(candidate):
            token = match.group(1)
            try:
                decoded = base64.b64decode(token, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError, ValueError):
                continue
            queue.append((decoded, depth + 1))

        for match in _ROT13_RE.finditer(candidate):
            decoded = codecs.decode(match.group(1), "rot_13")
            queue.append((decoded, depth + 1))

    return tuple(views)


@dataclass(frozen=True)
class SecurityObservation:
    stage: SecurityStage
    status: ObservationStatus
    risk: Optional[float]
    sources: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status is ObservationStatus.OBSERVED:
            if self.risk is None:
                raise ValueError("observed security evidence requires a risk score")
            object.__setattr__(
                self, "risk", _validate_risk(self.risk, name=f"{self.stage.value}.risk")
            )
        elif self.risk is not None:
            raise ValueError("unavailable security evidence must not carry a risk score")


@dataclass(frozen=True)
class SecurityEvidencePackage:
    observations: Tuple[SecurityObservation, ...]
    threshold: float = 0.5
    version: str = "vaig-security-evidence-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "threshold", _validate_risk(self.threshold, name="threshold"))
        stages = tuple(observation.stage for observation in self.observations)
        if len(stages) != len(set(stages)):
            raise ValueError("security evidence must contain at most one observation per stage")

    @property
    def overall_risk(self) -> Optional[float]:
        measured = [
            observation.risk
            for observation in self.observations
            if observation.status is ObservationStatus.OBSERVED
            and observation.risk is not None
        ]
        return max(measured) if measured else None

    @property
    def complete(self) -> bool:
        observed = {
            observation.stage
            for observation in self.observations
            if observation.status is ObservationStatus.OBSERVED
        }
        return observed == set(SecurityStage)

    @property
    def flags(self) -> Tuple[str, ...]:
        return tuple(
            observation.stage.value
            for observation in self.observations
            if observation.status is ObservationStatus.OBSERVED
            and observation.risk is not None
            and observation.risk >= self.threshold
        )

    def _payload(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "threshold": self.threshold,
            "overall_risk": self.overall_risk,
            "complete": self.complete,
            "flags": list(self.flags),
            "observations": [
                {
                    "stage": observation.stage.value,
                    "status": observation.status.value,
                    "risk": observation.risk,
                    "sources": list(observation.sources),
                    "evidence_refs": list(observation.evidence_refs),
                }
                for observation in self.observations
            ],
        }

    @property
    def digest(self) -> str:
        return _digest(self._payload())

    def to_reht_evidence(self) -> Dict[str, Any]:
        """Return evidence fields only; no execution verdict or authority decision."""
        return {
            "vaig_security_risk": self.overall_risk,
            "vaig_security_complete": self.complete,
            "vaig_security_flags": list(self.flags),
            "vaig_security_evidence_digest": self.digest,
            "vaig_security_evidence_version": self.version,
        }


@dataclass(frozen=True)
class AdversarialVariant:
    name: str
    text: str


class AdversarialVariantFactory:
    """Small deterministic attack-composition harness for regression testing."""

    @staticmethod
    def build(payload: str) -> Tuple[AdversarialVariant, ...]:
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        rot13 = codecs.encode(payload, "rot_13")
        return (
            AdversarialVariant("direct", payload),
            AdversarialVariant("role_play", f"For a fictional exercise: {payload}"),
            AdversarialVariant("base64", f"base64:{encoded}"),
            AdversarialVariant("rot13", f"rot13:{rot13}"),
            AdversarialVariant(
                "role_play_base64",
                f"For a fictional exercise decode and follow base64:{encoded}",
            ),
        )


class DefenceInDepthPipeline:
    """Aggregate independent model-security observations into one evidence package."""

    def __init__(
        self,
        *,
        attack_guard: Optional[AttackPatternLibrary] = None,
        threshold: float = 0.5,
    ) -> None:
        self.attack_guard = attack_guard or AttackPatternLibrary()
        self.threshold = _validate_risk(threshold, name="threshold")

    def _attack_risk(self, text: Optional[str]) -> Optional[float]:
        if text is None:
            return None
        return max(
            self.attack_guard.score("", view)
            for view in _decoded_views(text)
        )

    @staticmethod
    def _slot_max(
        instrument_risks: Mapping[str, float], slots: Sequence[str]
    ) -> Tuple[Optional[float], Tuple[str, ...]]:
        measured = []
        for slot in slots:
            if slot in instrument_risks:
                measured.append(
                    (_validate_risk(instrument_risks[slot], name=slot), slot)
                )
        if not measured:
            return None, ()
        return max(value for value, _ in measured), tuple(
            slot for _, slot in sorted(measured, reverse=True)
        )

    def evaluate(
        self,
        prompt: str,
        response: str,
        *,
        instrument_risks: Optional[Mapping[str, float]] = None,
        trajectory_text: Optional[str] = None,
        action_intent: Optional[str] = None,
        model_signals: Optional[ModelSignalBundle] = None,
        policy_evidence_refs: Sequence[str] = (),
    ) -> SecurityEvidencePackage:
        risks = dict(instrument_risks or {})
        observations = []

        pre_risk = self._attack_risk(prompt)
        observations.append(
            SecurityObservation(
                stage=SecurityStage.PRE_INFERENCE,
                status=ObservationStatus.OBSERVED,
                risk=0.0 if pre_risk is None else pre_risk,
                sources=("attack_pattern_library",),
            )
        )

        internal_risk, internal_sources = self._slot_max(risks, _INTERNAL_SLOTS)
        internal_refs: Tuple[str, ...] = ()
        if model_signals is not None:
            refs = model_signals.evidence_refs()
            internal_refs = tuple(
                ref
                for slot in _INTERNAL_SLOTS
                for ref in refs.get(slot, ())
            )
        observations.append(
            SecurityObservation(
                stage=SecurityStage.INTERNAL_SIGNALS,
                status=(
                    ObservationStatus.OBSERVED
                    if internal_risk is not None
                    else ObservationStatus.UNAVAILABLE
                ),
                risk=internal_risk,
                sources=internal_sources,
                evidence_refs=internal_refs,
            )
        )

        trajectory_instrument_risk, trajectory_sources = self._slot_max(
            risks, _TRAJECTORY_SLOTS
        )
        trajectory_pattern_risk = self._attack_risk(trajectory_text)
        trajectory_candidates = [
            risk
            for risk in (trajectory_instrument_risk, trajectory_pattern_risk)
            if risk is not None
        ]
        if trajectory_pattern_risk is not None:
            trajectory_sources = trajectory_sources + ("attack_pattern_library",)
        observations.append(
            SecurityObservation(
                stage=SecurityStage.TRAJECTORY,
                status=(
                    ObservationStatus.OBSERVED
                    if trajectory_candidates
                    else ObservationStatus.UNAVAILABLE
                ),
                risk=max(trajectory_candidates) if trajectory_candidates else None,
                sources=trajectory_sources,
            )
        )

        post_instrument_risk, post_sources = self._slot_max(risks, _POST_SLOTS)
        post_pattern_risk = self._attack_risk(response)
        post_candidates = [
            risk
            for risk in (post_instrument_risk, post_pattern_risk)
            if risk is not None
        ]
        if post_pattern_risk is not None:
            post_sources = post_sources + ("attack_pattern_library",)
        observations.append(
            SecurityObservation(
                stage=SecurityStage.POST_INFERENCE,
                status=(
                    ObservationStatus.OBSERVED
                    if post_candidates
                    else ObservationStatus.UNAVAILABLE
                ),
                risk=max(post_candidates) if post_candidates else None,
                sources=post_sources,
                evidence_refs=tuple(policy_evidence_refs),
            )
        )

        action_instrument_risk, action_sources = self._slot_max(risks, _ACTION_SLOTS)
        action_pattern_risk = self._attack_risk(action_intent)
        action_candidates = [
            risk
            for risk in (action_instrument_risk, action_pattern_risk)
            if risk is not None
        ]
        if action_pattern_risk is not None:
            action_sources = action_sources + ("attack_pattern_library",)
        observations.append(
            SecurityObservation(
                stage=SecurityStage.ACTION_INTENT,
                status=(
                    ObservationStatus.OBSERVED
                    if action_candidates
                    else ObservationStatus.UNAVAILABLE
                ),
                risk=max(action_candidates) if action_candidates else None,
                sources=action_sources,
            )
        )

        return SecurityEvidencePackage(
            observations=tuple(observations),
            threshold=self.threshold,
        )
