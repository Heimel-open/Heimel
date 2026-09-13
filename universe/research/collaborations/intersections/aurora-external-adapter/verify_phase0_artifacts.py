from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

EXPECTED_WHEEL_SHA256 = "d078f5340c177a894cde2fdb4a317226cb1c4c03e6f55de3e5f9f5cbfe62a3c6"
EXPECTED_SUITE_SHA256 = "0702bfcfe0f53e2619acddaad2d4b3aa028afee4503aec1d0d15b0a4175187d0"
REQUIRED_PROXY_SYMBOL = "PUBLIC_DEMO_EDGE_PATHS"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wheel_contains_symbol(wheel: Path, symbol: str) -> bool:
    with zipfile.ZipFile(wheel) as zf:
        source = zf.read("aurora_lens/proxy/app.py").decode("utf-8", errors="replace")
    return symbol in source


def suite_requires_symbol(suite: Path, symbol: str) -> bool:
    with zipfile.ZipFile(suite) as zf:
        candidates = [n for n in zf.namelist() if n.endswith("tests/conftest.py") or n.endswith("conftest.py")]
        if not candidates:
            return False
        text = zf.read(candidates[0]).decode("utf-8", errors="replace")
    return symbol in text


def main() -> int:
    p = argparse.ArgumentParser(description="Verify transferred Aurora-Lens Phase 0 artifacts without unpacking proprietary source into the research repo.")
    p.add_argument("wheel", type=Path)
    p.add_argument("suite", type=Path)
    args = p.parse_args()

    wheel_hash = sha256(args.wheel)
    suite_hash = sha256(args.suite)
    print(f"wheel_sha256={wheel_hash}")
    print(f"suite_sha256={suite_hash}")
    print(f"wheel_hash_match={wheel_hash == EXPECTED_WHEEL_SHA256}")
    print(f"suite_hash_match={suite_hash == EXPECTED_SUITE_SHA256}")
    print(f"python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"python_3_12={sys.version_info[:2] == (3, 12)}")

    suite_requires = suite_requires_symbol(args.suite, REQUIRED_PROXY_SYMBOL)
    wheel_has = wheel_contains_symbol(args.wheel, REQUIRED_PROXY_SYMBOL)
    print(f"suite_requires_{REQUIRED_PROXY_SYMBOL}={suite_requires}")
    print(f"wheel_has_{REQUIRED_PROXY_SYMBOL}={wheel_has}")

    compatible = not suite_requires or wheel_has
    print(f"observable_suite_wheel_symbol_compatibility={compatible}")

    return 0 if (
        wheel_hash == EXPECTED_WHEEL_SHA256
        and suite_hash == EXPECTED_SUITE_SHA256
        and sys.version_info[:2] == (3, 12)
        and compatible
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
