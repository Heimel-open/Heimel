#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence


SERVER_START_TIMEOUT_SECONDS = 0.5
TGREP_NO_MATCH = 1


def _run(command: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def _debug(message: str) -> None:
    if os.getenv("HEIMEL_SEARCH_DEBUG") == "1":
        print(f"heimel-search: {message}", file=sys.stderr)


def _repo_root() -> Path:
    proc = _run(["git", "rev-parse", "--show-toplevel"], capture=True)
    if proc.returncode != 0:
        raise RuntimeError("not inside a git repository")
    return Path(proc.stdout.strip()).resolve()


def _index_path(root: Path) -> Path:
    proc = _run(["git", "rev-parse", "--git-dir"], capture=True)
    if proc.returncode != 0:
        return root / ".git" / "heimel-tgrep-index"
    git_dir = Path(proc.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = root / git_dir
    return git_dir.resolve() / "heimel-tgrep-index"


def _rg_command(
    query: str,
    path: str,
    *,
    regex: bool,
    hidden: bool,
    globs: Sequence[str],
    rg_args: Sequence[str],
) -> list[str]:
    command = ["rg", "--no-heading", "--color", "never"]
    if not regex:
        command.append("-F")
    if hidden:
        command.append("--hidden")
    for pattern in globs:
        command.extend(["--glob", pattern])
    command.extend(rg_args)
    command.extend([query, path])
    return command


def _tgrep_command(query: str, path: str, index: Path) -> list[str]:
    return ["tgrep", "-F", "--index-path", str(index), "--", query, path]


def _ensure_index(root: Path, index: Path) -> bool:
    if index.exists():
        return True
    proc = _run(["tgrep", "index", str(root), "--index-path", str(index)], capture=True)
    if proc.returncode != 0:
        _debug("tgrep index unavailable; falling back to rg")
        return False
    return True


def _server_ready(root: Path, index: Path) -> bool:
    status = _run(
        ["tgrep", "status", str(root), "--index-path", str(index)],
        capture=True,
    )
    if status.returncode == 0:
        return True

    try:
        subprocess.Popen(
            ["tgrep", "serve", str(root), "--index-path", str(index)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False

    deadline = time.monotonic() + SERVER_START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        status = _run(
            ["tgrep", "status", str(root), "--index-path", str(index)],
            capture=True,
        )
        if status.returncode == 0:
            return True
        time.sleep(0.02)
    return False


def should_use_tgrep(
    *,
    broad: bool,
    regex: bool,
    force_rg: bool,
    hidden: bool,
    globs: Sequence[str],
    rg_args: Sequence[str],
) -> bool:
    return not (broad or regex or force_rg or hidden or globs or rg_args)


def search(
    query: str,
    path: str = ".",
    *,
    broad: bool = False,
    regex: bool = False,
    force_rg: bool = False,
    hidden: bool = False,
    globs: Sequence[str] = (),
    rg_args: Sequence[str] = (),
) -> int:
    rg = shutil.which("rg")
    if rg is None:
        print("heimel-search: ripgrep (rg) is required", file=sys.stderr)
        return 127

    use_tgrep = should_use_tgrep(
        broad=broad,
        regex=regex,
        force_rg=force_rg,
        hidden=hidden,
        globs=globs,
        rg_args=rg_args,
    )
    tgrep = shutil.which("tgrep") if use_tgrep else None

    if tgrep is not None:
        try:
            root = _repo_root()
            index = _index_path(root)
            if _ensure_index(root, index):
                # Server mode is an acceleration only. Disk-indexed tgrep remains valid
                # if the watcher/server cannot be started in the current environment.
                _server_ready(root, index)
                proc = _run(_tgrep_command(query, path, index))
                if proc.returncode in (0, TGREP_NO_MATCH):
                    return proc.returncode
                _debug(f"tgrep exited {proc.returncode}; falling back to rg")
        except (OSError, RuntimeError) as exc:
            _debug(f"tgrep unavailable ({exc}); falling back to rg")

    proc = _run(
        _rg_command(
            query,
            path,
            regex=regex,
            hidden=hidden,
            globs=globs,
            rg_args=rg_args,
        )
    )
    return proc.returncode


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Heimel coding search: tgrep for precise fixed-string lookups; "
            "ripgrep for broad, regex, filtered, or fallback searches."
        )
    )
    parser.add_argument("query")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--broad", action="store_true", help="route a high-frequency/broad query to rg")
    parser.add_argument("--regex", action="store_true", help="interpret query as regex and route to rg")
    parser.add_argument("--rg", dest="force_rg", action="store_true", help="force rg")
    parser.add_argument("--hidden", action="store_true", help="include hidden files via rg")
    parser.add_argument("--glob", action="append", default=[], help="rg glob; may be repeated")
    parser.add_argument(
        "--rg-arg",
        action="append",
        default=[],
        help="additional rg argument; use --rg-arg=VALUE for values beginning with '-'",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return search(
        args.query,
        args.path,
        broad=args.broad,
        regex=args.regex,
        force_rg=args.force_rg,
        hidden=args.hidden,
        globs=args.glob,
        rg_args=args.rg_arg,
    )


if __name__ == "__main__":
    raise SystemExit(main())
