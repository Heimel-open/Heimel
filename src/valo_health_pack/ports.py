# ruff: noqa: I001
"""Health Pack runtime ports over the canonical VALO boundary.

HealthKernel owns deterministic domain-state admissibility and Kernel event
projection. It never makes an authorization decision. REHT remains the only
execution-authorization boundary. The default Gateway/Veritas pair is a local
fixture; production/pilot runtimes inject provider-neutral external adapters.
"""

from __future__ import annotations

from hashlib import sha256
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


HEALTH_TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"NOTE_APPROVED"}),
    "NOTE_APPROVED": frozenset({"NOTE_COMMITTED"}),
    "NOTE_COMMITTED": frozenset(),
    "AVAILABLE": frozenset({"BOOKED"}),
    "BOOKED": frozenset({"RESCHEDULED", "CANCELLED"}),
    "RESCHEDULED": frozenset({"RESCHEDULED", "CANCELLED"}),
    "CANCELLED": frozenset(),
    "NEW": frozenset({"CAPTURED"}),
    "CAPTURED": frozenset({"ROUTED"}),
    "ROUTED": frozenset({"CLINICAL_REVIEW_REQUESTED"}),
    "CLINICAL_REVIEW_REQUESTED": frozenset({"CLINICIAN_DECISION_RECORDED"}),
    "CLINICIAN_DECISION_RECORDED": frozenset({"PATIENT_NOTIFIED"}),
    "PATIENT_NOTIFIED": frozenset(),
}

HEALTH_EFFECTS: dict[str, str] = {
    "APPROVE_NOTE_DRAFT": "review_recorded",
    "COMMIT_CLINICAL_NOTE": "clinical_record_committed",
    "BOOK_APPOINTMENT": "appointment_booked",
    "RESCHEDULE_APPOINTMENT": "appointment_rescheduled",
    "CANCEL_APPOINTMENT": "appointment_cancelled",
    "CAPTURE_RENEWAL_REQUEST": "renewal_request_captured",
    "ROUTE_RENEWAL_REQUEST": "renewal_request_routed",
    "REQUEST_CLINICAL_REVIEW": "clinical_review_requested",
    "RECORD_CLINICIAN_DECISION": "clinician_decision_recorded",
    "NOTIFY_PATIENT": "patient_notified",
}


