#!/usr/bin/env python3
"""
Verify a VALO WORM audit log artifact.

The log is expected to contain chained entries in the format produced by
`l2-orchestrator/src/worm_log.py`. This CLI prints a short summary and exits
non-zero when the chain is missing or tampered with.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
L2_ROOT = ROOT / "l2-orchestrator"
if str(L2_ROOT) not in sys.path:
    sys.path.insert(0, str(L2_ROOT))

from src.worm_log import WORMAuditLog  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a VALO WORM audit log artifact")
    parser.add_argument("--input", required=True, type=Path, help="Path to the WORM log file")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only return an exit code; suppress human-readable output",
    )
    args = parser.parse_args()

    try:
        verifier = WORMAuditLog(log_dir=str(args.input.parent))
        integrity = verifier.verify_integrity(str(args.input))
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        if not args.quiet:
            print(f"ERROR: {exc}")
        return 2

    if not args.quiet:
        print(f"integrity: {integrity}")
        print(f"input: {args.input}")

    return 0 if integrity else 1


if __name__ == "__main__":
    raise SystemExit(main())
