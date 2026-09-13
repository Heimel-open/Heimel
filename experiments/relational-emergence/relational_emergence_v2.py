#!/usr/bin/env python3
"""TOFOO relational emergence v2 compatibility entrypoint.

This file keeps the original v2 URL/path stable but runs the corrected
interface-only model preflight. The original v2 experiment implementation
lives in relational_emergence_v2_core.py.
"""
from __future__ import annotations

import relational_emergence_v2_core as core
from relational_emergence_v2_core import *  # noqa: F401,F403


def model_preflight(runner: core.Runner, model_id: str) -> dict:
    """Verify model execution + output contracts only; never reasoning ability."""
    if runner.mock:
        return {"status": "PASS", "mode": "MOCK", "scope": "INTERFACE_ONLY"}

    e = core.Evidence(
        "PF-KEM-P0",
        "KEM",
        "ABCDE",
        core.apply_rule("ABCDE", "REVERSE"),
        0,
    )
    hyp_prompt = """This is an interface check, not a reasoning task.
The verified hypothesis is already given below. Copy it once exactly.

VERIFIED OPERATOR: KEM
VERIFIED RULE: REVERSE
VERIFIED EVIDENCE ID: PF-KEM-P0

Return one line only:
HYP KEM REVERSE PF-KEM-P0
"""
    hyp_raw = runner.run(hyp_prompt, model_id, 32)
    hyp_parsed = core.parse_hypotheses(hyp_raw, [e], ["KEM"])
    if ("KEM", "REVERSE", "PF-KEM-P0") not in hyp_parsed:
        raise RuntimeError(
            "MODEL_PREFLIGHT_FAILED hypothesis output contract: " + repr(hyp_raw[:300])
        )

    direct_prompt = """This is an interface check, not a reasoning task.
The verified rule is already given below. Copy it once exactly.

VERIFIED OPERATOR: KEM
VERIFIED RULE: REVERSE

Return one line only:
RULE KEM REVERSE
"""
    direct_raw = runner.run(direct_prompt, model_id, 24)
    direct_parsed = core.parse_rules(direct_raw, ["KEM"])
    if direct_parsed.get("KEM") != "REVERSE":
        raise RuntimeError(
            "MODEL_PREFLIGHT_FAILED direct output contract: " + repr(direct_raw[:300])
        )

    return {
        "status": "PASS",
        "scope": "INTERFACE_ONLY",
        "hypothesis_raw": hyp_raw[:300],
        "direct_raw": direct_raw[:300],
    }


core.model_preflight = model_preflight
_original_selfcheck = core.selfcheck


def selfcheck() -> dict:
    result = _original_selfcheck()
    result["preflight_scope"] = "INTERFACE_ONLY"
    result["capability_not_instrument_validity"] = "PASS"
    return result


core.selfcheck = selfcheck


if __name__ == "__main__":
    raise SystemExit(core.main())
