from __future__ import annotations

from typing import Any

from .boundaries import KernelPort


class ValoKernelAdapter(KernelPort):
    """Reference adapter over `valo_kernel`. Imports valo_kernel lazily so the
    package has no hard dependency on it; workflow code never sees a mutable
    WorldState — every read returns immutable dumps."""

    def __init__(self, engine: Any, tenant_id: str) -> None:
        self.engine = engine
        self.tenant_id = tenant_id

    def read_state(self, tenant_id: str, entity_id: str) -> dict[str, Any]:
        entity = self.engine.state().entities.get(entity_id)
        if entity is None:
            raise KeyError(f"unknown entity {entity_id}")
        return entity.model_dump(mode="json")

    def query(self, tenant_id: str, query_type: str, params: dict[str, Any]) -> dict[str, Any]:
        from valo_kernel import Queries

        queries = Queries(self.engine.state())
        if query_type == "check_effect":
            process_ref = params.get("process_ref")
            phase = self.engine.state().clocks.get(f"{process_ref}:phase")
            return {"exists": phase == "EFFECT_VERIFIED"}
        if query_type == "who_may_act":
            return {"actors": queries.who_may_act(params.get("capability", ""))}
        if query_type == "resources_available":
            return {"resources": queries.resources_available()}
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
        from valo_kernel import build_execution_context
        from valo_kernel.contracts import CanonicalEvent, EventType

        transition = CanonicalEvent(
            event_id="wf-transition",
            event_type=EventType.RESOURCE_RESERVED
            if requested_transition.get("reservation")
            else EventType.EXTERNAL_EFFECT_OBSERVED,
            tenant_id=tenant_id,
            subject=target,
            actor=actor,
            source="workflow-isa",
            effective_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
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
        from valo_kernel import KernelInvariantViolation
        from valo_kernel.contracts import CanonicalEvent, EventType, Reservation
        from valo_kernel.contracts.common import utcnow

        event_type = event.get("event_type")
        tenant = event.get("tenant_id", self.tenant_id)
        subject = event.get("subject", "")
        payload = event.get("payload", {})
        transition = payload.get("requested_transition", {})

        if event_type == "RESOURCE_RESERVED":
            reservation_data = transition.get("reservation") or {
                "reservation_id": f"wf-{subject}-{event.get('actor')}",
                "resource_id": subject,
                "holder": event.get("actor"),
                "tenant_id": tenant,
            }
            canonical = CanonicalEvent(
                event_id=f"wf-{subject}-{event.get('actor')}",
                event_type=EventType.RESOURCE_RESERVED,
                tenant_id=tenant,
                subject=subject,
                actor=event.get("actor"),
                source="workflow-isa",
                effective_at=utcnow(),
                payload={"reservation": Reservation(**reservation_data)},
            )
        elif event_type == "EXECUTION_PHASE_UPDATED":
            canonical = CanonicalEvent(
                event_id=f"wf-phase-{subject}",
                event_type=EventType.EXECUTION_PHASE_UPDATED,
                tenant_id=tenant,
                subject=subject,
                actor=event.get("actor"),
                source="veritas",
                effective_at=utcnow(),
                payload={"process_ref": payload.get("process_ref"), "phase": payload.get("phase", "EXECUTION_OBSERVED")},
            )
        else:
            canonical = CanonicalEvent(
                event_id=f"wf-obs-{subject}-{event.get('actor')}",
                event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
                tenant_id=tenant,
                subject=subject,
                actor=event.get("actor"),
                source="veritas",
                effective_at=utcnow(),
                payload={"process_ref": payload.get("process_ref"), "observed": payload.get("observed", {})},
            )

        try:
            sealed = self.engine.append(canonical)
        except KernelInvariantViolation as exc:
            raise RuntimeError(f"kernel rejected event: {exc}") from exc
        return {"event_id": sealed.event_id}
