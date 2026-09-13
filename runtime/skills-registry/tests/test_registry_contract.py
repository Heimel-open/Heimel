#!/usr/bin/env python3
"""tests/test_registry_contract.py

Verifies:
  1. All reference skills validate against schemas/skill.schema.json.
  2. Each skill references existing input/output schemas.
  3. The registry runtime code (cli/) contains NO eval/auth/exec logic.
     (Docs and this test may mention those terms; only executable catalog code is checked.)
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cli"))


def test_all_skills_validate():
    skills = glob.glob(os.path.join(ROOT, "skills", "**", "*.yaml"), recursive=True)
    assert skills, "no skills found"
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(ROOT, "cli/validate.py"), *skills],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    print(f"VALIDATED {len(skills)} skills")


def test_no_eval_auth_exec_in_catalog_code():
    """Only cli/ (executable catalog code) is checked — no reht/racs/veritas/execute."""
    banned = ["reht.decide", "racs.", "veritas.record", "def execute",
              "subprocess.run", "os.system", "authorize("]
    hits = []
    cli_dir = os.path.join(ROOT, "cli")
    for fn in os.listdir(cli_dir):
        if fn.endswith(".py"):
            p = os.path.join(cli_dir, fn)
            txt = open(p, errors="ignore").read().lower()
            for b in banned:
                if b.lower() in txt:
                    hits.append((p, b))
    assert not hits, f"catalog code contains authority/eval: {hits}"
    print("NO_EVAL_AUTH_EXEC_IN_CLI_OK")


if __name__ == "__main__":
    test_all_skills_validate()
    test_no_eval_auth_exec_in_catalog_code()
    print("ALL_SKILLS_REGISTRY_TESTS_PASS")
