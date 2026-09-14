from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://api.github.com"


def _get(path: str, token: str) -> Any:
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "heimel-traction-tracker",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _optional(path: str, token: str) -> tuple[Any | None, str | None]:
    try:
        return _get(path, token), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except OSError as exc:
        return None, exc.__class__.__name__


def collect(repo: str, token: str) -> dict[str, Any]:
    owner, name = repo.split("/", 1)
    repo_data = _get(f"/repos/{owner}/{name}", token)

    views, views_error = _optional(f"/repos/{owner}/{name}/traffic/views", token)
    clones, clones_error = _optional(f"/repos/{owner}/{name}/traffic/clones", token)
    referrers, referrers_error = _optional(f"/repos/{owner}/{name}/traffic/popular/referrers", token)
    paths, paths_error = _optional(f"/repos/{owner}/{name}/traffic/popular/paths", token)

    query = urllib.parse.quote(f"repo:{repo} is:open author:!{owner}")
    external_open, external_open_error = _optional(f"/search/issues?q={query}", token)

    traffic_errors = {
        key: value
        for key, value in {
            "views": views_error,
            "clones": clones_error,
            "referrers": referrers_error,
            "paths": paths_error,
        }.items()
        if value
    }

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "repository": repo,
        "stars": repo_data.get("stargazers_count", 0),
        "forks": repo_data.get("forks_count", 0),
        "watchers": repo_data.get("subscribers_count", 0),
        "open_issues_and_prs": repo_data.get("open_issues_count", 0),
        "views_14d": views,
        "clones_14d": clones,
        "top_referrers_14d": referrers,
        "top_paths_14d": paths,
        "external_open_items": None if external_open is None else external_open.get("total_count"),
        "external_open_items_error": external_open_error,
        "traffic_complete": not traffic_errors,
        "traffic_errors": traffic_errors,
    }


def append_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, sort_keys=True, separators=(",", ":")) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture permanent Heimel GitHub traction snapshots.")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "Heimel-open/Heimel"))
    parser.add_argument("--output", type=Path, default=Path("telemetry/repo_traction.jsonl"))
    args = parser.parse_args(argv)

    token = os.getenv("HEIMEL_TRAFFIC_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        print("missing HEIMEL_TRAFFIC_TOKEN/GH_TOKEN/GITHUB_TOKEN", file=sys.stderr)
        return 2

    try:
        snapshot = collect(args.repo, token)
    except (ValueError, urllib.error.HTTPError, OSError) as exc:
        print(f"traction collection failed: {exc}", file=sys.stderr)
        return 1

    append_snapshot(args.output, snapshot)
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
