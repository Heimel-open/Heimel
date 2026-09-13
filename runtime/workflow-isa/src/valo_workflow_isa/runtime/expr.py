from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"\s*(==|!=|>=|<=|>|<|not\s+|[A-Za-z_][A-Za-z0-9_.]*|\"[^\"]*\"|'[^']*'|\d+(\.\d+)?|true|false|null|\s+)")


def _coerce(token: str) -> Any:
    t = token.strip()
    if t in ("true", "True"):
        return True
    if t in ("false", "False"):
        return False
    if t in ("null", "None"):
        return None
    if t.startswith(('"', "'")) and t.endswith(('"', "'")):
        return t[1:-1]
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def evaluate(expression: str, scope: dict[str, Any]) -> bool:
    """Deterministic boolean evaluator for edge conditions and preconditions.

    Supported forms:
      field
      not field
      field == value    field != value
      field > value     field >= value
      field < value     field <= value
    `value` may be a quoted string, number, true/false or null.
    """
    expr = expression.strip()
    if not expr:
        return True
    if expr in ("true", "True"):
        return True
    if expr in ("false", "False"):
        return False

    m = re.match(r"^(not\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*(==|!=|>=|<=|>|<)?\s*(.*)$", expr)
    if not m:
        raise ValueError(f"unsupported expression: {expression}")

    negate = bool(m.group(1))
    field = m.group(2)
    op = m.group(3)
    rhs = m.group(4).strip()

    value = _resolve(scope, field)

    if op is None:
        result = bool(value)
    else:
        operand = _coerce(rhs) if rhs else None
        if op == "==":
            result = value == operand
        elif op == "!=":
            result = value != operand
        elif op in (">", ">=", "<", "<="):
            if value is None or operand is None:
                result = False
            else:
                try:
                    cmp_value = float(value)
                    cmp_operand = float(operand)
                except (TypeError, ValueError):
                    cmp_value, cmp_operand = value, operand
                if op == ">":
                    result = cmp_value > cmp_operand
                elif op == ">=":
                    result = cmp_value >= cmp_operand
                elif op == "<":
                    result = cmp_value < cmp_operand
                else:
                    result = cmp_value <= cmp_operand
        else:  # pragma: no cover
            raise ValueError(f"unsupported operator: {op}")

    return (not result) if negate else result


def _resolve(scope: dict[str, Any], field: str) -> Any:
    parts = field.split(".")
    value: Any = scope
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value
