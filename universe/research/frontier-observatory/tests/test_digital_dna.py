from digital_dna import (
    ContinuityDecision,
    ContinuityEvaluator,
    ContinuityReceipt,
    DigitalDNAManifest,
    EquivalenceRule,
    IdentityTransition,
    MemoryRecord,
    MemoryStatus,
    PairOperator,
    StateOperator,
    StateRule,
)


def manifest() -> DigitalDNAManifest:
    return DigitalDNAManifest(
        identity_id="person:njal",
        version="1",
        state_space_id="personal-twin.v1",
        required_state_paths=("principal.id", "continuity.status"),
        allowed_transformations=frozenset({"LEARN", "CORRECT", "MEMORY_UPDATE"}),
        equivalence_rules=(
            EquivalenceRule("principal.id"),
            EquivalenceRule(
                "preferences.risk_tolerance",
                PairOperator.NUMERIC_DELTA_LTE,
                tolerance=0.25,
            ),
        ),
        invariants=(
            StateRule("principal.id", StateOperator.EQUAL, "person:njal"),
        ),
        collapse_conditions=(
            StateRule("continuity.status", StateOperator.EQUAL, "INVALIDATED"),
        ),
        authorized_amenders=frozenset({"principal:person:njal"}),
    )


def state(risk: float = 0.5, status: str = "ACTIVE") -> dict:
    return {
        "principal": {"id": "person:njal"},
        "preferences": {"risk_tolerance": risk},
        "continuity": {"status": status},
    }


def transition(**overrides) -> IdentityTransition:
    values = {
        "transition_id": "tx-001",
        "transformation": "LEARN",
        "before_state": state(),
        "after_state": state(0.6),
        "observed_at": "2026-08-17T06:00:00Z",
        "evidence_digests": ("sha256:evidence-1",),
    }
    values.update(overrides)
    return IdentityTransition(**values)


def test_legitimate_change_continues():
    result = ContinuityEvaluator().evaluate(manifest(), transition())
    assert result.decision is ContinuityDecision.CONTINUES


def test_undeclared_transformation_breaks_continuity():
    result = ContinuityEvaluator().evaluate(
        manifest(), transition(transformation="REWRITE_IDENTITY")
    )
    assert result.decision is ContinuityDecision.BREAK
    assert result.reasons == ("transformation_not_allowed:REWRITE_IDENTITY",)


def test_invariant_violation_breaks_continuity():
    after = state()
    after["principal"]["id"] = "person:other"

    result = ContinuityEvaluator().evaluate(manifest(), transition(after_state=after))

    assert result.decision is ContinuityDecision.BREAK
    assert any(
        reason.startswith("invariant_failed:principal.id") for reason in result.reasons
    )


def test_equivalence_class_violation_breaks_continuity():
    result = ContinuityEvaluator().evaluate(
        manifest(), transition(after_state=state(risk=0.9))
    )
    assert result.decision is ContinuityDecision.BREAK
    assert any(
        reason.startswith("equivalence_failed:preferences.risk_tolerance")
        for reason in result.reasons
    )


def test_collapse_condition_breaks_continuity():
    result = ContinuityEvaluator().evaluate(
        manifest(), transition(after_state=state(status="INVALIDATED"))
    )
    assert result.decision is ContinuityDecision.BREAK
    assert any(
        reason.startswith("collapse_condition_met:continuity.status")
        for reason in result.reasons
    )


def test_missing_required_state_is_indeterminate():
    after = state()
    del after["continuity"]

    result = ContinuityEvaluator().evaluate(manifest(), transition(after_state=after))

    assert result.decision is ContinuityDecision.INDETERMINATE
    assert "required_path_missing_after:continuity.status" in result.reasons


def test_protected_amendment_without_authority_requires_review():
    result = ContinuityEvaluator().evaluate(
        manifest(),
        transition(
            proposes_protected_amendment=True,
            proposed_manifest_digest="sha256:new-manifest",
        ),
    )
    assert result.decision is ContinuityDecision.REVIEW_REQUIRED


def test_unauthorized_amender_breaks_continuity():
    result = ContinuityEvaluator().evaluate(
        manifest(),
        transition(
            proposes_protected_amendment=True,
            proposed_manifest_digest="sha256:new-manifest",
            amendment_authority="agent:self",
        ),
    )
    assert result.decision is ContinuityDecision.BREAK
    assert result.reasons == ("unauthorized_amender:agent:self",)


def test_authorized_amendment_can_continue():
    result = ContinuityEvaluator().evaluate(
        manifest(),
        transition(
            proposes_protected_amendment=True,
            proposed_manifest_digest="sha256:new-manifest",
            amendment_authority="principal:person:njal",
        ),
    )
    assert result.decision is ContinuityDecision.CONTINUES
    assert "protected_amendment_authorized:principal:person:njal" in result.reasons


def test_superseded_memory_requires_lineage():
    record = MemoryRecord(
        memory_id="memory:2",
        content_digest="sha256:content",
        status=MemoryStatus.SUPERSEDED,
    )
    result = ContinuityEvaluator().evaluate(
        manifest(),
        transition(transformation="MEMORY_UPDATE", memory_records=(record,)),
    )
    assert result.decision is ContinuityDecision.INDETERMINATE
    assert "memory_lineage_missing:memory:2:SUPERSEDED" in result.reasons


def test_receipt_is_deterministic_and_hash_chainable():
    evaluator = ContinuityEvaluator()
    tx = transition()
    result = evaluator.evaluate(manifest(), tx)

    receipt_a = ContinuityReceipt.from_evaluation(manifest(), tx, result)
    receipt_b = ContinuityReceipt.from_evaluation(manifest(), tx, result)
    chained = ContinuityReceipt.from_evaluation(
        manifest(),
        tx,
        result,
        previous_receipt_digest=receipt_a.receipt_digest(),
    )

    assert receipt_a.receipt_digest() == receipt_b.receipt_digest()
    assert chained.previous_receipt_digest == receipt_a.receipt_digest()
    assert chained.receipt_digest() != receipt_a.receipt_digest()
