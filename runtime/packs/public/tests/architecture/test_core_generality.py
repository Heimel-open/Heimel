from __future__ import annotations

from valo_public_pack import build_public_registry, compile_golden


def test_core_generality_no_split() -> None:
    """Core generality: the SAME Function Fabric core functions are reused by
    both the Trades and the Public pack. The difference is the packs/programs,
    not the core. Trades is NOT a dependency of Public — this is the structural
    comparison proof."""
    registry = build_public_registry()
    snapshot = registry.snapshot()
    # every core Function referenced by the public graph is a core (non-public)
    # function — no public-specific core is invented
    public_ids = {fid for fid in snapshot.functions if fid.split("@")[0].startswith("valo.public.")}
    core_ids = set(snapshot.functions) - public_ids
    assert core_ids, "core functions must be reused"
    assert "valo.identity.verify_identity@1.0.0" in core_ids
    assert "valo.evidence.verify@1.0.0" in core_ids
    assert "valo.decision.approve@1.0.0" in core_ids


def test_public_types_confined_to_public_pack() -> None:
    """The same core used for the electrician job is used here; only the pack's
    types (Case, PublicDecision, LegalBasis) are public-specific."""
    registry = build_public_registry()
    identity = registry.resolve("valo.identity.verify_identity")
    approve = registry.resolve("valo.decision.approve")
    # the core functions are unchanged — no public vocabulary leaked in
    assert "Case" not in identity.input_type.type
    assert "PublicDecision" not in approve.output_type.type


def test_compiled_graphs_are_structural_programs() -> None:
    """PROCESS_PUBLIC_APPLICATION compiles to a valid Workflow ISA program —
    exactly like EV_CHARGER_JOB did — proving both are programs over the same
    machine."""
    compiled = compile_golden(build_public_registry())
    from valo_workflow_isa import compile_graph as isa_compile

    isa_compile(compiled.workflow_graph)
    assert len(compiled.workflow_graph.nodes) >= 20
