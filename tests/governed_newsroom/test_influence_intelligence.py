from datetime import datetime, timezone

from valo_platform.governed_newsroom.influence import (
    EvidenceLevel,
    InfluenceEdgeType,
    InfluenceGraphPackage,
    InfluenceNode,
    InfluenceNodeType,
    InfluenceObservation,
    ProvenanceRef,
)


def _provenance() -> ProvenanceRef:
    return ProvenanceRef(
        source_uri="https://example.test/programme",
        captured_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        content_digest="sha256:abc",
        adapter_id="speider.event-programme.v1",
    )


def test_documentary_relationship_can_enter_verified_finding_set():
    observation = InfluenceObservation(
        observation_id="obs-1",
        subject_id="person-1",
        predicate=InfluenceEdgeType.SPEAKS_AT,
        object_id="event-1",
        observed_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        valid_from=None,
        valid_until=None,
        provenance=(_provenance(),),
        evidence_level=EvidenceLevel.DOCUMENTARY,
    )

    assert observation.is_publishable_finding() is True


def test_speculation_never_enters_publishable_set():
    observation = InfluenceObservation(
        observation_id="obs-2",
        subject_id="organisation-1",
        predicate=InfluenceEdgeType.CONTROLS_PUBLICATION,
        object_id="publication-1",
        observed_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        valid_from=None,
        valid_until=None,
        provenance=(_provenance(),),
        evidence_level=EvidenceLevel.SPECULATION,
        limitations=("Co-attendance is not evidence of control.",),
        BARO_hypothesis=True,
    )
    package = InfluenceGraphPackage(
        package_id="pkg-1",
        nodes=(
            InfluenceNode("organisation-1", InfluenceNodeType.ORGANISATION, "Example Org"),
            InfluenceNode("publication-1", InfluenceNodeType.PUBLICATION, "Example Publication"),
        ),
        observations=(observation,),
        generated_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        scope="seminar and publication mapping",
    )

    assert observation.is_publishable_finding() is False
    assert package.publishable_observations() == ()
