from __future__ import annotations

from typing import Any

from .golden import Scenario, run_golden


def explain(kernel, case_state: str | None, scenario: Scenario | None = None) -> dict[str, Any]:
    """Structured explain from state — never chain-of-thought. 'Why was this
    case not decided?' answers with the Kernel's actual raw state fields."""
    scenario = scenario or Scenario()
    attributes = {}
    try:
        entity = kernel.state().entities["case-1"]
        attributes = entity.attributes or {}
    except KeyError:
        pass
    legal_active = any(
        a.capability == "LEGAL_BASIS" and a.is_active()
        for a in kernel.state().authorities.values()
    )
    evidence = attributes.get("evidence") or []
    return {
        "case_state": case_state,
        "legal_basis_active": legal_active,
        "competence_active": scenario.competence_active and not scenario.revoke_competence,
        "evidence_status": [e.get("status") for e in evidence],
        "evidence_purpose": [e.get("purpose") for e in evidence],
        "eligibility_from_raw": (
            "ELIGIBLE" if attributes.get("residency_fact") == "CONFIRMED" and (attributes.get("age") or 0) >= 18 else "UNKNOWN"
        ),
        "residency_fact": attributes.get("residency_fact"),
        "representation_scope": (attributes.get("representation") or {}).get("scope"),
        "habilitet_relations": attributes.get("relations"),
        "decision_ready": case_state in ("READY_FOR_DECISION", "DECIDED", "NOTIFIED", "APPEAL_PERIOD", "FINAL", "CLOSED"),
    }


def replay(kernel, expected_final_state: str, scenario: Scenario | None = None) -> dict[str, Any]:
    """Replay the same golden scenario. Expected: the same final Case state from
    the same event history (deterministic Kernel replay)."""
    from valo_reht import RealReht

    replayed = run_golden(reht=RealReht(), scenario=scenario or Scenario())
    return {
        "replayed_final_state": replayed.final_state,
        "matches_original": replayed.final_state == expected_final_state,
    }


def provenance(kernel) -> dict[str, Any]:
    events = kernel.events()
    return {
        "event_count": len(events),
        "case_events": [e.event_type.value for e in events if e.subject == "case-1"],
        "event_chain_integrity": _verify(kernel),
    }


def _verify(kernel) -> bool:
    try:
        kernel.verify_integrity()
        return True
    except Exception:
        return False
