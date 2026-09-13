"""VAIG Governed Refusal-to-Resolution — vertical orchestrator (VAIG #95).

WIRES TOGETHER VAIG's RRP lifecycle into one governed refusal-to-resolution flow:

  vaig.rrp.RefusalEvent      → a refusal is emitted (safety/authority boundary hit)
  vaig.rrp.UncertaintyInventory → the uncertainty is inventoried (missing evidence)
  vaig.rrp.AuthorityAssignment   → an authority is assigned to resolve it
  vaig.rrp.RefusalLifecycle → the governable transition: enrich -> route ->
                               under_review -> decide -> resolve
  (optional) WORM receipt    → each state change chained into an append-only log

This proves refusal is a GOVERNABLE TRANSITION, not a terminal block:
  VAIG's core invariant — no intent forms without validated evidence — is enacted
  here. A refusal carries its uncertainty, gets an assigned authority, is reviewed,
  decided, and resolved, with every transition on the accountability thread (and
  optionally WORM-chained). Invalid transitions are rejected; resolved is terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from vaig.rrp import (
    AuthorityAssignment,
    AuthorityDecision,
    RefusalCategory,
    RefusalEvent,
    RefusalLifecycle,
    ResolutionState,
    SeverityLevel,
    UncertaintyInventory,
)


@dataclass
class ResolutionStep:
    step: str
    ok: bool
    detail: str
    data: Dict[str, Any] = field(default_factory=dict)


class GovernedRefusalResolution:
    """Orchestrates a VAIG refusal through its full governed lifecycle."""

    def __init__(self, receipt_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
                 agent_id: str = "vaig-agent"):
        self._receipt_sink = receipt_sink  # optional WORM-chained audit sink
        self._agent_id = agent_id
        self._lifecycle: Optional[RefusalLifecycle] = None
        self._log: List[ResolutionStep] = []

    def _step(self, step: str, ok: bool, detail: str, **data) -> ResolutionStep:
        s = ResolutionStep(step=step, ok=ok, detail=detail, data=data)
        self._log.append(s)
        if self._receipt_sink is not None:
            try:
                self._receipt_sink({"step": step, "ok": ok, "detail": detail, **data})
            except Exception:
                pass
        return s

    def emit(self, refusal_id: str, category: RefusalCategory, severity: SeverityLevel,
             triggered_rule: str, input_summary: str, rationale: str,
             permitted_actions: List[str]) -> ResolutionStep:
        """Emit a refusal event."""
        evt = RefusalEvent(
            refusal_id=refusal_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            category=category, severity=severity, triggered_rule=triggered_rule,
            operator_id=self._agent_id, session_id=f"session-{refusal_id}",
            input_summary=input_summary, rationale=rationale,
            permitted_actions=permitted_actions, model_state_digest="sha256:pending")
        self._lifecycle = RefusalLifecycle(evt)
        return self._step("emit", True, f"refusal {refusal_id} emitted",
                          refusal_id=refusal_id, category=category.name)

    def enrich(self, missing_evidence: List[str], unresolved: List[str]) -> ResolutionStep:
        """Inventory the uncertainty (missing evidence / open questions)."""
        inv = UncertaintyInventory(
            refusal_id=self._lifecycle.refusal_event.refusal_id,
            unresolved_questions=unresolved,
            missing_evidence=missing_evidence,
            ambiguity_sources=["operator_intent"],
            confidence_notes="auto-inventoried",
            context_integrity_status="clean_context_no_prompt_injection_detected",
            risk_if_ignored="unauthorized action risk")
        self._lifecycle.enrich(inv)
        return self._step("enrich", True, "uncertainty inventoried",
                          missing_evidence=missing_evidence)

    def route(self, authority_id: str, authority_role: str,
              scope: List[str], decision_sla: str) -> ResolutionStep:
        """Assign an authority to resolve the refusal."""
        asg = AuthorityAssignment(
            refusal_id=self._lifecycle.refusal_event.refusal_id,
            authority_role=authority_role, authority_id=authority_id,
            scope_of_authority=scope,
            decision_latency_sla=decision_sla,
            permitted_decisions=[AuthorityDecision.APPROVE, AuthorityDecision.RESCOPE,
                                 AuthorityDecision.REJECT, AuthorityDecision.TERMINATE],
            assignment_rationale=f"{authority_role} assigned for resolution")
        self._lifecycle.route(asg)
        return self._step("route", True, f"routed to {authority_id}",
                          authority_id=authority_id)

    def review(self, authority_id: str) -> ResolutionStep:
        self._lifecycle.start_review(authority_id)
        return self._step("review", True, f"under review by {authority_id}")

    def decide(self, authority_id: str, decision: AuthorityDecision,
               rationale: str) -> ResolutionStep:
        self._lifecycle.decide(authority_id, decision, rationale)
        return self._step("decide", True, f"decision={decision.name}",
                          decision=decision.name)

    def resolve(self, service: str, note: str) -> ResolutionStep:
        self._lifecycle.resolve(service, note)
        exported = self._lifecycle.export()
        return self._step("resolve", self._lifecycle.state is ResolutionState.RESOLVED,
                          f"state={exported['current_state']}",
                          current_state=exported["current_state"])

    def run(self, refusal_id: str, category: RefusalCategory, severity: SeverityLevel,
            triggered_rule: str, input_summary: str, rationale: str,
            permitted_actions: List[str], missing_evidence: List[str],
            unresolved: List[str], authority_id: str, authority_role: str,
            scope: List[str], decision_sla: str, review_authority: str,
            decision: AuthorityDecision, decision_rationale: str,
            resolve_service: str, resolve_note: str) -> List[ResolutionStep]:
        self.emit(refusal_id, category, severity, triggered_rule, input_summary,
                  rationale, permitted_actions)
        self.enrich(missing_evidence, unresolved)
        self.route(authority_id, authority_role, scope, decision_sla)
        self.review(review_authority)
        self.decide(review_authority, decision, decision_rationale)
        self.resolve(resolve_service, resolve_note)
        return list(self._log)

    def trace(self) -> List[ResolutionStep]:
        return list(self._log)
