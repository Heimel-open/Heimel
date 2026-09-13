#!/usr/bin/env python3
"""Claude Code PreToolUse adapter for VALO.

This hook has no authority of its own. For matched tool calls it relays the exact
Claude event to an external VALO/reht gate and only forwards an explicit
allow/deny result. Missing, malformed or non-final results fail closed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

GATE_ENV = "VALO_REHT_PRETOOL_GATE"
TIMEOUT_SECONDS = 8


def _decision(decision: str, reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def _deny(reason: str) -> int:
    print(json.dumps(_decision("deny", reason), separators=(",", ":")))
    return 0


def _load_event() -> dict[str, Any] | None:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _validate_gate_output(stdout: str) -> tuple[str, str] | None:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    output = value.get("hookSpecificOutput")
    if not isinstance(output, dict):
        return None
    if output.get("hookEventName") != "PreToolUse":
        return None
    decision = output.get("permissionDecision")
    if decision not in {"allow", "deny"}:
        return None
    reason = output.get("permissionDecisionReason", "VALO gate decision")
    if not isinstance(reason, str) or not reason.strip():
        reason = "VALO gate decision"
    # Do not forward updatedInput or other mutation fields: a changed effect must
    # receive a fresh authorization decision for the exact new input.
    return decision, reason


def main() -> int:
    event = _load_event()
    if event is None:
        return _deny("VALO gate refused: invalid PreToolUse input")
    if event.get("hook_event_name") != "PreToolUse":
        return _deny("VALO gate refused: unexpected hook event")
    if not isinstance(event.get("tool_name"), str) or not isinstance(
        event.get("tool_input"), dict
    ):
        return _deny("VALO gate refused: incomplete tool event")

    gate = os.environ.get(GATE_ENV, "").strip()
    if not gate:
        return _deny(f"VALO gate refused: {GATE_ENV} is not configured")
    if not os.path.isabs(gate):
        return _deny("VALO gate refused: gate path must be absolute")
    if not os.path.isfile(gate) or not os.access(gate, os.X_OK):
        return _deny("VALO gate refused: configured gate is not executable")

    payload = json.dumps(event, separators=(",", ":"), sort_keys=True)
    try:
        proc = subprocess.run(
            [gate],
            input=payload,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return _deny("VALO gate refused: external gate unavailable")

    if proc.returncode != 0:
        return _deny("VALO gate refused: external gate failed")

    validated = _validate_gate_output(proc.stdout)
    if validated is None:
        return _deny(
            "VALO gate refused: external gate did not return a final allow/deny decision"
        )

    decision, reason = validated
    print(json.dumps(_decision(decision, reason), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
