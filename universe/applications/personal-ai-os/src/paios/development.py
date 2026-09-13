"""relAIon developmental state.

Models Alpha-local operative memory, salience, consolidation, forgetting,
proficiency, self-directed learning and evidence-backed relational capability
realization. Canonical evidence lives outside this module and remains
immutable/replayable. Nothing here can grant authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple


class AbilityOrigin(str, Enum):
    BORROWED = "borrowed"
    DEVELOPED = "developed"
    HYBRID = "hybrid"


class MemoryState(str, Enum):
    TRANSIENT = "transient"
    CONSOLIDATED = "consolidated"
    DORMANT = "dormant"


@dataclass(frozen=True)
class Experience:
    experience_id: str
    event_ref: str
    consequence: str
    salience: float
    valid_at: float

    def __post_init__(self) -> None:
        if not self.event_ref:
            raise ValueError("experience requires canonical event provenance")
        if not 0.0 <= self.salience <= 1.0:
            raise ValueError("salience must be between 0 and 1")


@dataclass
class OperativeMemory:
    experience_id: str
    event_ref: str
    strength: float
    state: MemoryState = MemoryState.TRANSIENT
    recalls: int = 0

    @property
    def available(self) -> bool:
        return self.state is not MemoryState.DORMANT


@dataclass
class Ability:
    ability_id: str
    skill_ref: str
    origin: AbilityOrigin
    proficiency: float = 0.0
    provider_ref: Optional[str] = None
    learning_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.origin in {AbilityOrigin.BORROWED, AbilityOrigin.HYBRID} and not self.provider_ref:
            raise ValueError("borrowed/hybrid ability requires provider provenance")
        if not 0.0 <= self.proficiency <= 1.0:
            raise ValueError("proficiency must be between 0 and 1")


@dataclass
class RelationalCapability:
    """A capability whose realization depends on an evidence-backed relation kernel.

    This is deliberately separate from Ability. Ability models Alpha's developed
    proficiency around a skill/provider. RelationalCapability models a capability
    that may exist only when a particular composition is present.

    Registration does not claim the TADA-BIRTH-01 mechanism is universal. A
    capability may enter this registry only with explicit evidence provenance and
    an asserted minimal relation kernel supplied by a verifier/evaluator.
    """

    capability_id: str
    minimal_relation_kernel: Tuple[str, ...]
    evidence_ref: str
    realized_at: float
    detected_at: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.capability_id:
            raise ValueError("relational capability requires capability_id")
        if not self.minimal_relation_kernel:
            raise ValueError("relational capability requires a non-empty relation kernel")
        if len(set(self.minimal_relation_kernel)) != len(self.minimal_relation_kernel):
            raise ValueError("relation kernel must not contain duplicates")
        if not self.evidence_ref:
            raise ValueError("relational capability requires evidence provenance")
        if self.detected_at is not None and self.detected_at < self.realized_at:
            raise ValueError("detection cannot precede realization")

    def is_realized(self, active_relations: Set[str]) -> bool:
        return set(self.minimal_relation_kernel).issubset(active_relations)

    @property
    def detected(self) -> bool:
        return self.detected_at is not None


@dataclass
class SelfModel:
    beliefs: Dict[str, float] = field(default_factory=dict)
    learning_targets: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SleepReport:
    consolidated: Tuple[str, ...]
    weakened: Tuple[str, ...]
    forgotten: Tuple[str, ...]


class DevelopmentState:
    """Alpha-local mutable state derived from provenance-bearing experiences."""

    def __init__(self) -> None:
        self.memories: Dict[str, OperativeMemory] = {}
        self.abilities: Dict[str, Ability] = {}
        self.relational_capabilities: Dict[str, RelationalCapability] = {}
        self.active_relations: Set[str] = set()
        self.self_model = SelfModel()

    def experience(self, item: Experience) -> OperativeMemory:
        memory = self.memories.get(item.experience_id)
        if memory is None:
            memory = OperativeMemory(item.experience_id, item.event_ref, item.salience)
            self.memories[item.experience_id] = memory
        else:
            memory.strength = min(1.0, memory.strength + item.salience * 0.25)
        return memory

    def recall(self, experience_id: str) -> Optional[OperativeMemory]:
        memory = self.memories.get(experience_id)
        if memory is None or not memory.available:
            return None
        memory.recalls += 1
        memory.strength = min(1.0, memory.strength + 0.05)
        return memory

    def register_ability(self, ability: Ability) -> None:
        self.abilities[ability.ability_id] = ability

    def practice(self, ability_id: str, experience_ref: str, outcome: float) -> Ability:
        if not 0.0 <= outcome <= 1.0:
            raise ValueError("outcome must be between 0 and 1")
        ability = self.abilities[ability_id]
        ability.learning_refs.append(experience_ref)
        ability.proficiency = min(1.0, ability.proficiency + 0.1 * outcome)
        return ability

    def activate_relation(self, relation_ref: str) -> None:
        if not relation_ref:
            raise ValueError("relation_ref must be non-empty")
        self.active_relations.add(relation_ref)

    def deactivate_relation(self, relation_ref: str) -> None:
        self.active_relations.discard(relation_ref)

    def register_relational_capability(self, capability: RelationalCapability) -> None:
        self.relational_capabilities[capability.capability_id] = capability

    def capability_realized(self, capability_id: str) -> bool:
        capability = self.relational_capabilities[capability_id]
        return capability.is_realized(self.active_relations)

    def mark_capability_detected(self, capability_id: str, detected_at: float) -> RelationalCapability:
        capability = self.relational_capabilities[capability_id]
        if detected_at < capability.realized_at:
            raise ValueError("detection cannot precede realization")
        capability.detected_at = detected_at
        return capability

    def choose_learning_target(self, candidates: Mapping[str, float]) -> Optional[str]:
        if not candidates:
            return None
        target = max(candidates.items(), key=lambda item: (item[1], item[0]))[0]
        if target not in self.self_model.learning_targets:
            self.self_model.learning_targets.append(target)
        return target

    def sleep(self, *, consolidate_at: float = 0.65, forget_below: float = 0.15, decay: float = 0.08) -> SleepReport:
        consolidated: List[str] = []
        weakened: List[str] = []
        forgotten: List[str] = []
        for memory in self.memories.values():
            if memory.state is MemoryState.DORMANT:
                continue
            if memory.strength >= consolidate_at or memory.recalls >= 2:
                if memory.state is not MemoryState.CONSOLIDATED:
                    memory.state = MemoryState.CONSOLIDATED
                    consolidated.append(memory.experience_id)
                continue
            memory.strength = max(0.0, memory.strength - decay)
            weakened.append(memory.experience_id)
            if memory.strength < forget_below:
                memory.state = MemoryState.DORMANT
                forgotten.append(memory.experience_id)
        return SleepReport(tuple(consolidated), tuple(weakened), tuple(forgotten))

    def operative_context(self) -> Iterable[str]:
        return tuple(m.event_ref for m in self.memories.values() if m.available)
