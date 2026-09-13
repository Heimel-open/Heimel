from __future__ import annotations


class CompileError(ValueError):
    """The graph failed static validation. Fail closed: nothing is executed."""
