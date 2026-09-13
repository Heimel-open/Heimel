from __future__ import annotations

from typing import Any

from valo_kernel import KernelInvariantViolation, build_execution_context
from valo_kernel.contracts import CanonicalEvent, EventType
from valo_kernel.contracts.common import utcnow
from valo_workflow_isa.ports import (
    BaroPort,
    BaroResult,
    ExecutionResult,
    GatewayPort,
    KernelPort,
    Observation,
    VeritasPort,
)

# Deterministic Case transition contract (pack-owned domain semantics).
# Admissibility is checked against the CURRENT Kernel state before any
# transition event is applied: current state + requested + contract ->
# deterministic allow/reject, then REHT, then execution.
CASE_TRANSITIONS: dict[str, frozenset[str]] = {
    "RECEIVED": frozenset({"REGISTERED", "CANCELLED", "EXCEPTION"}),
    "REGISTERED": frozenset({"AWAITING_INFORMATION", "READY_FOR_REVIEW", "EXCEPTION"}),
    "AWAITING_INFORMATION": frozenset({"READY_FOR_REVIEW", "EXCEPTION"}),
    "READY_FOR_REVIEW": frozenset({"UNDER_REVIEW", "EXCEPTION"}),
    "UNDER_REVIEW": frozenset({"READY_FOR_DECISION", "AWAITING_INFORMATION", "EXCEPTION"}),
    "READY_FOR_DECISION": frozenset({"DECIDED", "EXCEPTION"}),
    "DECIDED": frozenset({"NOTIFIED", "EXCEPTION"}),
    "NOTIFIED": frozenset({"APPEAL_PERIOD", "APPEALED", "EXCEPTION"}),
    "APPEAL_PERIOD": frozenset({"FINAL", "APPEALED", "EXCEPTION"}),
    "APPEALED": frozenset({"FINAL", "EXCEPTION"}),
    "FINAL": frozenset({"CLOSED", "EXCEPTION"}),
    "CANCELLED": frozenset(),
    "EXCEPTION": frozenset({"READY_FOR_REVIEW", "READY_FOR_DECISION"}),
}


class PublicKernel(KernelPort):
    """Kernel-backed case state. Business truth lives in the valo_kernel
    engine; every mutation is an append-only event. Legal basis and competence
    are Kernel authorities; REHT authorizes against the fresh execution
    context."""

    def __init__(self, engine: Any, tenant_id: str = "public", shadow: bool = False) -> None:
        self.engine = engine
        self.tenant_id = tenant_id
        self.shadow = shadow
        self.proposed_events: list[dict[str, Any]] = []
        self.proposed_states: dict[str, str] = {}

    def read_state(self, tenant_id: str, entity_id: str) -> dict[str, Any]:
        entity = self.engine.state().entities.get(entity_id)
        if entity is None:
            raise KeyError(f"unknown entity {entity_id}")
        return entity.model_dump(mode="json")

    def query(self, tenant_id: str, query_type: str, params: dict[str, Any]) -> dict[str, Any]:
        if query_type == "check_effect":
            phase = self.engine.state().clocks.get(f"{params.get('process_ref')}:phase")
            return {"exists": phase == "EFFECT_VERIFIED"}
        if query_type == "who_may_act":
            from valo_kernel import Queries

            return {"actors": Queries(self.engine.state()).who_may_act(params.get("capability", ""))}
        if query_type == "case_state":
            entity = self.engine.state().entities.get(params.get("case_id", "case-1"))
            return {"state": entity.state if entity else None}
        return {"params": params}

    def execution_context(
        self,
        tenant_id: str,
        actor: str,
        capability: str,
        target: str,
        requested_transition: dict[str, Any],
        identity_id: str | None = None,
        purpose_id: str | None = None,
    ) -> dict[str, Any]:
        # PRE-EXECUTION domain-invariant boundary. The deterministic Public
        # transition-admissibility check runs for EVERY requested Case state
        # BEFORE REHT/Gateway: no external Case transition (REGISTERED,
        # READY_FOR_REVIEW, UNDER_REVIEW, READY_FOR_DECISION, NOTIFIED,
        # APPEAL_PERIOD, FINAL, CLOSED, ...) can reach the Gateway unless the
        # transition is admissible from the CURRENT Kernel state. The
        # rights-impacting invariant is re-derived for DECIDED. No real-world
        # effect can happen for a transition that the invariant later rejects.
        # Kernel still does not authorize; REHT is still the only authorization
        # boundary. The same checks stay in append_event as defense-in-depth.
        requested_state = requested_transition.get("state")
        if requested_state is not None:
            _admissible_case_transition(
                self.engine, target, requested_state, self.proposed_states if self.shadow else None
            )
        if requested_state == "DECIDED":
            _assert_decidable_from_raw_facts(self.engine, target, actor)
        transition = CanonicalEvent(
            event_id="public-transition",
            event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
            tenant_id=tenant_id,
            subject=target,
            actor=actor,
            source="public-pack",
            effective_at=utcnow(),
            payload=requested_transition,
        )
        return build_execution_context(
            self.engine.state(),
            actor=actor,
            capability=capability,
            target=target,
            requested_transition=transition,
            identity_id=identity_id,
            purpose_id=purpose_id,
        )

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_type = event.get("event_type")
        subject = event.get("subject", "")
        payload = event.get("payload", {})
        actor = event.get("actor")
        transition = payload.get("requested_transition", {})
        tenant = event.get("tenant_id", self.tenant_id)

        if event_type == "CASE_TRANSITION":
            state = transition.get("state") or payload.get("state")
            if state is not None:
                _admissible_case_transition(
                    self.engine, subject, state, self.proposed_states if self.shadow else None, actor=actor
                )
            if self.shadow:
                self.proposed_events.append(event)
                if state is not None:
                    self.proposed_states[subject] = state
                return {"event_id": "shadow", "proposed": True}
            canonical = CanonicalEvent(
                event_id=f"wf-case-{subject}-{state}",
                event_type=EventType.ENTITY_UPDATED,
                tenant_id=tenant,
                subject=subject,
                actor=actor,
                source="public-pack",
                effective_at=utcnow(),
                payload={"entity_id": subject, "state": state},
            )
        else:
            if self.shadow:
                self.proposed_events.append(event)
                return {"event_id": "shadow", "proposed": True}
            canonical = CanonicalEvent(
                event_id=f"wf-obs-{subject}-{actor}",
                event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
                tenant_id=tenant,
                subject=subject,
                actor=actor,
                source="veritas",
                effective_at=utcnow(),
                payload={"process_ref": payload.get("process_ref"), "observed": payload.get("observed", {})},
            )
        try:
            sealed = self.engine.append(canonical)
        except KernelInvariantViolation as exc:
            raise RuntimeError(f"kernel rejected event: {exc}") from exc
        return {"event_id": sealed.event_id}


