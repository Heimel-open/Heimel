from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .common import utcnow
from .time import TimeWindow


class Obligation(BaseModel):
    """Canonical obligation: an executable duty. Makes obligations executable
    later by workflows."""

    obligation_id: str
    obligated_party: str
    action_required: str
    beneficiary: str | None = None
    basis: str
    trigger: str | None = None
    deadline: datetime | None = None
    completion_condition: str | None = None
    validity: TimeWindow
    status: str = "OPEN"  # OPEN | IN_PROGRESS | SATISFIED | FAILED | WAIVED

    model_config = ConfigDict(extra="forbid", frozen=True)

    def is_open(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        return self.status == "OPEN" and self.validity.is_active_at(moment) and (
            self.deadline is None or moment < self.deadline
        )
