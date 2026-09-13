"""
VALO ROI Gate v0.1

Pre-action value admissibility for AI agents.

Authority Gate asks: does the agent have the right to act?
ROI Gate asks: is the action worth the expected cost and risk?

Core rule:
    No expensive action without expected value.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class ROIDecision(Enum):
    ALLOW = "ALLOW"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


@dataclass(frozen=True)
class ROIEstimate:
    action_id: str
    expected_value_usd: float
    estimated_cost_usd: float
    risk_cost_usd: float = 0.0
    review_cost_usd: float = 0.0
    confidence: float = 1.0
    reversible: bool = True
    value_basis: str = "unspecified"
    cost_basis: str = "unspecified"

    @property
    def total_expected_cost_usd(self) -> float:
        return self.estimated_cost_usd + self.risk_cost_usd + self.review_cost_usd

    @property
    def net_expected_value_usd(self) -> float:
        return self.expected_value_usd - self.total_expected_cost_usd

    @property
    def roi_ratio(self) -> Optional[float]:
        if self.total_expected_cost_usd == 0:
            return None
        return self.expected_value_usd / self.total_expected_cost_usd


@dataclass(frozen=True)
class ROIPolicy:
    min_net_value_usd: float = 0.0
    min_roi_ratio: float = 1.0
    max_cost_without_step_up_usd: float = 10.0
    min_confidence: float = 0.70
    halt_on_irreversible_negative_value: bool = True


@dataclass(frozen=True)
class ROIResult:
    decision: ROIDecision
    reason: str
    estimate: ROIEstimate
    policy: ROIPolicy


class VALOROIGate:
    """
    Deterministic ROI admissibility gate.

    This class does not call a model. It evaluates an already supplied
    estimate against policy and returns an auditable decision.
    """

    def evaluate(self, estimate: ROIEstimate, policy: ROIPolicy | None = None) -> ROIResult:
        policy = policy or ROIPolicy()

        if estimate.confidence < 0 or estimate.confidence > 1:
            return ROIResult(ROIDecision.HALT, "confidence outside [0, 1]", estimate, policy)

        if estimate.estimated_cost_usd < 0 or estimate.expected_value_usd < 0:
            return ROIResult(ROIDecision.HALT, "negative value or cost estimate", estimate, policy)

        if estimate.confidence < policy.min_confidence:
            return ROIResult(
                ROIDecision.DEFER,
                f"confidence {estimate.confidence:.2f} below policy minimum {policy.min_confidence:.2f}",
                estimate,
                policy,
            )

        if (
            policy.halt_on_irreversible_negative_value
            and not estimate.reversible
            and estimate.net_expected_value_usd < 0
        ):
            return ROIResult(
                ROIDecision.HALT,
                "irreversible action has negative expected value",
                estimate,
                policy,
            )

        if estimate.net_expected_value_usd < policy.min_net_value_usd:
            return ROIResult(
                ROIDecision.DENY,
                f"net expected value {estimate.net_expected_value_usd:.2f} below minimum {policy.min_net_value_usd:.2f}",
                estimate,
                policy,
            )

        ratio = estimate.roi_ratio
        if ratio is not None and ratio < policy.min_roi_ratio:
            return ROIResult(
                ROIDecision.DENY,
                f"ROI ratio {ratio:.2f} below minimum {policy.min_roi_ratio:.2f}",
                estimate,
                policy,
            )

        if estimate.total_expected_cost_usd > policy.max_cost_without_step_up_usd:
            return ROIResult(
                ROIDecision.STEP_UP,
                f"expected cost {estimate.total_expected_cost_usd:.2f} exceeds step-up limit {policy.max_cost_without_step_up_usd:.2f}",
                estimate,
                policy,
            )

        return ROIResult(ROIDecision.ALLOW, "expected value exceeds cost and risk", estimate, policy)

    def receipt(self, result: ROIResult, packet: Dict[str, Any] | None = None) -> Dict[str, Any]:
        packet = packet or {}
        payload = {
            "packet": packet,
            "estimate": asdict(result.estimate),
            "policy": asdict(result.policy),
            "decision": result.decision.value,
            "reason": result.reason,
        }
        payload_hash = self._hash(payload)
        return {
            "receipt_id": str(uuid.uuid4()),
            "type": "valo.roi_gate.receipt.v1",
            "action_id": result.estimate.action_id,
            "decision": result.decision.value,
            "reason": result.reason,
            "expected_value_usd": result.estimate.expected_value_usd,
            "total_expected_cost_usd": result.estimate.total_expected_cost_usd,
            "net_expected_value_usd": result.estimate.net_expected_value_usd,
            "roi_ratio": result.estimate.roi_ratio,
            "confidence": result.estimate.confidence,
            "payload_hash": payload_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature": f"ed25519:{payload_hash.removeprefix('sha256:')[:64]}",
        }

    def _hash(self, data: Dict[str, Any]) -> str:
        normalized = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"
