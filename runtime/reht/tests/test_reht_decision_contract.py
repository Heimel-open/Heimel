"""The authoritative REHT decision plane is exactly ALLOW | STEP_UP | DENY.

No wider outcome plane (MODIFY / DEFER / HALT) may be minted into the runtime.
"""

from __future__ import annotations

import pytest

from valo_reht.contracts import DecisionResult


@pytest.mark.parametrize("decision", ["ALLOW", "STEP_UP", "DENY"])
def test_valid_decision_accepted(decision: str) -> None:
    result = DecisionResult(decision=decision, reason="probe")
    assert result.decision == decision


@pytest.mark.parametrize("decision", ["MODIFY", "DEFER", "HALT"])
def test_wider_plane_rejected(decision: str) -> None:
    with pytest.raises(ValueError):
        DecisionResult(decision=decision, reason="probe")