def _admissible_case_transition(engine: Any, case_id: str, requested: str, proposed_states: dict[str, str] | None = None, actor: str = "system-1") -> None:
    """Deterministic admissibility: the requested transition must be legal from
    the CURRENT Kernel state. Golden-path ordering is not a security control.
    Validates only — never mutates shadow proposed states."""
    if proposed_states is not None:
        current = proposed_states.get(case_id)
    else:
        entity = engine.state().entities.get(case_id)
        current = entity.state if entity is not None else None
    allowed = CASE_TRANSITIONS.get(current or "RECEIVED", frozenset())
    if requested not in allowed:
        raise RuntimeError(
            f"kernel rejected: illegal Case transition {current} -> {requested} "
            f"(allowed from {current or 'RECEIVED'}: {sorted(allowed)})"
        )
    if requested == "DECIDED" and proposed_states is None:
        # Rights-impacting invariant, derived deterministically from RAW Kernel
        # state — no pre-seeded adjudication flags. The decision boundary
        # re-derives every condition from the raw facts/authorities that the
        # control Functions flow into the DecisionContext.
        _assert_decidable_from_raw_facts(engine, case_id, actor)


def _assert_decidable_from_raw_facts(engine: Any, case_id: str, actor: str = "system-1") -> None:
    """Derive decidable-ness from the raw kernel state: a conflicted critical
    fact, a disqualifying relationship, stale/mis-purposed evidence, an
    out-of-scope representation, or an inactive/mis-scoped legal basis all
    block the decision. Nothing here is a seeded 'ok' flag."""
    from .world import DISQUALIFYING_RELATIONS

    entity = engine.state().entities.get(case_id)
    attributes = (entity.attributes or {}) if entity else {}
    state = engine.state()
    # fail closed: a case without an explicit service cannot be decided, even
    # if a legal basis happens to cover PUBLIC_SERVICE_A
    service = attributes.get("service")
    if not service:
        raise RuntimeError(f"kernel rejected: cannot decide — case {case_id} has no explicit service")

    # 1. legal basis must be an ACTIVE authority (separate from competence),
    #    bound to THIS decision maker, THIS case scope and THIS service. It is
    #    not enough that a legal basis exists — the EXACT action must have a
    #    RELEVANT legal basis. Fail closed: an authority without an explicit
    #    constraints.service covers nothing.
    legal_active = any(
        a.capability == "LEGAL_BASIS"
        and a.principal == actor
        and a.is_active()
        and (not a.scope or "*" in a.scope or case_id in a.scope)
        and a.constraints.get("service") == service
        for a in state.authorities.values()
    )
    if not legal_active:
        raise RuntimeError(
            f"kernel rejected: cannot decide — no ACTIVE legal basis bound to "
            f"{actor} for case {case_id} (service {service})"
        )

    # 2. conflicted critical fact (eligibility = UNKNOWN, never force-confirmed)
    if attributes.get("residency_fact") == "CONFLICTED":
        raise RuntimeError("kernel rejected: cannot decide a case whose critical fact is conflicted")

    # 3. disqualifying relationship (habilitet) against the ACTUAL decision
    #    maker and the ACTUAL applicant of THIS case
    relations = attributes.get("relations") or []
    applicant_id = attributes.get("applicant_id")
    disqualifying = [
        rel for rel in relations
        if rel.get("kind") in DISQUALIFYING_RELATIONS
        and rel.get("subject") == actor and rel.get("object") == applicant_id
    ]
    if disqualifying:
        raise RuntimeError(f"kernel rejected: cannot decide — decision maker {actor} is disqualified (habilitet {disqualifying[0].get('kind')})")

    # 4. evidence must be admitted and carry a permitted purpose
    evidence = attributes.get("evidence") or []
    for item in evidence:
        if item.get("status") != "ADMITTED":
            raise RuntimeError(f"kernel rejected: cannot decide — evidence not admitted ({item.get('status')}) — revalidate")
        if item.get("purpose") != service:
            raise RuntimeError(
                f"kernel rejected: cannot decide — evidence purpose {item.get('purpose')} not permitted for {service}"
            )

    # 5. representation must cover the case when one is claimed
    representation = attributes.get("representation")
    if representation is not None and representation.get("scope") != "FULL":
        raise RuntimeError("kernel rejected: cannot decide — representation does not cover this case")

    # 6. applicant must be eligible from the RAW facts (age + residency)
    age = attributes.get("age")
    if age is None or age < 18:
        raise RuntimeError("kernel rejected: cannot decide — applicant is not eligible (age)")


