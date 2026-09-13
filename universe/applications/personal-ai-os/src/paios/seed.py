"""relAIon developmental seed.

The seed carries identity and the capacity to form governed relational state. It
contains no role, character, preference, capability profile, autonomy level, or
solution. Those belong to lived developmental state.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Mapping


SEED_SCHEMA = "relaion-developmental-seed/v1"

SEED_INVARIANTS = (
    "identity_root_is_stable",
    "lineage_is_preserved",
    "evidence_precedes_canonical_change",
    "capability_is_not_authority",
    "external_models_harnesses_and_devices_are_replaceable",
    "no_direct_effect_path",
)


@dataclass(frozen=True)
class DevelopmentalSeed:
    """Minimal birth state. Identity is present; character is not prewritten."""

    seed_id: str
    identity_root: str
    lineage_root: str
    born_at: datetime
    governance_contract: str
    schema: str = SEED_SCHEMA

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        for name, value in (
            ("seed_id", self.seed_id),
            ("identity_root", self.identity_root),
            ("lineage_root", self.lineage_root),
            ("governance_contract", self.governance_contract),
        ):
            if not value.strip():
                errors.append(f"{name} is required")
        if self.born_at.tzinfo is None:
            errors.append("born_at must be timezone-aware")
        if self.schema != SEED_SCHEMA:
            errors.append(f"schema must be {SEED_SCHEMA}")
        return tuple(errors)

    def awaken(self) -> "DevelopmentalState":
        errors = self.validate()
        if errors:
            raise ValueError("; ".join(errors))
        return DevelopmentalState(seed=self)


@dataclass(frozen=True)
class RelationTrace:
    """One experienced relation, supported by provenance and consequence."""

    relation_id: str
    participants: tuple[str, ...]
    observed_at: datetime
    provenance_refs: tuple[str, ...]
    consequence_ref: str

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.relation_id.strip():
            errors.append("relation_id is required")
        if len(self.participants) < 2 or any(not item.strip() for item in self.participants):
            errors.append("at least two non-empty participants are required")
        if self.observed_at.tzinfo is None:
            errors.append("observed_at must be timezone-aware")
        if not self.provenance_refs:
            errors.append("provenance_refs are required")
        if not self.consequence_ref.strip():
            errors.append("consequence_ref is required")
        return tuple(errors)


@dataclass(frozen=True)
class DevelopmentalState:
    """Accumulated history around an unchanged seed identity."""

    seed: DevelopmentalSeed
    generation: int = 0
    relations: tuple[RelationTrace, ...] = ()
    active_relation_ids: frozenset[str] = frozenset()

    @property
    def identity_root(self) -> str:
        return self.seed.identity_root

    def learn(self, relation: RelationTrace) -> "DevelopmentalState":
        errors = relation.validate()
        if errors:
            raise ValueError("; ".join(errors))
        if any(item.relation_id == relation.relation_id for item in self.relations):
            raise ValueError(f"duplicate relation_id: {relation.relation_id}")
        return replace(
            self,
            generation=self.generation + 1,
            relations=(*self.relations, relation),
        )

    def activate(self, relation_ids: frozenset[str]) -> "DevelopmentalState":
        known = {item.relation_id for item in self.relations}
        unknown = relation_ids - known
        if unknown:
            raise ValueError("unknown relations: " + ", ".join(sorted(unknown)))
        return replace(
            self,
            generation=self.generation + 1,
            active_relation_ids=relation_ids,
        )

    def active_geometry(self) -> tuple[RelationTrace, ...]:
        return tuple(
            relation
            for relation in self.relations
            if relation.relation_id in self.active_relation_ids
        )

    def assert_identity_continuity(self, previous: "DevelopmentalState") -> None:
        if self.seed.seed_id != previous.seed.seed_id:
            raise ValueError("seed identity changed")
        if self.identity_root != previous.identity_root:
            raise ValueError("identity root changed")
        if self.seed.lineage_root != previous.seed.lineage_root:
            raise ValueError("lineage root changed")


def assert_seed_payload(payload: Mapping[str, object]) -> None:
    """Reject prewritten development disguised as birth state."""

    forbidden = {
        "role",
        "character",
        "preferences",
        "capabilities",
        "capability_profile",
        "autonomy_level",
        "maturity_level",
        "opportunity_rankings",
        "solutions",
    }
    present = sorted(key for key in forbidden if key in payload)
    if present:
        raise ValueError("seed contains developed state: " + ", ".join(present))
