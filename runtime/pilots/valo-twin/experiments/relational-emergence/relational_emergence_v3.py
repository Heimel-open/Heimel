#!/usr/bin/env python3
"""TOFOO relational emergence v3 runner.

Single compatibility layer over the v2 core. v3 patches the core module
*directly*, so core.main() sees the corrected functions in its own global
namespace.

Validity rules added here:
- preflight checks execution/output contracts only;
- HYP/RULE parsing is position-anchored (identifiers inside evidence ids cannot
  be mistaken for operators or rules);
- malformed extra tokens are rejected instead of heuristically recovered;
- every RELATIONAL_ADAPTIVE call must produce at least one structurally valid
  hypothesis, otherwise the run is TEST_INVALID_RELATIONAL_INTERFACE;
- the emitted manifest records the runtime package/GPU fingerprint.
"""
from __future__ import annotations

import json
import platform
import re
import sys
from pathlib import Path

import relational_emergence_v2_core as core


_HYP_RE = re.compile(
    r"^\s*HYP\s+([A-Z][A-Z0-9_]*)\s+\[?([A-Z][A-Z0-9_]*)\]?\s+\[?([A-Z0-9_-]+)\]?\s*$",
    re.IGNORECASE,
)
_RULE_RE = re.compile(
    r"^\s*RULE\s+([A-Z][A-Z0-9_]*)\s+\[?([A-Z][A-Z0-9_]*)\]?\s*$",
    re.IGNORECASE,
)


def parse_hypotheses(raw: str, shard, operators):
    """Parse only explicit `HYP <operator> <rule> <evidence-id>` records.

    Crucially, operator/rule discovery is anchored to token positions. An
    evidence id such as W0-KEM-P0 cannot manufacture an apparent KEM operator.
    Semantic compatibility remains the deterministic admission gate's job.
    """
    ops = {str(x).upper() for x in operators}
    rules = {str(x).upper() for x in core.RULES}
    eids = {e.eid.upper(): e.eid for e in shard}
    parsed = []
    for line in raw.splitlines():
        m = _HYP_RE.match(line)
        if not m:
            continue
        op, rule, eid_token = (x.upper() for x in m.groups())
        if op not in ops or rule not in rules or eid_token not in eids:
            continue
        item = (op, rule, eids[eid_token])
        if item not in parsed:
            parsed.append(item)
    return parsed


def parse_rules(raw: str, operators):
    """Parse only explicit `RULE <operator> <rule>` records."""
    ops = {str(x).upper() for x in operators}
    rules = {str(x).upper() for x in core.RULES}
    result = {}
    for line in raw.splitlines():
        m = _RULE_RE.match(line)
        if not m:
            continue
        op, rule = (x.upper() for x in m.groups())
        if op in ops and rule in rules and op not in result:
            result[op] = rule
    return result


def model_preflight(runner: core.Runner, model_id: str) -> dict:
    """Check model execution + parseable HYP/RULE interfaces only."""
    if runner.mock:
        return {"status": "PASS", "mode": "MOCK", "scope": "INTERFACE_ONLY"}

    evidence = core.Evidence(
        "PF-KEM-P0",
        "KEM",
        "ABCDE",
        core.apply_rule("ABCDE", "REVERSE"),
        0,
    )

    hyp_prompt = """INTERFACE CHECK ONLY. Do not solve anything.
Copy the verified record exactly once.

HYP KEM REVERSE PF-KEM-P0
"""
    hyp_raw = runner.run(hyp_prompt, model_id, 24)
    hyp_parsed = parse_hypotheses(hyp_raw, [evidence], ["KEM"])
    expected_hyp = ("KEM", "REVERSE", "PF-KEM-P0")
    if expected_hyp not in hyp_parsed:
        raise RuntimeError(
            "MODEL_PREFLIGHT_FAILED hypothesis output contract: " + repr(hyp_raw[:300])
        )

    rule_prompt = """INTERFACE CHECK ONLY. Do not solve anything.
Copy the verified record exactly once.

RULE KEM REVERSE
"""
    rule_raw = runner.run(rule_prompt, model_id, 16)
    rule_parsed = parse_rules(rule_raw, ["KEM"])
    if rule_parsed.get("KEM") != "REVERSE":
        raise RuntimeError(
            "MODEL_PREFLIGHT_FAILED direct output contract: " + repr(rule_raw[:300])
        )

    return {
        "status": "PASS",
        "scope": "INTERFACE_ONLY",
        "hypothesis_raw": hyp_raw[:300],
        "direct_raw": rule_raw[:300],
    }


