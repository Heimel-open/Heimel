from valo_kernel.contracts import Entity, EntityType, Fact, Provenance, TruthStatus
from valo_kernel.world import WorldState, check_invariants


def provenance(source_id: str) -> Provenance:
    return Provenance(
        source_type="system",
        source_id=source_id,
        source_system="semantic-identity-test",
    )


def entity(entity_id: str) -> Entity:
    return Entity(
        entity_id=entity_id,
        entity_type=EntityType.PERSON,
        tenant_id="tenant-a",
        provenance=provenance(entity_id),
    )


def test_identity_equivalence_requires_evidence() -> None:
    state = WorldState(tenant_id="tenant-a")
    state.entities["a"] = entity("a")
    state.entities["b"] = entity("b")
    state.facts["f1"] = Fact(
        fact_id="f1",
        subject="a",
        predicate="identity_equivalent",
        object="b",
        tenant_id="tenant-a",
        truth_status=TruthStatus.CONFIRMED,
        provenance=provenance("f1"),
    )

    violations = check_invariants(state)

    assert "identity-equivalence fact f1 has no evidence" in violations


def test_identity_equivalence_requires_known_entities() -> None:
    state = WorldState(tenant_id="tenant-a")
    state.entities["a"] = entity("a")
    state.facts["f2"] = Fact(
        fact_id="f2",
        subject="a",
        predicate="same_as",
        object="missing",
        tenant_id="tenant-a",
        truth_status=TruthStatus.CONFIRMED,
        evidence_refs=["evidence-1"],
        provenance=provenance("f2"),
    )

    violations = check_invariants(state)

    assert "identity-equivalence fact f2 has unknown object entity" in violations


def test_non_identity_similarity_is_not_promoted_to_identity() -> None:
    state = WorldState(tenant_id="tenant-a")
    state.facts["f3"] = Fact(
        fact_id="f3",
        subject="representation-a",
        predicate="pattern_equivalent",
        object="representation-b",
        tenant_id="tenant-a",
        truth_status=TruthStatus.CONFIRMED,
        provenance=provenance("f3"),
    )

    violations = check_invariants(state)

    assert not any("identity-equivalence fact f3" in violation for violation in violations)
