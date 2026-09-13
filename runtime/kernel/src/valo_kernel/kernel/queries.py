from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..contracts.common import TruthStatus
from ..world.state import WorldState


class Queries:
    """Deterministic query model over WorldState. Every question is answered
    from state alone; no evaluation happens here."""

    def __init__(self, state: WorldState) -> None:
        self.state = state

    def who_is(self, entity_id: str) -> dict[str, Any] | None:
        entity = self.state.entities.get(entity_id)
        if entity is None:
            return None
        return {
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type.value,
            "state": entity.state,
            "attributes": entity.attributes,
            "valid_from": entity.valid_from,
            "valid_until": entity.valid_until,
        }

    def facts_about(self, subject: str) -> list[dict[str, Any]]:
        return [
            {
                "fact_id": f.fact_id,
                "predicate": f.predicate,
                "object": f.object,
                "truth_status": f.truth_status.value,
                "confidence": f.confidence,
                "model": f.model,
            }
            for f in self.state.facts.values()
            if f.subject == subject
        ]

    def evidence_supporting(self, subject: str) -> list[dict[str, Any]]:
        return [
            {
                "evidence_id": e.evidence_id,
                "type": e.type,
                "source": e.source,
                "status": e.status.value,
            }
            for e in self.state.evidence.values()
            if e.subject == subject
        ]

    def who_may_act(self, capability: str, moment: datetime | None = None) -> list[str]:
        active = []
        for authority in self.state.authorities.values():
            if authority.capability == capability and authority.is_active(moment):
                active.append(authority.principal)
        return sorted(set(active))

    def rights_applying(self, holder: str, moment: datetime | None = None) -> list[dict[str, Any]]:
        return [
            {"right_id": r.right_id, "right_type": r.right_type, "object": r.object}
            for r in self.state.rights.values()
            if r.holder == holder and r.is_active(moment)
        ]

    def obligations_active(self, party: str, moment: datetime | None = None) -> list[dict[str, Any]]:
        return [
            {
                "obligation_id": o.obligation_id,
                "action_required": o.action_required,
                "deadline": o.deadline,
                "status": o.status,
            }
            for o in self.state.obligations.values()
            if o.obligated_party == party and o.is_open(moment)
        ]

    def resources_available(self, moment: datetime | None = None) -> list[str]:
        return [
            r.resource_id
            for r in self.state.resources.values()
            if r.can_reserve()
        ]

    def conflicted(self) -> list[dict[str, Any]]:
        return [
            {"fact_id": f.fact_id, "subject": f.subject, "predicate": f.predicate, "object": f.object}
            for f in self.state.facts.values()
            if f.truth_status == TruthStatus.CONFLICTED
        ]

    def what_was_true_at(
        self,
        subject: str,
        moment: datetime,
        events: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        from ..world.history import replay_at

        state = replay_at(events or [], moment)
        return [
            {
                "fact_id": f.fact_id,
                "predicate": f.predicate,
                "object": f.object,
                "truth_status": f.truth_status.value,
            }
            for f in state.facts.values()
            if f.subject == subject
        ]

    def expiring_soon(self, horizon: timedelta, moment: datetime | None = None) -> dict[str, list[dict[str, Any]]]:
        moment = moment or datetime.now().astimezone()
        end = moment + horizon
        result: dict[str, list[dict[str, Any]]] = {"authorities": [], "rights": [], "reservations": []}
        for authority in self.state.authorities.values():
            until = authority.validity.valid_until
            if until is not None and moment <= until <= end:
                result["authorities"].append({"authority_id": authority.authority_id, "valid_until": until})
        for right in self.state.rights.values():
            until = right.validity.valid_until
            if moment <= until <= end:
                result["rights"].append({"right_id": right.right_id, "valid_until": until})
        for reservation in self.state.reservations.values():
            until = reservation.valid_until
            if until is not None and reservation.is_active(moment) and moment <= until <= end:
                result["reservations"].append({"reservation_id": reservation.reservation_id, "valid_until": until})
        return result
