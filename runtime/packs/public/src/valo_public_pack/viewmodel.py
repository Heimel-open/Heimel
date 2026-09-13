from __future__ import annotations

from typing import Any

from .domain import CaseState
from .golden import GoldenPathResult


def public_view_model(results: list[GoldenPathResult]) -> dict[str, Any]:
    """Minimal public view model — the entry point for a later Operator. No UI
    is built here."""
    awaiting_evidence = [r for r in results if r.case_state == CaseState.AWAITING_INFORMATION.value]
    ready_for_decision = [r for r in results if r.case_state == CaseState.READY_FOR_DECISION.value]
    requiring_human = [r for r in results if r.instance_status == "FAILED"]
    appealed = [r for r in results if r.case_state in (CaseState.APPEALED.value, CaseState.APPEAL_PERIOD.value)]
    return {
        "case_summary": {
            "cases": len(results),
            "awaiting_evidence": len(awaiting_evidence),
            "ready_for_decision": len(ready_for_decision),
            "requiring_human": len(requiring_human),
            "appeals": len(appealed),
        },
        "cases_awaiting_evidence": len(awaiting_evidence),
        "cases_ready_for_decision": len(ready_for_decision),
        "cases_requiring_human": len(requiring_human),
        "deadline_risk": len(appealed),
        "appeals": len(appealed),
        "consistency_alerts": [],
    }
