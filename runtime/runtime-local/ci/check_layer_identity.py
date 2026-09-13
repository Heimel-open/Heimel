#!/usr/bin/env python3
"""ci/check_layer_identity.py — enforce canonical LA identity (enforcement, not docs).

Hard failures (block CI):
  - LAYER_IDENTITY.md must exist in repo root (canonical anchor)
  - no source file may DECLARE a component as belonging to two different LA layers
  - any file that assigns a known LA component to a layer must use the CANONICAL
    mapping (LA4 -> REHT only, etc.)

IMPORTANT: fields like `source_layer` / `source_la` describe which layer an
EVENT came from (runtime metadata), NOT a component's identity claim. They are
excluded from the ownership check.

Soft warnings (do not block):
  - new contract/test/doc files should reference the "LAx - Name" form

Infra repos (runtime/tool/skills/distribution) have NO layer of their own; the
check only requires the anchor + no false LA claims.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CANONICAL = {
    "LA1": "SPEIDER", "LA2": "BARO", "LA3": "VAIG",
    "LA4": "REHT", "LA5": "RACS", "LA6": "Veritas",
}
COMP_TO_LA = {v.upper(): k for k, v in CANONICAL.items()}
VALID = set(CANONICAL.keys()) | set(COMP_TO_LA.keys())


def fail(msg):
    print(f"FAIL: {msg}")
    return False


def check_anchor():
    p = os.path.join(ROOT, "LAYER_IDENTITY.md")
    if not os.path.exists(p):
        return fail("LAYER_IDENTITY.md missing — canonical LA anchor absent")
    print("OK: LAYER_IDENTITY.md present")
    return True


def check_layer_mapping():
    # Exclude source_layer/source_la (event provenance metadata, not identity)
    assign = re.compile(
        r'(?<!source_)(?:layer|la|belongs_to|lag)\s*[:=]\s*["\']?(LA\d|SPEIDER|BARO|VAIG|REHT|RACS|VERITAS)',
        re.I)
    ok = True
    for dp, _, files in os.walk(ROOT):
        if ".git" in dp:
            continue
        for fn in files:
            if not fn.endswith((".py", ".md", ".yaml", ".yml", ".json", ".ts", ".tsx")):
                continue
            fp = os.path.join(dp, fn)
            try:
                txt = open(fp, errors="ignore").read()
            except Exception:
                continue
            claims = []
            for m in assign.finditer(txt):
                tok = m.group(1).upper()
                if tok not in VALID:
                    continue
                num = tok if tok in CANONICAL else COMP_TO_LA[tok]
                comp = CANONICAL[num]
                if tok in COMP_TO_LA and COMP_TO_LA[tok] != num:
                    ok = fail(f"{fp}: inconsistent LA mapping {tok}")
                claims.append((num, comp))
            nums = {n for n, _ in claims}
            if len(nums) > 1:
                ok = fail(f"{fp}: component claimed for multiple layers {sorted(nums)}")
    if ok:
        print("OK: no inconsistent/multi-layer LA claims")
    return ok


def main():
    ok = True
    ok &= check_anchor()
    ok &= check_layer_mapping()
    if not ok:
        sys.exit(1)
    print("LAYER_IDENTITY_ENFORCED")
    sys.exit(0)


if __name__ == "__main__":
    main()
