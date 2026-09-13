"""
Boundaries — assert-no-execution guard for the Personal AI Operating System.

The OS is a co-worker that proposes + remembers.
Execution is OUT OF SCOPE — REHT/Harness own that.

This module provides a guard that MUST be called before any operation that
looks like execution. If the guard is triggered, it raises ExecutionGuardError.

Canonical rules:
  - REHT sole admissibility authority — OS proposes, never decides/executes.
  - This boundary is asserted in code + tests.
  - Deterministic, synchronous.
"""

from __future__ import annotations

import os
import traceback


class ExecutionGuardError(RuntimeError):
    """Raised when an execution path is attempted in the PAIOS layer."""

    def __init__(self, message: str = "", detail: str = "") -> None:
        full = message or "PAIOS: execution is out of scope. REHT/Harness own execution."
        if detail:
            full += f"\nDetail: {detail}"
        super().__init__(full)


def assert_no_execution(
    context: str = "",
    raise_on_call: bool = True,
) -> None:
    """Assert that no execution path is triggered in PAIOS.

    This guard MUST be called at every entry point that could be confused
    with an execution path.

    Args:
        context: Description of the calling context (for error detail).
        raise_on_call: If True (default), raises ExecutionGuardError immediately.
                       If False, logs a warning instead (for non-fatal checks).

    Raises:
        ExecutionGuardError: if *raise_on_call* is True.
    """
    if not raise_on_call:
        return

    caller_frame = traceback.extract_stack(limit=3)[0]
    caller_info = f"{caller_frame.filename}:{caller_frame.lineno} in {caller_frame.name}"

    raise ExecutionGuardError(
        message="PAIOS execution guard triggered",
        detail=f"Context: {context}\nCaller: {caller_info}",
    )


def guard_proposal_execution(envelope_dict: dict) -> None:
    """Guard that prevents any execution path from being reached with a proposal.

    This is the primary boundary check for the governed proposal flow.
    It MUST be called before any code path that would act on a proposal.

    Args:
        envelope_dict: The action envelope dict (for diagnostic context).

    Raises:
        ExecutionGuardError: always.
    """
    action_type = envelope_dict.get("action_type", "unknown")
    action_id = envelope_dict.get("action_id", "unknown")
    assert_no_execution(
        context=(
            f"Proposal execution blocked: action_type={action_type}, "
            f"action_id={action_id}. "
            f"PAIOS proposes. REHT/Harness executes."
        ),
    )
