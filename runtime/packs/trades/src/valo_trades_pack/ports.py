from __future__ import annotations

from typing import Any

from valo_kernel import KernelInvariantViolation, Queries, build_execution_context
from valo_kernel.contracts import CanonicalEvent, EventType, Reservation
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

# Deterministic WorkOrder transition contract (pack-owned domain semantics).
# Admissibility is checked against the CURRENT Kernel state before any
# transition event is applied: current state + requested transition + this
# contract -> deterministic allow/reject, then REHT, then execution.
WORK_ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "NEW": frozenset({"READY_TO_QUOTE"}),
    "READY_TO_QUOTE": frozenset({"SCHEDULED", "QUOTED"}),
    "QUOTED": frozenset({"ACCEPTED", "READY_TO_QUOTE"}),
    "ACCEPTED": frozenset({"SCHEDULED"}),
    "SCHEDULED": frozenset({"DISPATCHED"}),
    "DISPATCHED": frozenset({"IN_PROGRESS"}),
    "IN_PROGRESS": frozenset({"INVOICED"}),
    "INVOICED": frozenset({"PAID"}),
    "PAID": frozenset({"CLOSED"}),
    "CLOSED": frozenset(),
}


class TradeKernel(KernelPort):
    """Kernel-backed state for the pack. Business truth lives in the
    valo_kernel engine; every mutation is an append-only event. Workflows read
    immutable state and write only through events."""

    def __init__(self, engine: Any, tenant_id: str = "trades", shadow: bool = False) -> None:
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
        queries = Queries(self.engine.state())
        if query_type == "check_effect":
            phase = self.engine.state().clocks.get(f"{params.get('process_ref')}:phase")
            return {"exists": phase == "EFFECT_VERIFIED"}
        if query_type == "who_may_act":
            return {"actors": queries.who_may_act(params.get("capability", ""))}
        if query_type == "resources_available":
            available = [
                r.resource_id
                for r in self.engine.state().resources.values()
                if r.can_reserve() and r.resource_id in ("worker-a", "worker-b")
            ]
            return {"resources": sorted(available)}
        if query_type == "credential_valid":
            actor = params.get("actor")
            capability = params.get("capability", "DISPATCH")
            active = queries.who_may_act(capability)
            return {"valid": actor in active}
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
        transition = CanonicalEvent(
            event_id="trade-transition",
            event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
            tenant_id=tenant_id,
            subject=target,
            actor=actor,
            source="trades-pack",
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

        if event_type == "RESOURCE_RESERVED":
            reservation_data = transition.get("reservation") or {
                "reservation_id": f"wf-{subject}-{actor}",
                "resource_id": subject,
                "holder": actor,
                "tenant_id": tenant,
            }
            canonical = CanonicalEvent(
                event_id=f"wf-res-{subject}-{actor}",
                event_type=EventType.RESOURCE_RESERVED,
                tenant_id=tenant,
                subject=subject,
                actor=actor,
                source="workflow-isa",
                effective_at=utcnow(),
                payload={"reservation": Reservation(**reservation_data)},
            )
        elif event_type == "WORK_ORDER_TRANSITION":
            state = payload.get("requested_transition", {}).get("state") or payload.get("state")
            if state is not None:
                _admissible_work_order_transition(self.engine, subject, state, proposed_states=self.proposed_states if self.shadow else None)
            if state is None:
                canonical = CanonicalEvent(
                    event_id=f"wf-obs-{subject}-{actor}",
                    event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
                    tenant_id=tenant, subject=subject, actor=actor, source="veritas",
                    effective_at=utcnow(), payload={"process_ref": payload.get("process_ref"), "observed": payload.get("observed", {})},
                )
            else:
                canonical = CanonicalEvent(
                    event_id=f"wf-state-{subject}-{state}",
                    event_type=EventType.ENTITY_UPDATED,
                    tenant_id=tenant,
                    subject=subject,
                    actor=actor,
                    source="trades-pack",
                    effective_at=utcnow(),
                    payload={"entity_id": subject, "state": state},
                )
        elif event_type == "FACT_CONFIRMED":
            canonical = CanonicalEvent(
                event_id=f"wf-fact-{subject}-{payload.get('predicate')}",
                event_type=EventType.FACT_CONFIRMED,
                tenant_id=tenant,
                subject=subject,
                actor=actor,
                source="veritas",
                effective_at=utcnow(),
                payload={"fact_id": payload.get("fact_id")},
            )
        else:
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
        if self.shadow:
            self.proposed_events.append(event)
            return {"event_id": "shadow", "proposed": True}
        try:
            sealed = self.engine.append(canonical)
        except KernelInvariantViolation as exc:
            raise RuntimeError(f"kernel rejected event: {exc}") from exc
        return {"event_id": sealed.event_id}


class TradeGateway(GatewayPort):
    """Applies the external effect and returns a receipt. In shadow mode it
    records the proposed action and returns success WITHOUT applying any effect."""

    def __init__(self, shadow: bool = False) -> None:
        self.shadow = shadow
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


class TradeVeritas(VeritasPort):
    """Observes reality AFTER the gateway action. The observed reality is the
    external effect ledger: whether the payment actually landed, whether the
    invoice is within the quoted basis, whether dispatch is confirmed. An HTTP
    200 from the gateway is NOT the same as the observed effect."""

    def __init__(self, payment_lands: bool = True, invoice_drift: bool = False) -> None:
        self.observations: dict[str, dict[str, Any]] = {}
        self.payment_lands = payment_lands
        self.invoice_drift = invoice_drift

    def observe(self, execution: ExecutionResult, action_contract: dict[str, Any]) -> Observation:
        action_type = action_contract.get("action_type")
        shadow = execution.payload.get("shadow", False)
        if action_type == "PAY":
            observed = {"payment_observed": True if shadow else self.payment_lands}
        elif action_type == "DISPATCH":
            observed = {"dispatch_confirmed": True if shadow else execution.success}
        elif action_type == "INVOICE":
            observed = {"invoice_issued": True if shadow else (execution.success and not self.invoice_drift)}
        else:
            observed = {"executed": True if shadow else execution.success}
        self.observations[action_type] = observed
        return Observation(phase="EXECUTION_OBSERVED", observed=observed, receipt_ref=execution.receipt_ref)


class TradeBaro(BaroPort):
    def check(self, expected: dict[str, Any], observed: dict[str, Any]) -> BaroResult:
        diverged = False
        reason = None
        for key, value in expected.items():
            if observed.get(key) != value:
                diverged = True
                reason = f"expected {key}={value}, observed {key}={observed.get(key)}"
                break
        return BaroResult(diverged=diverged, reason=reason, expected=expected, observed=observed)

def _admissible_work_order_transition(engine: Any, work_order_id: str, requested: str, proposed_states: dict[str, str] | None = None) -> None:
    """Deterministic admissibility: the requested transition must be legal from
    the CURRENT Kernel state. In shadow mode the Kernel is read-only, so the
    proposed (simulated) state chain is used for the check instead. Golden-path
    ordering is not a security control."""
    if proposed_states is not None:
        current = proposed_states.get(work_order_id)
    else:
        entity = engine.state().entities.get(work_order_id)
        current = entity.state if entity is not None else None
    allowed = WORK_ORDER_TRANSITIONS.get(current or "NEW", frozenset())
    if requested not in allowed:
        raise RuntimeError(
            f"kernel rejected: illegal WorkOrder transition {current} -> {requested} "
            f"(allowed from {current or 'NEW'}: {sorted(allowed)})"
        )
    if proposed_states is not None:
        proposed_states[work_order_id] = requested
