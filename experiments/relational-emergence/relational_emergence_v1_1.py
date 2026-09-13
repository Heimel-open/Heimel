#!/usr/bin/env python3
"""TOFOO relational emergence harness v1.1.

Hotfixes v1's prompt-contract bug: the extraction prompt used a hard-coded
example (W0-E0), which a small model could faithfully copy during preflight
instead of citing the evidence id actually present in the prompt.

v1.1 keeps the v1 experiment machinery but replaces that prompt with a
prompt-local evidence id and extends self-check so this regression cannot pass.
"""
from __future__ import annotations

import relational_emergence_v1 as base


def extract_prompt(shard, field):
    eligible = [e.id for e in shard if e.kind in {"SUPPORT", "CONTRADICT"}]
    example = eligible[0] if eligible else "<evidence-id-from-YOUR-EVIDENCE>"
    return f"""Extract explicit directed relational evidence for a governed field.
Read only YOUR EVIDENCE. Cite the exact evidence id shown in YOUR EVIDENCE for every explicit \"X leads to Y\" or \"X does not lead to Y\".
Do not invent evidence ids. Do not copy ids from examples unless that exact id appears in YOUR EVIDENCE.
Do not infer transitive edges. Do not cite side notes.
Return one line per selected item exactly as: USE <evidence-id>
For this prompt, a valid example is: USE {example}

YOUR EVIDENCE:
{base.shard_text(shard)}

CURRENT GOVERNED FIELD (read-only):
{base.field_text(field)}
"""


# Patch the module global used by preflight() and the experiment loop.
base.extract_prompt = extract_prompt

_original_selfcheck = base.selfcheck


def selfcheck():
    result = _original_selfcheck()
    probe = [base.E("PF-E0", "Archive: A leads to B.", "A", "B")]
    prompt = extract_prompt(probe, base.new_field())
    assert "USE PF-E0" in prompt
    assert "USE W0-E0" not in prompt
    result["prompt_contract"] = "PASS"
    return result


base.selfcheck = selfcheck


if __name__ == "__main__":
    raise SystemExit(base.main())
