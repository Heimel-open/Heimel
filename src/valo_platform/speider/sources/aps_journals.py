"""Official APS Journals source adapter for Speider.

Speider collects publisher metadata and provenance only. Scientific claims are
not evaluated here, and no article content is fetched unless a separate access
check establishes open-access or licensed use.
"""

from __future__ import annotations

import hashlib
from typing import Callable, Dict, List, Optional

from src.valo_platform.research_intake.discovery_record import DiscoveryRecord
from src.valo_platform.research_intake.source_manifest import (
    APS_JOURNALS_DEFAULT_MANIFESTS,
    ResearchSourceManifest,
    SnapshotStore,
    SourceSnapshot,
)

from ..parsers import aps_rss

PARSER_DISPATCH: Dict[
    str, Callable[[SourceSnapshot, ResearchSourceManifest], List[DiscoveryRecord]]
] = {
    "valo_platform.speider.parsers.aps_rss": aps_rss.parse,
}


class ApsJournalsSource:
    """Adapter over approved official APS journal feeds.

    ``fetcher`` is injected (callable URL -> text) so retrieval can run through
    the governed network boundary and remain fully testable offline.
    """

    def __init__(
        self,
        fetcher: Callable[[str], str],
        manifests: Optional[List[ResearchSourceManifest]] = None,
        snapshot_store: Optional[SnapshotStore] = None,
    ) -> None:
        self._fetch = fetcher
        self.manifests = list(manifests or APS_JOURNALS_DEFAULT_MANIFESTS)
        self.snapshots = snapshot_store or SnapshotStore()
        self._last_digest: Dict[str, str] = {}

    def collect(self, manifest: ResearchSourceManifest) -> List[DiscoveryRecord]:
        """Fetch, snapshot and normalize one feed.

        Unchanged feed content is skipped. Unknown parsers and disabled sources
        fail closed by returning no records.
        """
        if not manifest.enabled:
            return []

        content = self._fetch(manifest.url)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if self._last_digest.get(manifest.source_id) == digest:
            return []
        self._last_digest[manifest.source_id] = digest

        snapshot = self.snapshots.capture(
            manifest.source_id,
            content,
            publisher="American Physical Society",
            ingestion_scope="metadata_only",
        )
        parser = PARSER_DISPATCH.get(manifest.parser)
        if parser is None:
            return []
        return parser(snapshot, manifest)

    def collect_all(self) -> List[DiscoveryRecord]:
        records: List[DiscoveryRecord] = []
        for manifest in self.manifests:
            records.extend(self.collect(manifest))
        return records