# Patch parser + preflight into the module whose main() actually executes.
core.parse_hypotheses = parse_hypotheses
core.parse_rules = parse_rules
core.model_preflight = model_preflight

_original_selfcheck = core.selfcheck


def selfcheck() -> dict:
    result = _original_selfcheck()

    # Regression: never infer operator KEM merely because it occurs inside eid.
    probe = [core.Evidence("W0-KEM-P0", "KEM", "ABCDE", "BACDE", 0)]
    assert parse_hypotheses(
        "HYP PAIRSWAP PAIRSWAP [W0-KEM-P0]", probe, ["KEM"]
    ) == []
    assert parse_hypotheses(
        "HYP KEM PAIRSWAP [W0-KEM-P0]", probe, ["KEM"]
    ) == [("KEM", "PAIRSWAP", "W0-KEM-P0")]

    # Regression: ambiguous/multi-rule lines are rejected, not guessed.
    assert parse_rules("RULE KEM ROTL1 PAIRSWAP", ["KEM"]) == {}
    assert parse_rules("RULE KEM [EVENS_FIRST]", ["KEM"]) == {"KEM": "EVENS_FIRST"}

    result["preflight_scope"] = "INTERFACE_ONLY"
    result["capability_not_instrument_validity"] = "PASS"
    result["runner_binding"] = "CORE_PATCHED_DIRECTLY"
    result["parser_anchor_contract"] = "PASS"
    result["no_operator_from_evidence_id"] = "PASS"
    result["no_heuristic_extra_token_recovery"] = "PASS"
    return result


core.selfcheck = selfcheck


def _out_path() -> Path:
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        if i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])
    return Path("/content/tofoo_relational_results_v2")


def _environment_fingerprint() -> dict:
    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import torch
        env.update(
            torch=torch.__version__,
            cuda=torch.version.cuda,
            gpu=(torch.cuda.get_device_name(0) if torch.cuda.is_available() else None),
        )
    except Exception as exc:
        env["torch_error"] = repr(exc)
    try:
        import transformers
        env["transformers"] = transformers.__version__
    except Exception as exc:
        env["transformers_error"] = repr(exc)
    try:
        import bitsandbytes as bnb
        env["bitsandbytes"] = getattr(bnb, "__version__", "UNKNOWN")
    except Exception as exc:
        env["bitsandbytes_error"] = repr(exc)
    return env


def _post_validate(out: Path) -> int:
    manifest_path = out / "manifest.json"
    raw_path = out / "raw_calls.json"
    if not manifest_path.exists() or not raw_path.exists():
        return 0

    manifest = json.loads(manifest_path.read_text())
    raw_calls = json.loads(raw_path.read_text())
    relational = [x for x in raw_calls if x.get("condition") == "RELATIONAL_ADAPTIVE"]
    parsed_calls = sum(bool(x.get("parsed")) for x in relational)
    coverage = parsed_calls / len(relational) if relational else 0.0

    diagnostics = manifest.setdefault("diagnostics", {})
    diagnostics["relational_call_parse_coverage"] = coverage
    diagnostics["relational_calls"] = len(relational)
    diagnostics["relational_calls_with_valid_hypothesis"] = parsed_calls
    manifest["environment"] = _environment_fingerprint()

    if relational and coverage < 1.0:
        manifest["instrument_status"] = "TEST_INVALID_RELATIONAL_INTERFACE"
        manifest["interpretation"] = "DO_NOT_INTERPRET_AS_RESEARCH_RESULT"
        manifest["error"] = (
            "At least one RELATIONAL_ADAPTIVE model call produced no structurally valid "
            f"HYP record ({parsed_calls}/{len(relational)} calls valid)."
        )
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(json.dumps({
            "status": manifest["instrument_status"],
            "relational_call_parse_coverage": coverage,
            "error": manifest["error"],
        }, indent=2))
        return 4

    manifest_path.write_text(json.dumps(manifest, indent=2))
    return 0


def main() -> int:
    rc = core.main()
    if rc != 0 or "--self-test-only" in sys.argv:
        return rc
    return _post_validate(_out_path())


if __name__ == "__main__":
    raise SystemExit(main())
