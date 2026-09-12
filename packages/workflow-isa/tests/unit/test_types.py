from __future__ import annotations

from valo_workflow_isa.types import can_consume, parse_type


def test_parse_types() -> None:
    assert parse_type("Verified<Recipient>").wrapper == "Verified"
    assert parse_type("Verified<Recipient>").base == "Recipient"
    assert parse_type("Recipient").wrapper is None
    assert parse_type("any").base == "any"


def test_candidate_cannot_satisfy_verified() -> None:
    assert not can_consume("Candidate<Recipient>", "Verified<Recipient>")


def test_identity_consumption() -> None:
    assert can_consume("Verified<Recipient>", "Verified<Recipient>")
    assert can_consume("Admitted<Document>", "Admitted<Document>")
    assert can_consume("Authorized<Action>", "Authorized<Action>")
    assert can_consume("Reserved<Resource>", "Reserved<Resource>")


def test_no_implicit_cross_wrapper_promotion() -> None:
    """Verified, Admitted, Authorized, Reserved, Confirmed are orthogonal
    refinements. There is no strength ladder and no implicit promotion."""
    assert not can_consume("Confirmed<Recipient>", "Verified<Recipient>")
    assert not can_consume("Verified<Recipient>", "Admitted<Recipient>")
    assert not can_consume("Authorized<Document>", "Verified<Document>")
    assert not can_consume("Reserved<Resource>", "Verified<Resource>")
    assert not can_consume("Confirmed<Action>", "Authorized<Action>")


def test_wrapper_identity_and_mismatch() -> None:
    assert can_consume("Admitted<Document>", "Admitted<Document>")
    assert not can_consume("Verified<Document>", "Admitted<Document>")
    assert not can_consume("Admitted<Document>", "Verified<Document>")
    assert not can_consume("Admitted<Document>", "Confirmed<Document>")


def test_base_type_mismatch() -> None:
    assert not can_consume("Verified<Recipient>", "Verified<Account>")


def test_raw_never_satisfies_wrapped() -> None:
    assert not can_consume("Recipient", "Verified<Recipient>")
    assert can_consume("Verified<Recipient>", "Recipient")


def test_any_is_wide_open() -> None:
    assert can_consume("Verified<Recipient>", "any")
    assert can_consume("any", "Verified<Recipient>")


def test_parse_multi_refinement() -> None:
    t = parse_type("Evidence{VERIFIED, ADMITTED}")
    assert t.base == "Evidence"
    assert t.refinements == {"Verified", "Admitted"}
    assert t.wrapper is None
    assert str(t) in ("Evidence{Admitted,Verified}", "Evidence{Verified,Admitted}")


def test_multi_refinement_satisfies_single() -> None:
    assert can_consume("Evidence{VERIFIED, ADMITTED}", "Verified<Evidence>")
    assert can_consume("Evidence{VERIFIED, ADMITTED}", "Admitted<Evidence>")


def test_single_does_not_satisfy_multi_refinement() -> None:
    assert not can_consume("Verified<Evidence>", "Evidence{VERIFIED, ADMITTED}")
    assert not can_consume("Admitted<Evidence>", "Evidence{VERIFIED, ADMITTED}")


def test_multi_refinement_does_not_cross_base() -> None:
    assert not can_consume("Identity{VERIFIED, ADMITTED}", "Verified<Evidence>")
