import pytest

from heimel_design_plane import (
    CandidateDesign,
    DesignPlane,
    DesignPlaneError,
    EvidenceVector,
    Intent,
    PromotionStatus,
)


def test_gcu_promotion_stops_at_authority_boundary():
    intent = Intent(
        intent_id="gcu-001",
        domain="gcu",
        objective="complete invoice reconciliation",
        constraints=("bounded_cost",),
        invariants=("no_unapproved_payment",),
        measures=("completion", "quality", "sla", "cost", "exception_rate"),
    )
    plane = DesignPlane(intent)
    candidate = CandidateDesign(
        candidate_id="agent-first",
        intent_digest=intent.digest,
        mechanism={"carrier": "agent", "exception": "human"},
    )
    plane.register_candidate(candidate)
    plane.attach_evidence(
        EvidenceVector(
            candidate_digest=candidate.digest,
            dimensions={
                "completion": 1.0,
                "quality": 0.98,
                "sla": 0.95,
                "cost": 0.90,
                "exception_rate": 0.85,
            },
            controls_passed=("contract", "completion_proof"),
            shadow_verified=True,
            provenance=("shadow:gcu-001",),
        )
    )

    proposal = plane.propose_promotion(
        candidate.digest,
        required_controls=("contract", "completion_proof"),
    )

    assert proposal.status is PromotionStatus.AUTHORITY_REQUIRED
    assert proposal.effect_class == "work_unit_execution"
    assert proposal.boundary_effect_fields(actor_id="worker-7", target="gcu:gcu-001") == {
        "effect_id": proposal.digest,
        "actor_id": "worker-7",
        "action": "promote:work_unit_execution",
        "target": "gcu:gcu-001",
    }


def test_promotion_fails_without_shadow_evidence():
    intent = Intent("alpha-001", "alpha", "reduce gateway latency")
    plane = DesignPlane(intent)
    candidate = CandidateDesign("candidate-a", intent.digest, {"topology": "a"})
    plane.register_candidate(candidate)
    plane.attach_evidence(
        EvidenceVector(
            candidate_digest=candidate.digest,
            dimensions={
                "correctness": 1.0,
                "security": 1.0,
                "reliability": 1.0,
                "cost": 0.8,
                "complexity": 0.7,
            },
            controls_passed=("tests",),
            shadow_verified=False,
        )
    )

    with pytest.raises(DesignPlaneError, match="shadow"):
        plane.propose_promotion(candidate.digest, required_controls=("tests",))


def test_evidence_cannot_attach_to_unknown_candidate():
    intent = Intent("traxin-001", "traxin", "improve case throughput")
    plane = DesignPlane(intent)

    with pytest.raises(DesignPlaneError, match="unknown candidate"):
        plane.attach_evidence(
            EvidenceVector(
                candidate_digest="sha256:unknown",
                dimensions={},
            )
        )


def test_relaion_candidate_is_bound_to_seed_intent():
    intent = Intent(
        "relaion-seed-001",
        "relaion",
        "stewarded development without breaking lineage",
        invariants=("lineage_preserved", "stewardship_required"),
    )
    plane = DesignPlane(intent)
    wrong = CandidateDesign("path-a", "sha256:wrong", {"path": "a"})

    with pytest.raises(DesignPlaneError, match="active intent"):
        plane.register_candidate(wrong)


def test_pareto_frontier_preserves_tradeoffs():
    intent = Intent("alpha-002", "alpha", "select bounded architecture")
    plane = DesignPlane(intent)

    a = CandidateDesign("a", intent.digest, {"design": "simple"})
    b = CandidateDesign("b", intent.digest, {"design": "secure"})
    c = CandidateDesign("c", intent.digest, {"design": "dominated"})
    for candidate in (a, b, c):
        plane.register_candidate(candidate)

    plane.attach_evidence(EvidenceVector(a.digest, {"security": 0.7, "cost": 0.9}))
    plane.attach_evidence(EvidenceVector(b.digest, {"security": 0.95, "cost": 0.7}))
    plane.attach_evidence(EvidenceVector(c.digest, {"security": 0.6, "cost": 0.6}))

    frontier = plane.pareto_candidates(("security", "cost"))

    assert {candidate.candidate_id for candidate in frontier} == {"a", "b"}
