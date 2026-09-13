from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _run(command: list[str], cwd: Path) -> dict[str, object]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/causal-effect-boundary-v1-result.json")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    checks: list[dict[str, object]] = []

    checks.append(
        _run(
            [sys.executable, "-m", "pytest", "-q", "tests/test_causal_effect_boundary.py"],
            root,
        )
    )
    checks.append(
        _run(
            [sys.executable, "-m", "compileall", "-q", "src", "tests", "examples"],
            root,
        )
    )
    if args.full:
        checks.append(_run([sys.executable, "-m", "pytest", "-q"], root))

    passed = all(check["returncode"] == 0 for check in checks)
    result = {
        "schema_version": "causal_effect_boundary_run.v1",
        "run_id": "CAUSAL-EFFECT-BOUNDARY-01",
        "execution": "LOCAL_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": "nsolland/valo-kernel",
        "required_source_files": {
            "src/valo_kernel/effect_boundary.py": _digest(root / "src/valo_kernel/effect_boundary.py"),
            "tests/test_causal_effect_boundary.py": _digest(root / "tests/test_causal_effect_boundary.py"),
            "docs/effect_boundary_conformance_v1.md": _digest(root / "docs/effect_boundary_conformance_v1.md"),
        },
        "full_regression_requested": bool(args.full),
        "checks": checks,
        "status": "PASS" if passed else "FAIL",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    print(result["status"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
