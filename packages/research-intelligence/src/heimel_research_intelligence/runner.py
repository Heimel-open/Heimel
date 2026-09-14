from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Callable
import json

from .pipeline import EvidenceRecord, Fetch, SourcePolicy, default_fetch, ingest, parse_feed


@dataclass(frozen=True)
class RunResult:
    accepted: int
    duplicates: int
    dropped: int
    errors: int
    written: tuple[Path, ...]


class EvidenceStore:
    def __init__(self, root: Path):
        self.root = root
        self.records_dir = root / "records"
        self.index_path = root / "index.json"

    def _index(self) -> dict:
        if not self.index_path.exists():
            return {"schema_version": "heimel.research.index.v1", "by_hash": {}, "by_url": {}}
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "heimel.research.index.v1":
            raise ValueError("unsupported research evidence index schema")
        return data

    @staticmethod
    def _digest_id(record: EvidenceRecord) -> str:
        return record.content_sha256.removeprefix("sha256:")

    def add(self, record: EvidenceRecord) -> tuple[bool, Path | None]:
        if record.disposition != "ACCEPT":
            return False, None
        index = self._index()
        digest = self._digest_id(record)
        if digest in index["by_hash"] or record.canonical_url in index["by_url"]:
            return False, None

        self.records_dir.mkdir(parents=True, exist_ok=True)
        path = self.records_dir / f"{digest}.json"
        payload = json.loads(record.to_json())
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        rel = path.relative_to(self.root).as_posix()
        index["by_hash"][digest] = rel
        index["by_url"][record.canonical_url] = digest
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.index_path)
        return True, path


def collect_once(
    policies: list[SourcePolicy],
    store: EvidenceStore,
    *,
    threshold: int = 12,
    fetch: Fetch = default_fetch,
) -> RunResult:
    accepted = duplicates = dropped = errors = 0
    written: list[Path] = []

    for policy in policies:
        try:
            feed, _, final_feed_url = fetch(policy.feed_url)
            if final_feed_url:
                candidates = parse_feed(feed, policy.source_id)
            else:
                candidates = []
        except Exception:
            errors += 1
            continue

        for candidate in candidates:
            try:
                record = ingest(candidate, policy, fetch=fetch, threshold=threshold)
            except Exception:
                errors += 1
                continue
            if record.disposition != "ACCEPT":
                dropped += 1
                continue
            added, path = store.add(record)
            if not added:
                duplicates += 1
                continue
            accepted += 1
            if path is not None:
                written.append(path)

    return RunResult(accepted, duplicates, dropped, errors, tuple(written))


def watch(
    policies: list[SourcePolicy],
    store: EvidenceStore,
    *,
    threshold: int = 12,
    interval_seconds: int = 3600,
    fetch: Fetch = default_fetch,
    on_run: Callable[[RunResult], None] | None = None,
) -> None:
    if interval_seconds < 60:
        raise ValueError("interval_seconds must be >= 60")
    while True:
        result = collect_once(policies, store, threshold=threshold, fetch=fetch)
        if on_run is not None:
            on_run(result)
        sleep(interval_seconds)
