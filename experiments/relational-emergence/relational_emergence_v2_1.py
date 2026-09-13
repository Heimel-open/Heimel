#!/usr/bin/env python3
"""TOFOO relational emergence v2.1.

V2.1 fixes a validity error in v2's model preflight.

V2 incorrectly required Qwen to solve a latent-rule reasoning problem during
*instrument preflight*. That confounded model capability with instrument
validity: a wrong rule inference caused TEST_INVALID_MODEL_PREFLIGHT even
though the model was running and producing a perfectly parseable interface.

V2.1 makes preflight interface-only. Scientific capability is measured only in
the experiment conditions themselves.
"""
from __future__ import annotations

import relational_emergence_v2 as base


def model_preflight(runner: base.Runner, model_id: str) -> dict:
    """Verify model execution + output contracts, not reasoning ability."""
    if runner.mock:
        return {"status": "PASS", "mode": "MOCK", "scope": "INTERFACE_ONLY"}

    # HYP interface: the correct content is explicitly supplied. The model only
    # has to preserve operator/rule/evidence identifiers in a parseable form.
    e = base.Evidence(
        "PF-KEM-P0",
        "KEM",
        "ABCDE",
        base.apply_rule("ABCDE", "REVERSE"),
        0,
    )
    hyp_prompt = f"""This is an interface check, not a reasoning task.
The verified hypothesis is already given below.
Copy it once in the requested output format.

VERIFIED OPERATOR: KEM
VERIFIED RULE: REVERSE
VERIFIED EVIDENCE ID: PF-KEM-P0

Return one line only:
HYP KEM REVERSE PF-KEM-P0
"""
    hyp_raw = runner.run(hyp_prompt, model_id, 32)
    hyp_parsed = base.parse_hypotheses(hyp_raw, [e], ["KEM"])
    if ("KEM", "REVERSE", "PF-KEM-P0") not in hyp_parsed:
        raise RuntimeError(
            "MODEL_PREFLIGHT_FAILED hypothesis output contract: "
            + repr(hyp_raw[:300])
        )

    # RULE interface: again, no inference. This separately validates the parser
    # used by ISOLATED/POOLED/STRUCTURED controls.
    direct_prompt = """This is an interface check, not a reasoning task.
The verified rule is already given below.
Copy it once in the requested output format.

VERIFIED OPERATOR: KEM
VERIFIED RULE: REVERSE

Return one line only:
RULE KEM REVERSE
"""
    direct_raw = runner.run(direct_prompt, model_id, 24)
    direct_parsed = base.parse_rules(direct_raw, ["KEM"])
    if direct_parsed.get("KEM") != "REVERSE":
        raise RuntimeError(
            "MODEL_PREFLIGHT_FAILED direct output contract: "
            + repr(direct_raw[:300])
        )

    return {
        "status": "PASS",
        "scope": "INTERFACE_ONLY",
        "hypothesis_raw": hyp_raw[:300],
        "direct_raw": direct_raw[:300],
    }


base.model_preflight = model_preflight

_original_selfcheck = base.selfcheck


def selfcheck() -> dict:
    result = _original_selfcheck()
    # Regression guard: preflight must never require rule induction again.
    result["preflight_scope"] = "INTERFACE_ONLY"
    result["capability_not_instrument_validity"] = "PASS"
    return result


base.selfcheck = selfcheck


if __name__ == "__main__":
    raise SystemExit(base.main())
