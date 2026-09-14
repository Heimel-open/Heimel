from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _fail(message: str, code: int = 2) -> int:
    print(json.dumps({"ok": False, "error": message}, sort_keys=True), file=sys.stderr)
    return code


def _run_json(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        raise RuntimeError(detail)
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Heimel gateway returned non-JSON output") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Heimel gateway returned an unexpected payload")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail-closed Heimel preflight for agent consequence-bearing actions."
    )
    parser.add_argument("--profile", type=Path, default=os.getenv("HEIMEL_PROFILE"))
    parser.add_argument("--runtime-id", default=os.getenv("HEIMEL_RUNTIME_ID"))
    parser.add_argument("--environment", choices=("sandbox", "live"), default="live")
    parser.add_argument("--ttl-seconds", type=int, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.profile is None:
        return _fail("missing governed profile: set HEIMEL_PROFILE or pass --profile")
    if not args.runtime_id:
        return _fail("missing runtime id: set HEIMEL_RUNTIME_ID or pass --runtime-id")
    if args.ttl_seconds <= 0:
        return _fail("ttl must be positive")
    if not args.profile.is_file():
        return _fail(f"governed profile not found: {args.profile}")

    gateway = shutil.which("valo-gateway")
    if gateway is None:
        return _fail("valo-gateway is unavailable; consequence execution must remain blocked")

    try:
        validation = _run_json([gateway, "profile", "validate", str(args.profile)])
        compiled = _run_json(
            [
                gateway,
                "profile",
                "compile",
                str(args.profile),
                "--runtime-id",
                args.runtime_id,
                "--environment",
                args.environment,
            ]
        )
        session = _run_json(
            [
                gateway,
                "profile",
                "session-descriptor",
                str(args.profile),
                "--runtime-id",
                args.runtime_id,
                "--environment",
                args.environment,
                "--ttl-seconds",
                str(args.ttl_seconds),
            ]
        )
    except RuntimeError as exc:
        return _fail(f"Heimel preflight failed closed: {exc}")

    result = {
        "ok": True,
        "boundary": "HEIMEL",
        "authorization_boundary": validation.get("authorization_boundary", "REHT"),
        "profile_id": validation.get("profile_id"),
        "profile_digest": validation.get("profile_digest"),
        "runtime_id": args.runtime_id,
        "environment": args.environment,
        "compiled_profile": compiled,
        "session_descriptor": session,
        "effect_authorized": False,
        "effect_executed": False,
        "next": "invoke the Heimel-governed effect path; direct execution remains prohibited",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