class HealthKernel(KernelPort):
    """Kernel-backed health state with fail-closed transition admissibility."""

    def __init__(self, engine: Any, tenant_id: str = "health", shadow: bool = False) -> None:
        self.engine = engine
        self.tenant_id = tenant_id
        self.shadow = shadow
        self.proposed_events: list[dict[str, Any]] = []
        self.proposed_states: dict[str, str] = {}

    def read_state(self, tenant_id: str, entity_id: str) -> dict[str, Any]:
        entity = self.engine.state().entities.get(entity_id)
        if entity is None:
            raise KeyError(f"unknown health entity {entity_id}")
        return entity.model_dump(mode="json")

    def query(self, tenant_id: str, query_type: str, params: dict[str, Any]) -> dict[str, Any]:
        if query_type == "entity_state":
            entity = self.engine.state().entities.get(params.get("entity_id", ""))
            return {"state": entity.state if entity else None}
        if query_type == "check_effect":
            phase = self.engine.state().clocks.get(f"{params.get('process_ref')}:phase")
            return {"exists": phase == "EFFECT_VERIFIED"}
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
        requested_state = requested_transition.get("state")
        if requested_state is not None:
            self._assert_transition(target, requested_state)

        transition = CanonicalEvent(
            event_id="health-execution-context-transition",
            event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
            tenant_id=tenant_id,
            subject=target,
            actor=actor,
            source="health-pack",
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
        actor = event.get("actor")
        tenant = event.get("tenant_id", self.tenant_id)
        payload = event.get("payload", {})
        requested_transition = payload.get("requested_transition", {})
        requested_state = requested_transition.get("state")

        if event_type == "HEALTH_TRANSITION" and requested_state is not None:
            self._assert_transition(subject, requested_state)
            if self.shadow:
                self.proposed_events.append(event)
                self.proposed_states[subject] = requested_state
                return {"event_id": "shadow", "proposed": True}
            process_ref = str(payload.get("process_ref") or "health")
            suffix = sha256(process_ref.encode("utf-8")).hexdigest()[:12]
            canonical = CanonicalEvent(
                event_id=f"health-transition-{subject}-{requested_state}-{suffix}",
                event_type=EventType.ENTITY_UPDATED,
                tenant_id=tenant,
                subject=subject,
                actor=actor,
                source="veritas",
                effective_at=utcnow(),
                payload={"entity_id": subject, "state": requested_state},
            )
        else:
            if self.shadow:
                self.proposed_events.append(event)
                return {"event_id": "shadow", "proposed": True}
            process_ref = str(payload.get("process_ref") or "health")
            suffix = sha256(process_ref.encode("utf-8")).hexdigest()[:12]
            canonical = CanonicalEvent(
                event_id=f"health-observation-{subject}-{suffix}",
                event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
                tenant_id=tenant,
                subject=subject,
                actor=actor,
                source="veritas",
                effective_at=utcnow(),
                payload={
                    "process_ref": payload.get("process_ref"),
                    "observed": payload.get("observed", {}),
                },
            )

        try:
            sealed = self.engine.append(canonical)
        except KernelInvariantViolation as exc:
            raise RuntimeError(f"kernel rejected health event: {exc}") from exc
        return {"event_id": sealed.event_id}

    def _assert_transition(self, target: str, requested: str) -> None:
        if self.shadow and target in self.proposed_states:
            current = self.proposed_states[target]
        else:
            entity = self.engine.state().entities.get(target)
            if entity is None:
                raise RuntimeError(f"kernel rejected: unknown health target {target}")
            current = entity.state
        allowed = HEALTH_TRANSITIONS.get(current or "", frozenset())
        if requested not in allowed:
            raise RuntimeError(
                f"kernel rejected: illegal health transition {target}: {current} -> {requested}; "
                f"allowed={sorted(allowed)}"
            )


class HealthGateway(GatewayPort):
    """Deterministic local execution fixture. No authority logic."""

    def __init__(self, shadow: bool = False) -> None:
        self.shadow = shadow
        self.executions: list[dict[str, Any]] = []
        self.proposed: list[dict[str, Any]] = []
        self.keys: set[str] = set()

    def execute(
        self,
        binding: str,
        action_contract: dict[str, Any],
        idempotency_key: str,
    ) -> ExecutionResult:
        if idempotency_key and idempotency_key in self.keys:
            return ExecutionResult(
                success=True,
                external_id="replayed",
                receipt_ref="health-receipt-replay",
                payload={"replayed": True},
            )
        if idempotency_key:
            self.keys.add(idempotency_key)
        record = {
            "binding": binding,
            "action_type": action_contract.get("action_type"),
            "target": action_contract.get("target"),
        }
        if self.shadow:
            self.proposed.append(record)
            return ExecutionResult(
                success=True,
                external_id="shadow",
                receipt_ref="health-receipt-shadow",
                payload={"shadow": True},
            )
        self.executions.append(record)
        external_id = f"health-ext-{len(self.executions)}"
        return ExecutionResult(
            success=True,
            external_id=external_id,
            receipt_ref=f"health-receipt-{len(self.executions)}",
            payload={"external_record_id": external_id},
        )

    def has_effect(self, idempotency_key: str) -> bool:
        return idempotency_key in self.keys


class HealthVeritas(VeritasPort):
    """Local deterministic observation fixture for pack runtime tests."""

    def observe(self, execution: ExecutionResult, action_contract: dict[str, Any]) -> Observation:
        action_type = str(action_contract.get("action_type") or "")
        effect_key = HEALTH_EFFECTS.get(action_type)
        if effect_key is None or not execution.success:
            observed = {"outcome": "NOT_VERIFIED", "verified": False}
        else:
            observed = {
                effect_key: True,
                "outcome": "VERIFIED",
                "verified": True,
            }
        return Observation(
            phase="EXECUTION_OBSERVED",
            observed=observed,
            receipt_ref=execution.receipt_ref,
        )


class HealthBaro(BaroPort):
    """Deterministic expected-vs-observed comparison, never a decision engine."""

    def check(self, expected: dict[str, Any], observed: dict[str, Any]) -> BaroResult:
        for key, value in expected.items():
            if observed.get(key) != value:
                return BaroResult(
                    diverged=True,
                    reason=f"expected {key}={value}, observed {key}={observed.get(key)}",
                    expected=expected,
                    observed=observed,
                )
        return BaroResult(
            diverged=False,
            reason=None,
            expected=expected,
            observed=observed,
        )
