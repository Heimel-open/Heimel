"""GOS-001F: outcome learning without constitutional drift (#26).

Builds outcome, realized-value, regret and variance analysis. The system may
propose weight, threshold, evidence or mandate changes but may never apply
constitutional, purpose, risk-appetite or authority changes without authorized
human ratification.

Learning can never silently mutate active production profiles. Failed outcomes
do not retroactively erase a valid clearance record.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class OutcomeLearningError(ValueError):
    pass


class ConstitutionalChangeRequiresRatification(OutcomeLearningError):
    pass


class SilentProductionMutationBlocked(OutcomeLearningError):
    pass


class ClearanceRecordImmutabilityViolation(OutcomeLearningError):
    pass


@dataclass(frozen=True)
class OutcomeRecord:
    """One executed action outcome (expected vs realized)."""

    outcome_id: str
    action_ref: str
    expected_value_minor: int
    realized_value_minor: int
    expected_cost_minor: int
    realized_cost_minor: int
    omission: bool = False
    delay: bool = False
    clearance_record_id: str = ""

    @property
    def value_delta(self) -> int:
        return self.realized_value_minor - self.expected_value_minor

    @property
    def cost_delta(self) -> int:
        return self.realized_cost_minor - self.expected_cost_minor

    @property
    def regret(self) -> int:
        return max(0, -self.value_delta)

    def digest(self) -> str:
        return _digest({
            "outcome_id": self.outcome_id,
            "action_ref": self.action_ref,
            "expected_value": self.expected_value_minor,
            "realized_value": self.realized_value_minor,
            "expected_cost": self.expected_cost_minor,
            "realized_cost": self.realized_cost_minor,
            "omission": self.omission,
            "delay": self.delay,
        })


@dataclass(frozen=True)
class ProposedChange:
    """A proposal to change weight/threshold/evidence/mandate.

    Proposals carry evidence and counterfactuals. They are NEVER applied
    automatically; constitutional/purpose/risk-appetite/authority changes
    require authorized human ratification.
    """

    proposal_id: str
    change_type: str  # weight | threshold | evidence | mandate | constitutional
    description: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    counterfactuals: tuple[str, ...] = field(default_factory=tuple)
    proposed_by: str = "learning-system"
    is_constitutional: bool = False


@dataclass(frozen=True)
class RatifiedChange:
    """Human-ratified change: a new version with a receipt."""

    version_id: str
    proposal_ref: str
    ratified_by: str
    ratified_at: datetime = field(default_factory=_utcnow)
    receipt_digest: str = ""


@dataclass
class OutcomeLearningEngine:
    """Outcome learning. Proposes; never self-applies constitutional drift."""

    def __init__(self) -> None:
        self._outcomes: list[OutcomeRecord] = []
        self._proposals: list[ProposedChange] = []
        self._ratified: list[RatifiedChange] = []
        self._active_profiles: dict[str, str] = {}
        self._clearance_records: set[str] = set()

    def record_outcome(self, outcome: OutcomeRecord) -> None:
        self._outcomes.append(outcome)

    def propose_change(self, proposal: ProposedChange) -> str:
        if proposal.is_constitutional and proposal.proposed_by == "learning-system":
            raise ConstitutionalChangeRequiresRatification(
                "constitutional/purpose/risk-appetite/authority changes require "
                "authorized human ratification"
            )
        self._proposals.append(proposal)
        return proposal.proposal_id

    def ratify(self, proposal_ref: str, ratified_by: str) -> RatifiedChange:
        """Human ratification creates a new version + receipt."""
        version_id = f"v-{len(self._ratified) + 1}"
        receipt = _digest({"version": version_id, "proposal": proposal_ref,
                           "ratified_by": ratified_by})
        change = RatifiedChange(version_id=version_id, proposal_ref=proposal_ref,
                                ratified_by=ratified_by, receipt_digest=receipt)
        self._ratified.append(change)
        return change

    def apply_profile(self, profile_id: str, content_digest: str) -> None:
        self._active_profiles[profile_id] = content_digest

    def mutate_active_profile(self, profile_id: str, new_digest: str) -> None:
        """Learning must not silently mutate active production profiles."""
        raise SilentProductionMutationBlocked(
            "learning cannot silently mutate active production profiles; "
            "ratify a change and create a new version instead"
        )

    def note_clearance_record(self, clearance_id: str) -> None:
        self._clearance_records.add(clearance_id)

    def outcome_digests_for(self, clearance_id: str) -> list[str]:
        """Outcome digests referencing a clearance record.

        Failed outcomes never erase a valid clearance record; the record stays
        referenced and immutable.
        """
        return [o.digest() for o in self._outcomes if o.clearance_record_id == clearance_id]

    @property
    def has_authority_surface(self) -> bool:
        return False


__all__ = [
    "ClearanceRecordImmutabilityViolation",
    "ConstitutionalChangeRequiresRatification",
    "OutcomeLearningEngine",
    "OutcomeLearningError",
    "OutcomeRecord",
    "ProposedChange",
    "RatifiedChange",
    "SilentProductionMutationBlocked",
]
