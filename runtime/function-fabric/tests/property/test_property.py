from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from valo_workflow_isa import compile_graph as isa_compile_graph

from tests.helpers import call, graph
from valo_function_fabric import can_consume, compile_function_graph
from valo_function_fabric.types import ISA_REFINEMENTS, REFINEMENTS

# 'any' is a reserved wildcard (opaque constructors lower to it) — exclude it
# from the generated base domain so it never collides with the escape hatch.
BASES = st.text(min_size=1, max_size=5).map(
    lambda s: "".join(ch for ch in s if ch.isalnum()) or "T"
).filter(lambda s: s.lower() != "any")
REFS = list(REFINEMENTS)


@settings(max_examples=20)
@given(st.lists(st.tuples(BASES, st.sampled_from(REFS + [None])), min_size=1, max_size=6))
def test_property_type_consumption_is_transitive(pairs) -> None:
    types = [f"{w}<{b}>" if w else b for b, w in pairs]
    for a in types:
        for b in types:
            for c in types:
                if can_consume(a, b) and can_consume(b, c):
                    assert can_consume(a, c), f"transitivity broken: {a} >= {b} >= {c}"


def test_property_compiled_graph_is_valid_isa(snapshot, stdlib_registry) -> None:
    g = graph(
        "prop.valid",
        [call("price", "valo.finance.price", input_bindings={"scope": "scope"})],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
    )
    compiled = compile_function_graph(g, snapshot)
    isa_compile_graph(compiled.workflow_graph)  # must not raise


def test_property_function_effects_cover_compiled(snapshot, stdlib_registry) -> None:
    """Golden invariant across the whole stdlib: every function's declared
    effects cover its compiled workflow's effects."""
    for entry in snapshot.functions.values():
        definition = entry.definition
        graph = stdlib_registry.graph_for(definition)
        node_effects = {n.effect_type.value for n in graph.nodes if n.effect_type.value != "PURE"}
        declared = set(definition.effects)
        assert node_effects.issubset(declared), f"{definition.identity} leaks effects {node_effects - declared}"


def test_property_risk_never_decreases_in_stdlib(stdlib_registry) -> None:
    """Composition governance: ONBOARD risk >= each child's risk."""
    from valo_function_fabric.contracts.common import RISK_ORDER

    onboard = stdlib_registry.get("valo.lifecycle.onboard@1.0.0")
    for dep in stdlib_registry.dependencies("valo.lifecycle.onboard"):
        dep_def = stdlib_registry.resolve(dep)
        assert RISK_ORDER[onboard.risk_class] >= RISK_ORDER[dep_def.risk_class]


@settings(max_examples=20)
@given(st.sampled_from(["Verified", "Authorized", "Confirmed", "Admitted", "Reserved"]), BASES)
def test_property_no_implicit_strength_increase(wrapper, base) -> None:
    """A single-refinement type never satisfies a DIFFERENT single refinement
    of the same base (orthogonality), in either direction."""
    others = [r for r in ISA_REFINEMENTS if r != wrapper]
    for other in others:
        assert not can_consume(f"{wrapper}<{base}>", f"{other}<{base}>")


def test_property_compilation_deterministic(snapshot, stdlib_registry) -> None:
    g = graph(
        "prop.deterministic",
        [call("price", "valo.finance.price", input_bindings={"scope": "scope"})],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
    )
    hashes = {compile_function_graph(g, snapshot).compiled_graph_hash for _ in range(3)}
    assert len(hashes) == 1
