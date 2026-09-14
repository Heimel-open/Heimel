#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "PUBLIC_BOUNDARY.json"


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def load_policy() -> dict:
    with POLICY_PATH.open("r", encoding="utf-8") as fh:
        policy = json.load(fh)
    if policy.get("mode") != "fail_closed":
        raise RuntimeError("PUBLIC_BOUNDARY.json must remain fail_closed")
    return policy


def tracked_files() -> set[str]:
    return {p for p in git("ls-files", "-z").split("\0") if p}


def changed_files(base: str | None, head: str) -> set[str]:
    if not base or set(base) == {"0"}:
        return tracked_files()
    try:
        out = git("diff", "--name-only", "--diff-filter=ACMR", "-z", base, head)
    except RuntimeError:
        return tracked_files()
    return {p for p in out.split("\0") if p}


def path_violations(paths: set[str], policy: dict) -> list[str]:
    blocked_segments = {s.casefold() for s in policy["forbidden_path_segments"]}
    blocked_fragments = [s.casefold() for s in policy["forbidden_filename_fragments"]]
    violations = []
    for raw in sorted(paths):
        p = PurePosixPath(raw)
        parts = [part.casefold() for part in p.parts]
        filename = p.name.casefold()
        hit_segments = sorted(blocked_segments.intersection(parts))
        hit_fragments = [frag for frag in blocked_fragments if frag in filename]
        if hit_segments or hit_fragments:
            reason = ", ".join(hit_segments + hit_fragments)
            violations.append(f"PATH {raw}: forbidden private/public-boundary marker ({reason})")
    return violations


def is_probably_text(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def content_violations(paths: set[str], policy: dict) -> list[str]:
    markers = policy["forbidden_content_markers"]
    exempt = set(policy.get("content_scan_exempt_paths", []))
    violations = []
    for raw in sorted(paths - exempt):
        path = ROOT / raw
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            violations.append(f"READ {raw}: cannot inspect file ({exc})")
            continue
        if not is_probably_text(data):
            continue
        text = data.decode("utf-8")
        for marker in markers:
            if marker in text:
                violations.append(f"CONTENT {raw}: contains forbidden marker {marker}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail closed when private material crosses the Heimel public boundary.")
    parser.add_argument("--base", default=None)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()

    try:
        policy = load_policy()
        tracked = tracked_files()
        changed = changed_files(args.base, args.head).intersection(tracked)
        violations = path_violations(tracked, policy)
        violations.extend(content_violations(changed, policy))
    except Exception as exc:
        print(f"PUBLIC BOUNDARY: FAIL CLOSED: {exc}", file=sys.stderr)
        return 2

    if violations:
        print("PUBLIC BOUNDARY: BLOCKED", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print("Move private/research/internal material outside this public repository. Do not bypass the gate.", file=sys.stderr)
        return 1

    print(f"PUBLIC BOUNDARY: PASS ({len(tracked)} tracked paths; {len(changed)} changed files inspected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
