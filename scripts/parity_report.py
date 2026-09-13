"""Summarize a VALO parity report artifact.

The report is produced by ``simulate.py --mode parity --report-json=...``.
This CLI reads the JSON artifact, prints a short summary, and exits non-zero
when the legacy telemetry path and permit shadow path are not aligned.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_report(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    report = json.loads(text)
    if not isinstance(report, dict):
        raise ValueError("report must be a JSON object")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a VALO parity report artifact")
    parser.add_argument("--input", required=True, type=Path, help="Path to parity report JSON")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only return an exit code; suppress human-readable output",
    )
    args = parser.parse_args()

    try:
        report = _load_report(args.input)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        if not args.quiet:
            print(f"ERROR: {exc}")
        return 2

    legacy = report.get("legacy_telemetry", {})
    shadow = report.get("permit_shadow", {})
    aligned = bool(report.get("aligned"))

    if not args.quiet:
        print(f"legacy_telemetry: passed={bool(legacy.get('passed'))} checks={legacy.get('checks')}")
        print(f"permit_shadow: passed={bool(shadow.get('passed'))} checks={shadow.get('checks')}")
        print(f"aligned: {aligned}")

    return 0 if aligned else 1


if __name__ == "__main__":
    raise SystemExit(main())
