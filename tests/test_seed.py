from datetime import datetime, timezone

import pytest

from paios.seed import (
    DevelopmentalSeed,
    RelationTrace,
    SEED_INVARIANTS,
    assert_seed_payload,
)


def make_seed() -> DevelopmentalSeed:
    return DevelopmentalSeed(
        seed_id="seed-1",
        identity_root="identity-root-1",
        lineage_root="lineage-root-1",
        born_at=datetime.now(timezone.utc),
        governance_contract="reht://contract/1",
    )


def test_seed_is_identity_without_preloaded_character_or_capability() -> None:
    state = make_seed().awaken()
    assert state.generation == 0
    assert state.relations == ()
    assert state.active_relation_ids == frozenset()
    assert "capability_is_not_authority" in SEED_INVARIANTS


@pytest.mark.parametrize(
    "field",
    ["role", "character", "preferences", "capabilities", "autonomy_level"],
)
def test_developed_state_cannot_be_smuggled_into_seed(field: str) -> None:
    with pytest.raises(ValueError, match="developed state"):
        assert_seed_payload({field: "prewritten"})


def test_history_changes_geometry_without_changing_identity() -> None:
    before = make_seed().awaken()
    relation = RelationTrace(
        relation_id="r1",
        participants=("person", "world"),
        observed_at=datetime.now(timezone.utc),
        provenance_refs=("observation:1",),
        consequence_ref="effect:1",
    )
    learned = before.learn(relation)
    active = learned.activate(frozenset({"r1"}))

    active.assert_identity_continuity(before)
    assert active.identity_root == before.identity_root
    assert active.generation == 2
    assert active.active_geometry() == (relation,)


def test_unknown_relation_cannot_be_activated() -> None:
    with pytest.raises(ValueError, match="unknown relations"):
        make_seed().awaken().activate(frozenset({"missing"}))