class PublicGateway(GatewayPort):
    """Applies the external effect (decision issued, notification sent, appeal
    deadline set) and returns a receipt. Shadow mode records proposals without
    applying them."""

    def __init__(self, shadow: bool = False, notification_delivered: bool = True) -> None:
        self.shadow = shadow
        self.notification_delivered = notification_delivered
        self.executions: list[dict[str, Any]] = []
        self.proposed: list[dict[str, Any]] = []
        self.keys: set[str] = set()

    def execute(self, binding: str, action_contract: dict[str, Any], idempotency_key: str) -> ExecutionResult:
        if idempotency_key and idempotency_key in self.keys:
            return ExecutionResult(success=True, external_id="replayed", receipt_ref="receipt-replay")
        self.keys.add(idempotency_key)
        record = {"binding": binding, "action_type": action_contract.get("action_type"), "target": action_contract.get("target")}
        if self.shadow:
            self.proposed.append(record)
            return ExecutionResult(success=True, external_id="shadow", receipt_ref="receipt-shadow", payload={"shadow": True})
        self.executions.append(record)
        return ExecutionResult(success=True, external_id=f"ext-{len(self.executions)}", receipt_ref=f"receipt-{len(self.executions)}", payload={"executed": True})

    def has_effect(self, idempotency_key: str) -> bool:
        return idempotency_key in self.keys


class PublicVeritas(VeritasPort):
    """Observes reality AFTER the gateway action. Delivery is distinct from
    send: an HTTP 200 from the notifier is not a delivered decision."""

    def __init__(self, notification_delivered: bool = True) -> None:
        self.notification_delivered = notification_delivered

    def observe(self, execution: ExecutionResult, action_contract: dict[str, Any]) -> Observation:
        action_type = action_contract.get("action_type")
        shadow = execution.payload.get("shadow", False)
        if action_type == "NOTIFY":
            observed = {"delivered": True if shadow else (execution.success and self.notification_delivered)}
        elif action_type == "ISSUE_DECISION":
            observed = {"decision_issued": True if shadow else execution.success}
        elif action_type == "CREATE_APPEAL_DEADLINE":
            observed = {"deadline_set": True if shadow else execution.success}
        else:
            observed = {"executed": True if shadow else execution.success}
        return Observation(phase="EXECUTION_OBSERVED", observed=observed, receipt_ref=execution.receipt_ref)


class PublicBaro(BaroPort):
    def check(self, expected: dict[str, Any], observed: dict[str, Any]) -> BaroResult:
        diverged = False
        reason = None
        for key, value in expected.items():
            if observed.get(key) != value:
                diverged = True
                reason = f"expected {key}={value}, observed {key}={observed.get(key)}"
                break
        return BaroResult(diverged=diverged, reason=reason, expected=expected, observed=observed)
