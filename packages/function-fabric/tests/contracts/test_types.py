from __future__ import annotations

from valo_function_fabric.types import can_consume, parse_type, workflow_type


def test_multi_refinement() -> None:
    t = parse_type("Evidence{Verified, Admitted}")
    assert t.base == "Evidence"
    assert t.refinements == {"Verified", "Admitted"}


def test_refinement_capability_semantics() -> None:
    assert can_consume("Evidence{Verified,Admitted}", "Verified<Evidence>")
    assert can_consume("Evidence{Verified,Admitted}", "Admitted<Evidence>")
    assert not can_consume("Verified<Evidence>", "Evidence{Verified,Admitted}")


def test_orthogonal_no_promotion() -> None:
    assert not can_consume("Authorized<Document>", "Verified<Document>")
    assert not can_consume("Confirmed<Action>", "Authorized<Action>")
    assert not can_consume("Verified<Document>", "Admitted<Document>")


def test_no_implicit_effect_promotion() -> None:
    assert not can_consume("Executed<Payment>", "VerifiedEffect<Payment>")
    assert not can_consume("Inferred<X>", "Confirmed<X>")
    assert not can_consume("Asserted<X>", "Verified<X>")


def test_identity_consumption() -> None:
    assert can_consume("Verified<Recipient>", "Verified<Recipient>")
    assert can_consume("Confirmed<Payment>", "Confirmed<Payment>")


def test_raw_never_satisfies_refined() -> None:
    assert not can_consume("Recipient", "Verified<Recipient>")
    assert can_consume("Verified<Recipient>", "Recipient")


def test_any_wide_open() -> None:
    assert can_consume("Verified<Recipient>", "any")
    assert can_consume("any", "Verified<Recipient>")


def test_approval_is_not_authorization() -> None:
    assert not can_consume("ApprovalAttestation", "Authorized<Action>")


def test_gateway_success_is_not_verified_effect() -> None:
    assert not can_consume("GatewaySuccess<Payment>", "VerifiedEffect<Payment>")


def test_workflow_lowering_is_lossless() -> None:
    """Governance refinements lower losslessly: never a single projected
    refinement, never 'any'."""
    assert workflow_type("Verified<Identity>") == "Verified<Identity>"
    assert workflow_type("Evidence{Verified,Admitted}") == "Evidence{Admitted,Verified}"
    assert workflow_type("VerifiedEffect<Payment>") == "VerifiedEffect<Payment>"
    assert workflow_type("Executed<Allocation>") == "Executed<Allocation>"
    assert workflow_type("Inferred<X>") == "Inferred<X>"
    assert workflow_type("Amount") == "Amount"


def test_opaque_constructor_lowers_to_any() -> None:
    """Opaque domain constructors carry no governance refinement; the ISA
    contract cannot express them, so they lower to 'any' (FF enforces)."""
    assert workflow_type("CandidateSet<Resource>") == "any"
    assert workflow_type("Calculated<Price>") == "any"


def test_domain_constructor_is_opaque() -> None:
    """Non-refinement wrappers (Calculated<Price>, CandidateSet<Resource>) are
    opaque atomic domain types, not governance refinements."""
    t = parse_type("Magic<Value>")
    assert t.base == "Magic<Value>"
    assert t.refinements == frozenset()
    assert not can_consume("Magic<Value>", "Verified<Value>")
    assert can_consume("Magic<Value>", "Magic<Value>")

