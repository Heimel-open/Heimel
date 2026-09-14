from tools.authority_decomposition import (
    BoundaryControl,
    RealizationStep,
    RealizationWitness,
    analyze_authority_decomposition,
)


def test_clean_witness_set_passes_all_invariants():
    witnesses = [
        RealizationWitness(
            witness_id="normal",
            effect="payment:settle",
            steps=(
                RealizationStep("propose", "agent"),
                RealizationStep("gateway", "boundary", crosses_boundary=True),
                RealizationStep("settle", "provider", irreversible=True),
                RealizationStep("receipt", "veritas", evidence=True),
            ),
        )
    ]
    result = analyze_authority_decomposition(
        effect="payment:settle",
        witnesses=witnesses,
        boundary=BoundaryControl(boundary_id="gateway"),
    )
    assert result.passes
    assert result.minimal_coalitions == (frozenset({"agent", "boundary", "provider", "veritas"}),)


def test_witness_bypass_kills_no_direct_effect_path():
    witnesses = [
        RealizationWitness(
            witness_id="legacy-sdk",
            effect="payment:settle",
            steps=(
                RealizationStep("legacy-call", "agent"),
                RealizationStep("settle", "provider", irreversible=True),
            ),
        )
    ]
    result = analyze_authority_decomposition(
        effect="payment:settle",
        witnesses=witnesses,
        boundary=BoundaryControl(boundary_id="gateway"),
    )
    assert not result.no_direct_effect_path
    assert result.witness_bypass == ("legacy-sdk",)


def test_unilateral_boundary_capture_is_detected():
    witnesses = [
        RealizationWitness(
            witness_id="normal",
            effect="payment:settle",
            steps=(
                RealizationStep("propose", "operator"),
                RealizationStep("gateway", "boundary", crosses_boundary=True),
                RealizationStep("settle", "provider", irreversible=True),
                RealizationStep("receipt", "veritas", evidence=True),
            ),
        )
    ]
    result = analyze_authority_decomposition(
        effect="payment:settle",
        witnesses=witnesses,
        boundary=BoundaryControl(
            boundary_id="gateway",
            disable_domains=frozenset({"operator"}),
        ),
    )
    assert not result.no_unilateral_boundary_capture
    assert result.boundary_capture_domains == frozenset({"operator"})


def test_irreversible_commit_before_boundary_is_detected():
    witnesses = [
        RealizationWitness(
            witness_id="reserve-then-check",
            effect="payment:settle",
            steps=(
                RealizationStep("reserve-funds", "provider", irreversible=True),
                RealizationStep("gateway", "boundary", crosses_boundary=True),
                RealizationStep("settle", "provider", irreversible=True),
                RealizationStep("receipt", "veritas", evidence=True),
            ),
        )
    ]
    result = analyze_authority_decomposition(
        effect="payment:settle",
        witnesses=witnesses,
        boundary=BoundaryControl(boundary_id="gateway"),
    )
    assert not result.commit_point_coverage
    assert result.uncovered_commit_points == ("reserve-then-check:reserve-funds",)


def test_evidence_control_collapse_is_detected():
    witnesses = [
        RealizationWitness(
            witness_id="self-attested",
            effect="payment:settle",
            steps=(
                RealizationStep("gateway", "operator", crosses_boundary=True),
                RealizationStep("settle", "operator", irreversible=True),
                RealizationStep("receipt", "operator", evidence=True),
            ),
        )
    ]
    result = analyze_authority_decomposition(
        effect="payment:settle",
        witnesses=witnesses,
        boundary=BoundaryControl(boundary_id="gateway"),
    )
    assert not result.evidence_independence
    assert result.evidence_control_collapse == ("self-attested",)


def test_minimal_coalitions_remove_supersets():
    witnesses = [
        RealizationWitness(
            witness_id="short",
            effect="effect:x",
            steps=(
                RealizationStep("gateway", "a", crosses_boundary=True),
                RealizationStep("commit", "b", irreversible=True),
                RealizationStep("receipt", "c", evidence=True),
            ),
        ),
        RealizationWitness(
            witness_id="long",
            effect="effect:x",
            steps=(
                RealizationStep("prepare", "d"),
                RealizationStep("gateway", "a", crosses_boundary=True),
                RealizationStep("commit", "b", irreversible=True),
                RealizationStep("receipt", "c", evidence=True),
            ),
        ),
    ]
    result = analyze_authority_decomposition(
        effect="effect:x",
        witnesses=witnesses,
        boundary=BoundaryControl(boundary_id="gateway"),
    )
    assert result.minimal_coalitions == (frozenset({"a", "b", "c"}),)
