"""DAIR.AI Speider source adapter (discovery-only).

Speider collects and normalizes. It does not evaluate, decide adoption, or
grant any authority. Fetched content is treated as inert data: instructions
embedded in pages are stored as content, never executed.
"""

from __future__ import annotations

import hashlib
from typing import Callable, Dict, List, Optional

from src.valo_platform.research_intake.discovery_record import DiscoveryRecord
from src.valo_platform.research_intake.source_manifest import (
    DAIR_AI_DEFAULT_MANIFESTS,
    ResearchSourceManifest,
    SnapshotStore,
    SourceSnapshot,
)

from ..parsers import dair_plugins, dair_prompt_guide, dair_weekly

PARSER_DISPATCH: Dict[str, Callable[[SourceSnapshot, ResearchSourceManifest], List[DiscoveryRecord]]] = {
    "valo_platform.speider.parsers.dair_weekly": dair_weekly.parse,
    "valo_platform.speider.parsers.dair_prompt_guide": dair_prompt_guide.parse,
    "valo_platform.speider.parsers.dair_plugins": dair_plugins.parse,
}


class DairAiSource:
    """Adapter over the DAIR.AI source endpoints.

    ``fetcher`` is injected (callable url -> text) so collection can run
    through governed retrieval and be fully testable offline.
    """

    def __init__(
        self,
        fetcher: Callable[[str], str],
        manifests: Optional[List[ResearchSourceManifest]] = None,
        snapshot_store: Optional[SnapshotStore] = None,
    ) -> None:
        self._fetch = fetcher
        self.manifests = list(manifests or DAIR_AI_DEFAULT_MANIFESTS)
        self.snapshots = snapshot_store or SnapshotStore()
        self._last_digest: Dict[str, str] = {}

    def collect(self, manifest: ResearchSourceManifest) -> List[DiscoveryRecord]:
        """Fetch, snapshot and normalize one source. Unchanged content
        (same digest) is skipped to avoid repeated processing."""
        if not manifest.enabled:
            return []
        content = self._fetch(manifest.url)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if self._last_digest.get(manifest.source_id) == digest:
            return []
        self._last_digest[manifest.source_id] = digest
        snapshot = self.snapshots.capture(manifest.source_id, content)
        parser = PARSER_DISPATCH.get(manifest.parser)
        if parser is None:
            return []
        return parser(snapshot, manifest)

    def collect_all(self) -> List[DiscoveryRecord]:
        records: List[DiscoveryRecord] = []
        for manifest in self.manifests:
            records.extend(self.collect(manifest))
        return records
