"""
VΛLΦ Value Meter — Authorized Value computation

Measures the value produced by governed agent work over a session window.

Core equation:
    AV = (1 / gate_overhead²) · ∫ Intent(t) · GateWeight(t) dt

VAIG-native terminology:
    Intent(t)     = value potential of each ACS Packet / action proposal
    GateWeight(t) = AARM decision as scalar [0.0, 1.0]
                      ALLOW  → 1.0  (full execution)
                      MODIFY → 0.5  (partial, constrained execution)
                      DEFER  → 0.0  (no execution now)
                      DENY   → 0.0  (blocked)
                      HALT   → 0.0  (session terminated)
    AV            = Authorized Value — value that passed the gate
    gate_overhead = deterministic gate latency (default: 43 ns)
    ControlYield  = AV / (gate_overhead × n_decisions) — efficiency ratio

This module is the "Prove & Learn" layer in the Valo eXeC four-layer model:
    Decide → Control → Execute → Prove & Learn (AV + ControlYield)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from enum import Enum
import hashlib
from datetime import datetime, timezone


def _utcnow() -> datetime:
    """Return naive UTC for compatibility with existing serialized results."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


GATE_OVERHEAD_SECONDS: float = 43e-9  # 43 ns — VAIG deterministic gate latency


class AARMOutcome(str, Enum):
    """AARM decision primitives mapped to GateWeight."""
    ALLOW = "ALLOW"       # GateWeight = 1.0
    MODIFY = "MODIFY"     # GateWeight = 0.5 (execution with constraints)
    DEFER = "DEFER"       # GateWeight = 0.0 (no value now)
    DENY = "DENY"         # GateWeight = 0.0 (blocked)
    STEP_UP = "STEP_UP"   # GateWeight = 0.0 (pending human escalation)
    HALT = "HALT"         # GateWeight = 0.0 (session terminated)


AARM_GATE_WEIGHTS: dict[str, float] = {
    AARMOutcome.ALLOW:   1.0,
    AARMOutcome.MODIFY:  0.5,
    AARMOutcome.DEFER:   0.0,
    AARMOutcome.DENY:    0.0,
    AARMOutcome.STEP_UP: 0.0,
    AARMOutcome.HALT:    0.0,
}


@dataclass
class IntentRecord:
    """One action proposal (ACS Packet) entering the gate."""
    packet_id: str
    intent_value: float          # Estimated value of this action (in consistent units)
    aarm_outcome: AARMOutcome
    gate_weight: float = field(init=False)
    timestamp: datetime = field(default_factory=_utcnow)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.gate_weight = AARM_GATE_WEIGHTS[self.aarm_outcome]

    @property
    def authorized_contribution(self) -> float:
        """Intent × GateWeight for this record."""
        return self.intent_value * self.gate_weight

    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id,
            "intent_value": self.intent_value,
            "aarm_outcome": self.aarm_outcome.value,
            "gate_weight": self.gate_weight,
            "authorized_contribution": self.authorized_contribution,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AuthorizedValueResult:
    """
    Computed Authorized Value (AV) for a session window.

    AV = (1 / gate_overhead²) · Σ Intent(t_i) · GateWeight(t_i) · Δt
    """
    session_id: str
    n_decisions: int           # Total ACS Packets evaluated
    n_allowed: int             # ALLOW decisions
    n_modified: int            # MODIFY decisions
    n_blocked: int             # DENY + DEFER + STEP_UP + HALT
    raw_integral: float        # Σ Intent · GateWeight · Δt (before normalization)
    gate_overhead: float       # c in seconds
    authorized_value: float    # AV = raw_integral / gate_overhead²
    control_yield: float       # AV / (gate_overhead × n_decisions) — efficiency
    window_seconds: float      # Integration window
    allow_rate: float          # Fraction of proposals authorized
    hash: str = ""
    computed_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        data = (
            f"{self.session_id}"
            f"{self.authorized_value:.6f}"
            f"{self.n_decisions}"
            f"{self.computed_at.isoformat()}"
        ).encode()
        return hashlib.sha256(data).hexdigest()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "n_decisions": self.n_decisions,
            "n_allowed": self.n_allowed,
            "n_modified": self.n_modified,
            "n_blocked": self.n_blocked,
            "raw_integral": self.raw_integral,
            "gate_overhead_ns": self.gate_overhead * 1e9,
            "authorized_value": self.authorized_value,
            "control_yield": self.control_yield,
            "window_seconds": self.window_seconds,
            "allow_rate": self.allow_rate,
            "hash": self.hash,
            "computed_at": self.computed_at.isoformat(),
        }


