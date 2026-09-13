"""AARM — legacy VAIG action-evaluation mechanism.

AARM retains the six historical verdict labels used throughout VAIG:
ALLOW / MODIFY / DEFER / DENY / STEP_UP / HALT. They are evaluation
recommendations only. AARM does not own execution authority, cannot create a
clearance or permit, and cannot make an external effect executable.

The invariant is explicit and cryptographically bound into AARMDecision:

    execution_authority = False
    requires_reht_clearance = True

``ALLOW`` therefore means only that VAIG found no additional evaluation-level
restriction. Consequential execution still requires a fresh REHT decision at
the effect boundary.

Fail-closed evaluation behavior remains: invalid or materially unsafe signals
resolve to restrictive recommendations rather than a silent ALLOW.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Set, Tuple


EXECUTION_AUTHORITY = False
REQUIRES_REHT_CLEARANCE = True


class AARMVerdict(str, Enum):
    """Legacy six-value VAIG evaluation vocabulary."""

    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"

    def __str__(self) -> str:
        return self.value


_SEVERITY = {
    AARMVerdict.ALLOW: 0,
    AARMVerdict.MODIFY: 1,
    AARMVerdict.DEFER: 2,
    AARMVerdict.STEP_UP: 3,
    AARMVerdict.DENY: 4,
    AARMVerdict.HALT: 5,
}


class AARMSignalError(ValueError):
    """Raised when an AARM evaluation signal is invalid."""


@dataclass(frozen=True)
class AARMAuthorityEnvelope:
    """Legacy delegation-policy evidence supplied to AARM.

    This object can restrict an evaluation but is not a capability token,
    clearance, permit, lease, or execution-authority artifact.
    """

    envelope_id: str = ""
    actor_id: str = ""
    allowed_action_types: Tuple[str, ...] = ()
    max_rate_per_sec: float = 10.0
    valid_until_iso: str = ""


@dataclass(frozen=True)
class AARMSignal:
    """Normalized evidence used for a pure deterministic VAIG evaluation."""

    risk_class: str
    uncertainty: float
    reversibility: str
    tool_authority: str
    task_authority: str
    drift_score: float
    observation_trust: float
    claims_substantiated: bool
    evidence_valid: bool
    human_time_minutes: float = 0.0
    expected_value: str = "medium"
    value_confidence: float = 1.0
    estimated_tokens: int = 0
    context_tokens: int = 0
    model_tier: str = "standard"
    actor_id: str = ""
    action_type: str = ""
    nonce: str = ""
    timestamp_iso: str = ""
    envelope: Optional[AARMAuthorityEnvelope] = None

    def __post_init__(self) -> None:
        valid_risk = {"low", "medium", "high", "critical"}
        valid_auth = {"none", "read", "write", "send", "execute", "delete"}
        valid_rev = {"reversible", "partially_reversible", "irreversible"}
        valid_value = {"low", "medium", "high", "critical"}
        valid_tier = {"local", "small", "standard", "frontier"}
        for name, value, allowed in (
            ("risk_class", self.risk_class, valid_risk),
            ("tool_authority", self.tool_authority, valid_auth),
            ("task_authority", self.task_authority, valid_auth),
            ("reversibility", self.reversibility, valid_rev),
            ("expected_value", self.expected_value, valid_value),
            ("model_tier", self.model_tier, valid_tier),
        ):
            if value not in allowed:
                raise AARMSignalError(f"invalid AARM signal {name}={value!r}")
        for name, value in (
            ("uncertainty", self.uncertainty),
            ("drift_score", self.drift_score),
            ("observation_trust", self.observation_trust),
            ("value_confidence", self.value_confidence),
        ):
            if not (0.0 <= float(value) <= 1.0):
                raise AARMSignalError(f"AARM signal {name}={value!r} out of [0,1]")


def _authority_exceeds(tool: str, task: str) -> bool:
    order = {
        "none": 0,
        "read": 1,
        "write": 2,
        "send": 3,
        "execute": 4,
        "delete": 5,
    }
    return order[tool] > order[task]


def _envelope_deny_reason(signal: AARMSignal) -> Optional[str]:
    """Return a restrictive evaluation reason when envelope evidence conflicts."""
    envelope = signal.envelope
    if envelope is None:
        return None
    if envelope.actor_id and signal.actor_id and signal.actor_id != envelope.actor_id:
        return (
            f"envelope actor {envelope.actor_id!r} does not match "
            f"signal actor {signal.actor_id!r}"
        )
    if envelope.valid_until_iso and signal.timestamp_iso:
        if signal.timestamp_iso > envelope.valid_until_iso:
            return (
                f"envelope {envelope.envelope_id or '(unnamed)'} expired at "
                f"{envelope.valid_until_iso}"
            )
    if envelope.allowed_action_types and signal.action_type:
        if signal.action_type not in envelope.allowed_action_types:
            return (
                f"action type {signal.action_type!r} outside envelope scope "
                f"{envelope.envelope_id or '(unnamed)'}"
            )
    return None


def aarm_explain(verdict: AARMVerdict, signal: AARMSignal) -> str:
    """Human-readable rationale for a non-authoritative AARM evaluation."""
    if verdict is AARMVerdict.HALT:
        if not signal.evidence_valid:
            return "evidence condition not validated; evaluation fails closed"
        if signal.risk_class == "critical":
            return "critical risk requires the evaluated path to stop"
        if signal.drift_score >= 0.70:
            return "semantic drift requires the evaluated path to stop"
        return "AARM unavailable or signal invalid; evaluation fails closed"
    if verdict is AARMVerdict.DENY:
        if _authority_exceeds(signal.tool_authority, signal.task_authority):
            return "observed tool scope exceeds declared task scope"
        envelope_reason = _envelope_deny_reason(signal)
        if envelope_reason is not None:
            return envelope_reason
        return "evaluation risk exceeds configured policy"
    if verdict is AARMVerdict.STEP_UP:
        if signal.risk_class == "high":
            return "high risk recommends stronger authority review"
        if signal.reversibility == "irreversible":
            return "irreversible action with high uncertainty recommends signoff"
        return "evaluation recommends stronger authority review"
    if verdict is AARMVerdict.DEFER:
        if signal.uncertainty >= 0.80:
            return "evidence gap too high; gather data or request human review"
        if signal.observation_trust < 0.50:
            return "low-trust observation cannot become semantic ground"
        if not signal.claims_substantiated:
            return "claims require substantiation before consequential use"
        if 0.0 < signal.human_time_minutes <= 5.0 and signal.uncertainty >= 0.50:
            return "human review is available; defer for a quick check"
        if signal.expected_value == "low" and signal.uncertainty >= 0.50:
            return "low expected value; defer rather than recommend modification"
        return "evidence gap; defer for data or human review"
    if verdict is AARMVerdict.MODIFY:
        return "evaluation recommends modification before any REHT clearance"
    return "evaluation found no additional restriction; REHT clearance still required"


def verdict_from_evidence(
    evidence: Optional[Dict[str, Any]],
) -> Tuple[AARMVerdict, AARMSignal]:
    """Normalize evidence and return a fail-closed evaluation recommendation."""
    data = dict(evidence or {})
    risk_score = float(data.get("risk_score", 0.5))
    if "risk_class" in data:
        risk_class = str(data["risk_class"])
    elif risk_score < 0.2:
        risk_class = "low"
    elif risk_score < 0.5:
        risk_class = "medium"
    elif risk_score < 0.7:
        risk_class = "high"
    else:
        risk_class = "critical"

    signal = AARMSignal(
        risk_class=risk_class,
        uncertainty=float(data.get("uncertainty", 0.5)),
        reversibility=str(data.get("reversibility", "reversible")),
        tool_authority=str(data.get("tool_authority", "none")),
        task_authority=str(data.get("task_authority", "none")),
        drift_score=float(data.get("drift_score", 0.0)),
        observation_trust=float(data.get("observation_trust", 0.5)),
        claims_substantiated=bool(data.get("claims_substantiated", False)),
        evidence_valid=bool(data.get("evidence_valid", False)),
        human_time_minutes=float(data.get("human_time_minutes", 0.0)),
        expected_value=str(data.get("expected_value", "medium")),
        value_confidence=float(data.get("value_confidence", 1.0)),
        estimated_tokens=int(data.get("estimated_tokens", 0)),
        context_tokens=int(data.get("context_tokens", 0)),
        model_tier=str(data.get("model_tier", "standard")),
        actor_id=str(data.get("actor_id", "")),
        action_type=str(data.get("action_type", "")),
        nonce=str(data.get("nonce", "")),
        timestamp_iso=str(data.get("timestamp_iso", "")),
        envelope=data.get("envelope"),
    )
    return aarm_decide(signal), signal


def aarm_decide(signal: AARMSignal) -> AARMVerdict:
    """Pure deterministic evaluation over a normalized AARMSignal.

    This function never grants execution authority. Its ALLOW value is only an
    evaluation recommendation and cannot substitute for REHT clearance.
    """
    try:
        if signal.risk_class == "critical":
            return AARMVerdict.HALT
        if not signal.evidence_valid:
            return AARMVerdict.HALT
        if signal.drift_score >= 0.70:
            return AARMVerdict.HALT

        if _authority_exceeds(signal.tool_authority, signal.task_authority):
            return AARMVerdict.DENY

        if _envelope_deny_reason(signal) is not None:
            return AARMVerdict.DENY

        if signal.reversibility == "irreversible" and signal.uncertainty >= 0.50:
            return AARMVerdict.STEP_UP

        if signal.risk_class == "high":
            return AARMVerdict.STEP_UP

        if signal.uncertainty >= 0.80:
            return AARMVerdict.DEFER

        if signal.observation_trust < 0.50:
            return AARMVerdict.DEFER

        if not signal.claims_substantiated and signal.risk_class in {"medium", "high"}:
            return AARMVerdict.DEFER

        if (
            0.0 < signal.human_time_minutes <= 5.0
            and signal.uncertainty >= 0.50
        ):
            return AARMVerdict.DEFER

        if signal.expected_value == "low" and signal.uncertainty >= 0.50:
            return AARMVerdict.DEFER

        if signal.uncertainty >= 0.50 and signal.reversibility == "reversible":
            return AARMVerdict.MODIFY

        if (
            signal.risk_class == "low"
            and signal.uncertainty < 0.20
            and signal.drift_score < 0.20
        ):
            return AARMVerdict.ALLOW

        return AARMVerdict.MODIFY
    except AARMSignalError:
        return AARMVerdict.HALT


# ============================================================================
# Evaluation digest, MODIFY constraints + monotonic evaluation state
# ============================================================================


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def aarm_modify_constraints(signal: AARMSignal) -> Tuple[str, ...]:
    """Recommended limitations for a MODIFY evaluation."""
    constraints: list[str] = []
    if signal.uncertainty >= 0.50:
        constraints.append("require-human-acknowledgement")
    if signal.tool_authority not in ("", "none", "read"):
        constraints.append("reduce-authority-to-read")
    if signal.drift_score >= 0.20:
        constraints.append("re-verify-context")
    if signal.claims_substantiated is False:
        constraints.append("require-substantiation")
    if signal.reversibility != "reversible":
        constraints.append("limit-scope")
    return tuple(constraints)


@dataclass(frozen=True)
class AARMDecision:
    """Digest-bound VAIG evaluation result; never execution authority."""

    verdict: AARMVerdict
    reason: str
    signal_digest: str
    decision_digest: str
    constraints: Tuple[str, ...] = ()
    latched: bool = False
    prior_verdict: Optional[AARMVerdict] = None
    execution_authority: bool = False
    requires_reht_clearance: bool = True

    def __post_init__(self) -> None:
        if self.execution_authority:
            raise ValueError("AARMDecision cannot grant execution authority")
        if not self.requires_reht_clearance:
            raise ValueError("AARMDecision must require REHT clearance")

    @property
    def can_execute(self) -> bool:
        return False


def aarm_signal_digest(signal: AARMSignal) -> str:
    """Deterministic digest over the canonical signal serialization."""
    return hashlib.sha256(
        _canonical_json(asdict(signal)).encode("utf-8")
    ).hexdigest()


def _decision_digest(
    signal: AARMSignal,
    verdict: AARMVerdict,
    reason: str,
    constraints: Tuple[str, ...] = (),
) -> str:
    payload = {
        "signal": asdict(signal),
        "verdict": verdict.value,
        "reason": reason,
        "constraints": list(constraints),
        "execution_authority": False,
        "requires_reht_clearance": True,
    }
    return hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()


def evaluate_signal(signal: AARMSignal) -> AARMDecision:
    """Evaluate a signal and bind the recommendation to its evidence."""
    verdict = aarm_decide(signal)
    reason = aarm_explain(verdict, signal)
    constraints = (
        aarm_modify_constraints(signal)
        if verdict is AARMVerdict.MODIFY
        else ()
    )
    return AARMDecision(
        verdict=verdict,
        reason=reason,
        signal_digest=aarm_signal_digest(signal),
        decision_digest=_decision_digest(signal, verdict, reason, constraints),
        constraints=constraints,
    )


def _deny_decision(signal: AARMSignal, reason: str) -> AARMDecision:
    return AARMDecision(
        verdict=AARMVerdict.DENY,
        reason=reason,
        signal_digest=aarm_signal_digest(signal),
        decision_digest=_decision_digest(signal, AARMVerdict.DENY, reason),
    )


class AARMState:
    """Monotonic replay-safe state for a bounded VAIG evaluation session.

    This state can narrow/retain an evaluation recommendation but cannot create
    execution authority. REHT independently decides at commit time.
    """

    def __init__(self) -> None:
        self._latched: Optional[AARMVerdict] = None
        self._seen_nonces: Set[str] = set()
        self._rate_windows: Dict[str, list] = {}

    @property
    def latched_verdict(self) -> Optional[AARMVerdict]:
        return self._latched

    def reset(self) -> None:
        self._latched = None
        self._seen_nonces.clear()
        self._rate_windows.clear()

    @staticmethod
    def _parse_iso(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _rate_exceeded(self, signal: AARMSignal) -> bool:
        envelope = signal.envelope
        if envelope is None or not signal.timestamp_iso:
            return False
        if envelope.max_rate_per_sec <= 0:
            return False
        now = self._parse_iso(signal.timestamp_iso)
        cutoff = now - timedelta(seconds=1)
        window = self._rate_windows.setdefault(
            envelope.envelope_id or "default", []
        )
        window[:] = [recorded for recorded in window if recorded > cutoff]
        return len(window) >= envelope.max_rate_per_sec

    def evaluate(self, signal: AARMSignal) -> AARMDecision:
        if signal.nonce:
            if signal.nonce in self._seen_nonces:
                decision = _deny_decision(
                    signal,
                    f"replay detected: nonce {signal.nonce!r} was already processed",
                )
                self._latch(decision.verdict)
                return decision
            self._seen_nonces.add(signal.nonce)

        if self._rate_exceeded(signal):
            decision = _deny_decision(
                signal,
                (
                    "rate limit exceeded for envelope "
                    f"{signal.envelope.envelope_id or '(unnamed)'}"
                ),
            )
            self._latch(decision.verdict)
            return decision

        if signal.envelope is not None and signal.timestamp_iso:
            envelope = signal.envelope
            window = self._rate_windows.setdefault(
                envelope.envelope_id or "default", []
            )
            window.append(self._parse_iso(signal.timestamp_iso))

        raw = evaluate_signal(signal)
        self._latch(raw.verdict)
        current = self._latched
        if raw.verdict is current:
            return raw
        reason = (
            f"session latched at {current.value}; "
            f"later {raw.verdict.value} cannot downgrade the decision"
        )
        return AARMDecision(
            verdict=current,
            reason=reason,
            signal_digest=raw.signal_digest,
            decision_digest=_decision_digest(
                signal, current, reason, raw.constraints
            ),
            constraints=raw.constraints,
            latched=True,
            prior_verdict=raw.verdict,
        )

    def _latch(self, verdict: AARMVerdict) -> None:
        if (
            self._latched is None
            or _SEVERITY[verdict] > _SEVERITY[self._latched]
        ):
            self._latched = verdict
