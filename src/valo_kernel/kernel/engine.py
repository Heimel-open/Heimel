from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import uuid4

from ..contracts.common import SCHEMA_VERSION, EntityType, RelationType, utcnow
from ..contracts.entity import Entity
from ..contracts.events import CanonicalEvent, EventType
from ..contracts.relationship import Relationship
from ..packs.base import Reducer, WorldPack
from ..storage.base import AppendOnlyStore
from ..storage.memory import MemoryStore
from ..world.history import replay_at, state_effective_at
from ..world.invariants import check_invariants
from ..world.state import WorldState
from .errors import (
    ConcurrencyError,
    FailClosedError,
    IdempotentReplay,
    IntegrityError,
)
from .integrity import (
    GENESIS_HASH,
    WorldSnapshot,
    make_snapshot,
    seal_event,
    verify_chain,
)
from .reducers import reduce


class KernelEngine:
    """The deterministic state owner. All mutation flows through `append`.

    Registered packs may extend domain types and deterministic reducers. They
    remain subordinate to every Kernel invariant and receive no execution or
    authorization path.
    """

    def __init__(
        self,
        tenant_id: str,
        storage: AppendOnlyStore | None = None,
        schema_version: str = SCHEMA_VERSION,
        packs: Iterable[WorldPack] | None = None,
    ) -> None:
        if not tenant_id:
            raise FailClosedError("tenant_id is required")
        if schema_version != SCHEMA_VERSION:
            raise FailClosedError(f"unknown schema version: {schema_version}")
        self._tenant_id = tenant_id
        self._schema_version = schema_version
        self._storage = storage or MemoryStore()
        self._pack_namespaces: set[str] = set()
        self._pack_entity_types: set[str] = set()
        self._pack_relationship_types: set[str] = set()
        self._pack_reducers: dict[str, Reducer] = {}
        for pack in packs or ():
            self._register_pack(pack)

    def _register_pack(self, pack: WorldPack) -> None:
        if pack.namespace in self._pack_namespaces:
            raise FailClosedError(f"duplicate pack namespace: {pack.namespace}")
        entity_overlap = self._pack_entity_types & set(pack.entity_types)
        relationship_overlap = (
            self._pack_relationship_types & set(pack.relationship_types)
        )
        event_overlap = set(self._pack_reducers) & set(pack.event_types)
        if entity_overlap or relationship_overlap or event_overlap:
            raise FailClosedError("pack type collision")
        try:
            pack.register(self._pack_reducers)
        except ValueError as exc:
            raise FailClosedError(str(exc)) from exc
        self._pack_namespaces.add(pack.namespace)
        self._pack_entity_types.update(pack.entity_types)
        self._pack_relationship_types.update(pack.relationship_types)

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def state(self) -> WorldState:
        stored = self._storage.state()
        if stored is None:
            return WorldState(tenant_id=self._tenant_id)
        return stored.model_copy(deep=True)

    def events(self) -> list[CanonicalEvent]:
        return self._storage.events()

    def sequence(self) -> int:
        return len(self.events())

    def _reduce_event(
        self,
        state: WorldState,
        event: CanonicalEvent,
    ) -> WorldState:
        return reduce(state, event, self._pack_reducers)

    def state_at(self, moment: datetime) -> WorldState:
        return replay_at(self.events(), moment, reduce_fn=self._reduce_event)

    def state_effective_at(self, moment: datetime) -> WorldState:
        return state_effective_at(
            self.events(),
            moment,
            reduce_fn=self._reduce_event,
        )

    def verify_integrity(self) -> None:
        verify_chain(self.events())

    def snapshot(self) -> WorldSnapshot:
        return make_snapshot(
            self.state(),
            snapshot_id=str(uuid4()),
            tenant=self._tenant_id,
            timestamp=utcnow().isoformat(),
            event_position=self.sequence(),
        )

    def _validate_pack_contract(self, event: CanonicalEvent) -> None:
        if (
            not isinstance(event.event_type, EventType)
            and event.event_type not in self._pack_reducers
        ):
            raise FailClosedError(
                f"unregistered pack event type: {event.event_type}"
            )

        if event.event_type == EventType.ENTITY_REGISTERED:
            try:
                entity = Entity.model_validate(event.payload.get("entity"))
            except (TypeError, ValueError) as exc:
                raise FailClosedError("invalid entity payload") from exc
            if (
                not isinstance(entity.entity_type, EntityType)
                and entity.entity_type not in self._pack_entity_types
            ):
                raise FailClosedError(
                    f"unregistered pack entity type: {entity.entity_type}"
                )

        if event.event_type == EventType.RELATIONSHIP_ESTABLISHED:
            try:
                relationship = Relationship.model_validate(
                    event.payload.get("relationship")
                )
            except (TypeError, ValueError) as exc:
                raise FailClosedError("invalid relationship payload") from exc
            if (
                not isinstance(relationship.relation_type, RelationType)
                and relationship.relation_type
                not in self._pack_relationship_types
            ):
                raise FailClosedError(
                    "unregistered pack relationship type: "
                    f"{relationship.relation_type}"
                )

    def append(
        self,
        event: CanonicalEvent,
        expected_version: int | None = None,
    ) -> CanonicalEvent:
        """Append an event and apply its deterministic core or pack reducer."""
        if event.tenant_id != self._tenant_id:
            raise FailClosedError(
                f"tenant mismatch: event {event.tenant_id} != kernel {self._tenant_id}"
            )

        self._validate_pack_contract(event)

        if event.idempotency_key is not None and self._storage.has_idempotency_key(
            event.idempotency_key
        ):
            raise IdempotentReplay(
                f"idempotency_key {event.idempotency_key} was already applied"
            )

        if expected_version is not None and self.sequence() != expected_version:
            raise ConcurrencyError(
                f"expected_version {expected_version} != current sequence {self.sequence()}"
            )

        stored = self._storage.state()
        current = (
            stored
            if stored is not None
            else WorldState(tenant_id=self._tenant_id)
        )
        next_state = reduce(current.clone(), event, self._pack_reducers)

        violations = check_invariants(next_state)
        if violations:
            raise FailClosedError(
                "world invariant violation: " + "; ".join(violations)
            )

        previous = self._storage.last_event()
        previous_hash = previous.event_hash if previous else GENESIS_HASH
        sealed = seal_event(
            event,
            sequence=self.sequence() + 1,
            previous_hash=previous_hash,
        )

        try:
            verify_chain(self.events() + [sealed])
        except IntegrityError as exc:
            raise FailClosedError(
                f"event chain integrity failure: {exc}"
            ) from exc

        self._storage.append_event(sealed, next_state)
        return sealed
