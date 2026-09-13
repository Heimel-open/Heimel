"""Validate VALO V5 Core repository structure.

This script is intentionally conservative. It does not execute runtime code and
it does not modify protected L1/formal-verification assets.
"""

from __future__ import annotations

from pathlib import Path


REQUIRED_FILES = [
    "README.md",
    "context.md",
    "docs/PRODUCT_MODES.md",
    "docs/ARCHITECTURE.md",
    "docs/architecture/PRE_INTENT_GOVERNANCE_ALIGNMENT.md",
]

REQUIRED_TEXT = {
    # The project was rebranded VALO V5 Core -> REHT V5 Core; accept the
    # current branding.
    "README.md": [
        "REHT V5 Core",
        "Protected Boundary",
        "Do not change l1-guardian/src/validation_logic.rs",
    ],
    "context.md": [
        "READ -> TRACE -> EXPLAIN -> PLAN -> PATCH -> TEST -> HANDOFF",
        "Do not modify frozen L1 logic casually",
        "docs/analysis/ai_handoff_YYYY-MM-DD.md",
    ],
    "docs/PRODUCT_MODES.md": [
        "Sidecar, MCP, HTTP Proxy and Wrapper are not duplicates",
        "same governance input -> same governance decision",
    ],
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    for rel_path in REQUIRED_FILES:
        path = root / rel_path
        if not path.exists():
            errors.append(f"missing required file: {rel_path}")
            continue
        if path.is_file() and path.stat().st_size == 0:
            errors.append(f"empty required file: {rel_path}")

    for rel_path, needles in REQUIRED_TEXT.items():
        path = root / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel_path} missing required text: {needle}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("VALO V5 Core repository structure OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