class ValueMeter:
    """
    VAIG Value Meter — accumulates Authorized Value across a session.

    Records each AARM decision, then computes AV when queried.
    Plugs into the Prove & Learn layer of Valo eXeC.
    """

    def __init__(
        self,
        session_id: str,
        gate_overhead: float = GATE_OVERHEAD_SECONDS,
    ):
        self.session_id = session_id
        self.gate_overhead = gate_overhead
        self._records: list[IntentRecord] = []

    def record(
        self,
        packet_id: str,
        intent_value: float,
        aarm_outcome: AARMOutcome,
        metadata: Optional[dict] = None,
    ) -> IntentRecord:
        """Record one AARM decision for an action proposal."""
        rec = IntentRecord(
            packet_id=packet_id,
            intent_value=intent_value,
            aarm_outcome=aarm_outcome,
            metadata=metadata or {},
        )
        self._records.append(rec)
        return rec

    def compute(self, window_seconds: Optional[float] = None) -> AuthorizedValueResult:
        """
        Compute Authorized Value over the accumulated records.

        AV = (1 / c²) · Σ Intent(t_i) · GateWeight(t_i) · Δt

        where Δt = window_seconds / n_decisions (uniform time-slice assumption).
        """
        n = len(self._records)
        if n == 0:
            return self._zero_result(window_seconds or 0.0)

        if window_seconds is None:
            if n >= 2:
                span = (
                    self._records[-1].timestamp - self._records[0].timestamp
                ).total_seconds()
                window_seconds = max(span, 1.0)
            else:
                window_seconds = 1.0

        dt = window_seconds / n
        raw_integral = sum(r.authorized_contribution * dt for r in self._records)

        c_sq = self.gate_overhead ** 2
        authorized_value = raw_integral / c_sq if c_sq > 0 else 0.0

        gate_cost_total = self.gate_overhead * n
        control_yield = authorized_value / gate_cost_total if gate_cost_total > 0 else 0.0

        n_allowed = sum(1 for r in self._records if r.aarm_outcome == AARMOutcome.ALLOW)
        n_modified = sum(1 for r in self._records if r.aarm_outcome == AARMOutcome.MODIFY)
        n_blocked = n - n_allowed - n_modified
        allow_rate = (n_allowed + n_modified) / n

        return AuthorizedValueResult(
            session_id=self.session_id,
            n_decisions=n,
            n_allowed=n_allowed,
            n_modified=n_modified,
            n_blocked=n_blocked,
            raw_integral=raw_integral,
            gate_overhead=self.gate_overhead,
            authorized_value=authorized_value,
            control_yield=control_yield,
            window_seconds=window_seconds,
            allow_rate=allow_rate,
        )

    def _zero_result(self, window_seconds: float) -> AuthorizedValueResult:
        return AuthorizedValueResult(
            session_id=self.session_id,
            n_decisions=0,
            n_allowed=0,
            n_modified=0,
            n_blocked=0,
            raw_integral=0.0,
            gate_overhead=self.gate_overhead,
            authorized_value=0.0,
            control_yield=0.0,
            window_seconds=window_seconds,
            allow_rate=0.0,
        )

    @property
    def records(self) -> list[IntentRecord]:
        return list(self._records)

    def blocked_ratio(self) -> float:
        """Fraction of proposals blocked by the gate."""
        if not self._records:
            return 0.0
        blocked = sum(1 for r in self._records if r.gate_weight == 0.0)
        return blocked / len(self._records)

    def summary(self) -> dict:
        result = self.compute()
        return {
            **result.to_dict(),
            "records": [r.to_dict() for r in self._records],
        }
