from __future__ import annotations

import argparse
import json
from pathlib import Path

from .git_publish import publish
from .pipeline import SourcePolicy
from .runner import EvidenceStore, collect_once, watch


def load_policies(path: Path) -> list[SourcePolicy]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        SourcePolicy(
            source_id=item["source_id"],
            feed_url=item["feed_url"],
            allowed_domains=tuple(item["allowed_domains"]),
            trust=item.get("trust", "authoritative"),
        )
        for item in raw["sources"]
        if item.get("enabled", True)
    ]


def _print_result(result) -> None:
    print(json.dumps({
        "accepted": result.accepted,
        "duplicates": result.duplicates,
        "dropped": result.dropped,
        "errors": result.errors,
        "written": [str(p) for p in result.written],
    }, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(prog="heimel-research-intelligence")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--store", type=Path, default=Path("research/evidence"))
    parser.add_argument("--threshold", type=int, default=12)

    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    collect.add_argument("--git-commit", action="store_true")
    collect.add_argument("--git-push", action="store_true")

    watcher = sub.add_parser("watch")
    watcher.add_argument("--interval-seconds", type=int, default=3600)
    watcher.add_argument("--git-commit", action="store_true")
    watcher.add_argument("--git-push", action="store_true")

    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    store_path = args.store if args.store.is_absolute() else repo_root / args.store
    store = EvidenceStore(store_path)
    policies = load_policies(args.config)

    def finish(result) -> None:
        _print_result(result)
        if args.git_commit or args.git_push:
            paths = list(result.written)
            if result.written:
                paths.append(store.index_path)
            sha = publish(repo_root, paths, push=args.git_push)
            if sha:
                print(json.dumps({"git_commit": sha}, sort_keys=True))

    if args.command == "collect":
        result = collect_once(policies, store, threshold=args.threshold)
        finish(result)
        return 0

    watch(
        policies,
        store,
        threshold=args.threshold,
        interval_seconds=args.interval_seconds,
        on_run=finish,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
