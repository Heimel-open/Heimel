from __future__ import annotations

from valo_workflow_isa.runtime.expr import evaluate


def test_truthy_field() -> None:
    assert evaluate("ok", {"ok": True})
    assert not evaluate("ok", {"ok": False})


def test_not() -> None:
    assert evaluate("not ok", {"ok": False})
    assert not evaluate("not ok", {"ok": True})


def test_equality() -> None:
    assert evaluate("state == READY", {"state": "READY"})
    assert not evaluate("state == READY", {"state": "OPEN"})
    assert evaluate("count != 0", {"count": 3})
    assert evaluate("flag == true", {"flag": True})


def test_numeric_comparison() -> None:
    assert evaluate("amount > 100000", {"amount": 150000})
    assert not evaluate("amount > 100000", {"amount": 50000})
    assert evaluate("score >= 5", {"score": 5})


def test_nested_scope() -> None:
    assert evaluate("entity.state == OPEN", {"entity": {"state": "OPEN"}})


def test_unknown_field_is_falsy() -> None:
    assert not evaluate("missing", {})
