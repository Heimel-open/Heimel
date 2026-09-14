from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import SourcePolicy, default_fetch, deduplicate, ingest, parse_feed


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


def run(config: Path, output: Path, threshold: int) -> int:
    records = []
    for policy in load_policies(config):
        try:
            feed, _, _ = default_fetch(policy.feed_url)
            candidates = parse_feed(feed, policy.source_id)
        except Exception as exc:
            records.append({"source_id": policy.source_id, "candidate_url": policy.feed_url, "disposition": "SOURCE_ERROR", "error": str(exc)})
            continue
        for candidate in candidates:
            try:
                records.append(ingest(candidate, policy, threshold=threshold))
            except Exception as exc:
                records.append({"source_id": policy.source_id, "candidate_url": candidate.url, "disposition": "ERROR", "error": str(exc)})
    normalized = []
    evidence = deduplicate(r for r in records if not isinstance(r, dict))
    normalized.extend(json.loads(r.to_json()) for r in evidence)
    normalized.extend(r for r in records if isinstance(r, dict))
    normalized.sort(key=lambda r: (r.get("disposition", ""), r.get("source_id", ""), r.get("canonical_url", r.get("candidate_url", ""))))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"records": normalized}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="heimel-research-intelligence")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=int, default=12)
    args = parser.parse_args()
    return run(args.config, args.output, args.threshold)


if __name__ == "__main__":
    raise SystemExit(main())
