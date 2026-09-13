from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..contracts.common import canonical_digest
from ..ports import BaroResult, DecisionResult, ExecutionResult, Observation


@dataclass
class DictKernel:
    """A pure-Python fake kernel implementing the KernelPort semantics. Holds
    authoritative state in plain dicts; every WRITE must go through append_event."""

    tenant: str = "tenant-a"
    entities: dict[str, dict[str, Any]] = field(default_factory=dict)
    facts: dict[str, dict[str, Any]] = field(default_factory=dict)
    resources: dict[str, dict[str, Any]] = field(default_factory=dict)
    reservations: dict[str, dict[str, Any]] = field(default_factory=dict)
    authorities: list[dict[str, Any]] = field(default_factory=list)
    identities: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    effects: dict[str, bool] = field(default_factory=dict)
    append_count: int = 0

    def register_entity(self, entity_id: str, state: str | None = None, **attrs: Any) -> None:
        self.entities[entity_id] = {"entity_id": entity_id, "state": state, **attrs}

    def register_resource(self, resource_id: str, capacity: int = 1, state: str = "AVAILABLE") -> None:
        self.resources[resource_id] = {"resource_id": resource_id, "capacity": capacity, "state": state, "holder": None, "allocated": 0}

    def register_identity(self, identity_id: str, entity_id: str, verified: bool = True) -> None:
        self.identities[identity_id] = {
            "identity_id": identity_id,
            "entity_id": entity_id,
            "verification_status": "VERIFIED" if verified else "UNVERIFIED",
            "revoked_at": None,
            "valid_until": None,
        }

    def grant_authority(self, principal: str, capability: str, scope: list[str] | None = None, active: bool = True) -> str:
        authority_id = f"auth-{principal}-{capability}"
        self.authorities.append(
            {"authority_id": authority_id, "principal": principal, "capability": capability, "scope": scope or [], "active": active}
        )
        return authority_id

    def revoke_authority(self, principal: str, capability: str) -> None:
        for authority in self.authorities:
            if authority["principal"] == principal and authority["capability"] == capability:
                authority["active"] = False

    def read_state(self, tenant_id: str, entity_id: str) -> dict[str, Any]:
        entity = self.entities.get(entity_id)
        if entity is None:
            raise KeyError(f"unknown entity {entity_id}")
        return dict(entity)

    def query(self, tenant_id: str, query_type: str, params: dict[str, Any]) -> dict[str, Any]:
        if query_type == "check_effect":
            return {"exists": self.effects.get(params.get("process_ref"), False)}
        if query_type == "who_may_act":
            capability = params.get("capability")
            return {"actors": sorted({a["principal"] for a in self.authorities if a["capability"] == capability and a["active"]})}
        if query_type == "resources_available":
            return {"resources": sorted(r["resource_id"] for r in self.resources.values() if r["state"] == "AVAILABLE")}
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
        identity = self.identities.get(identity_id or "", {})
        identity_ok = bool(identity) and identity["verification_status"] == "VERIFIED"
        if not identity_ok and identity_id:
            raise RuntimeError("no active verified execution identity")
        authority = [
            a for a in self.authorities if a["principal"] == actor and a["capability"] == capability and a["active"]
        ]
        return {
            "actor": actor,
            "identity": identity_id,
            "authority": authority,
            "capability": capability,
            "target": target,
            "current_state": dict(self.entities.get(target, {})),
            "requested_transition": requested_transition,
        }

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self.append_count += 1
        event_type = event.get("event_type")
        subject = event.get("subject", "")
        process_ref = event.get("payload", {}).get("process_ref")
        if event_type == "RESOURCE_RESERVED":
            resource = self.resources.get(subject)
            if resource is None:
                raise RuntimeError(f"kernel rejected: unknown resource {subject}")
            if resource["state"] != "AVAILABLE":
                raise RuntimeError(f"kernel rejected: resource {subject} already reserved")
            resource["state"] = "RESERVED"
            resource["holder"] = event.get("actor")
            if process_ref:
                self.effects[process_ref] = True
            reservation_id = event.get("payload", {}).get("requested_transition", {}).get("reservation", {}).get("reservation_id", f"r-{subject}")
            self.reservations[reservation_id] = {"resource_id": subject, "holder": event.get("actor")}
        if event_type == "RESERVATION_RELEASED":
            self.reservations.pop(subject, None)
        self.events.append(event)
        return {"event_id": f"k-event-{self.append_count}"}


class FakeReht:
    def __init__(self, allow_all: bool = True, deny_reason: str | None = None) -> None:
        self.allow_all = allow_all
        self.deny_reason = deny_reason
        self.authorize_calls: list[dict[str, Any]] = []

    def authorize(self, execution_context: dict[str, Any], action_contract: dict[str, Any]) -> DecisionResult:
        self.authorize_calls.append({"ctx": execution_context, "action": action_contract})
        authority = execution_context.get("authority") or []
        if not self.allow_all or not authority:
            return DecisionResult(decision="DENY", reason=self.deny_reason or "no authority")
        return DecisionResult(
            decision="ALLOW",
            clearance_ref="clearance-1",
            permit_ref="permit-1",
            execution_context_hash=canonical_digest(execution_context),
        )


class FakeGateway:
    def __init__(self, success: bool = True, seen_keys: set[str] | None = None, fail_after_execute: bool = False) -> None:
        self.success = success
        self.seen_keys: set[str] = seen_keys if seen_keys is not None else set()
        self.executions: list[dict[str, Any]] = []
        self.replayed: list[str] = []
        self.fail_after_execute = fail_after_execute

    def execute(self, binding: str, action_contract: dict[str, Any], idempotency_key: str) -> ExecutionResult:
        if idempotency_key:
            if idempotency_key in self.seen_keys:
                self.replayed.append(idempotency_key)
                return ExecutionResult(success=True, external_id="replayed", receipt_ref="receipt-replay")
            self.seen_keys.add(idempotency_key)
        self.executions.append({"binding": binding, "action": action_contract, "key": idempotency_key})
        if self.fail_after_execute:
            from ..runtime import NodeFailure

            raise NodeFailure("external response lost after effect may have occurred")
        return ExecutionResult(
            success=self.success,
            external_id=f"ext-{len(self.executions)}",
            receipt_ref=f"receipt-{len(self.executions)}",
            payload={"done": self.success},
        )

    def has_effect(self, idempotency_key: str) -> bool:
        return idempotency_key in self.seen_keys


class FakeVeritas:
    def __init__(self, observed: dict[str, Any] | None = None) -> None:
        self._observed = observed

    def observe(self, execution: ExecutionResult, action_contract: dict[str, Any]) -> Observation:
        observed = dict(self._observed or {})
        observed.setdefault("executed", execution.success)
        return Observation(phase="EXECUTION_OBSERVED", observed=observed, receipt_ref=execution.receipt_ref)


class FakeBaro:
    def __init__(self, force_diverged: bool = False) -> None:
        self.force_diverged = force_diverged

    def check(self, expected: dict[str, Any], observed: dict[str, Any]) -> BaroResult:
        if self.force_diverged:
            return BaroResult(diverged=True, reason="observed reality diverges from expected postcondition", expected=expected, observed=observed)
        diverged = expected != observed
        return BaroResult(diverged=diverged, reason=None if not diverged else "mismatch", expected=expected, observed=observed)


@dataclass
class FakePorts:
    kernel: DictKernel
    reht: FakeReht
    gateway: FakeGateway
    veritas: FakeVeritas
    baro: FakeBaro
