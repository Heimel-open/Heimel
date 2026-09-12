from __future__ import annotations

import pytest

from tests.helpers import call, graph
from valo_function_fabric import CompileError, TypecheckError, compile_function_graph
from valo_function_fabric.contracts import FunctionEdge


def test_raw_bank_account_cannot_feed_pay(snapshot, stdlib_registry) -> None:
    """Function algebra: an upstream output can never satisfy an incompatible
    downstream input — no implicit promotion across bases or refinements."""
    g = graph(
        "algebratest.mismatch",
        [
            call("produce", "valo.identity.verify_identity", input_bindings={"candidate": "identity"}, output_bindings={"identity": "verified"}),
            call("check", "valo.qualification.check_eligibility", input_bindings={"criteria": "produce"}),
        ],
        edges=[FunctionEdge(source="produce", target="check")],
        inputs={"identity": "IdentityCandidate"},
        outputs={"result": "EligibilityResult"},
    )
    # Verified<Identity> (output of verify) can never satisfy EligibilityCriteria
    with pytest.raises(TypecheckError, match="no implicit promotion"):
        compile_function_graph(g, snapshot)


def test_unknown_function_rejected(snapshot, stdlib_registry) -> None:
    g = graph(
        "test.unknown", [call("a", "valo.nonexistent.function")],
        inputs={"x": "Request"}, outputs={"y": "any"},
    )
    with pytest.raises(CompileError, match="unknown function"):
        compile_function_graph(g, snapshot)


def test_unknown_version_rejected(snapshot, stdlib_registry) -> None:
    g = graph(
        "test.version", [call("a", "valo.finance.pay", version="9.9.9")],
        inputs={"payment": "PaymentRequest"}, outputs={"payment_result": "VerifiedEffect<Payment>"},
    )
    with pytest.raises(CompileError, match="unknown function"):
        compile_function_graph(g, snapshot)


def test_missing_graph_input_rejected(snapshot, stdlib_registry) -> None:
    g = graph(
        "test.missing_input",
        [call("a", "valo.finance.pay", input_bindings={"payment": "does_not_exist"})],
        inputs={"other": "PaymentRequest"}, outputs={"payment_result": "VerifiedEffect<Payment>"},
    )
    with pytest.raises(TypecheckError, match="unknown source"):
        compile_function_graph(g, snapshot)


def test_compile_is_deterministic(snapshot, stdlib_registry) -> None:
    g = graph(
        "test.determinism",
        [call("a", "valo.finance.price", input_bindings={"scope": "scope"})],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
    )
    c1 = compile_function_graph(g, snapshot)
    c2 = compile_function_graph(g, snapshot)
    assert c1.compiled_graph_hash == c2.compiled_graph_hash
    assert c1.function_graph_hash == c2.function_graph_hash
    assert c1.registry_snapshot_hash == snapshot.hash


def test_registry_mutation_does_not_affect_compiled(snapshot, stdlib_registry) -> None:
    g = graph(
        "test.pinned",
        [call("a", "valo.finance.price", input_bindings={"scope": "scope"})],
        inputs={"scope": "PriceScope"}, outputs={"price": "Calculated<Price>"},
    )
    compiled = compile_function_graph(g, snapshot)
    stdlib_registry.deprecate("valo.finance.price", "1.0.0")
    new_snapshot = stdlib_registry.snapshot()
    assert new_snapshot.hash != snapshot.hash
    # the compiled result is still bound to the OLD snapshot
    assert compiled.registry_snapshot_hash == snapshot.hash
    assert compiled.registry_snapshot_hash != new_snapshot.hash

