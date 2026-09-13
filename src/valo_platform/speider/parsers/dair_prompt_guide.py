"""Parser for dair-ai/Prompt-Engineering-Guide pages.

Produces a single page-level DISCOVERY_SUMMARY record keyed on the page
revision (content digest). Learning/reference content — routes to
RehtLearn / research wiki after human disposition.
"""

from __future__ import annotations

from typing import List

from src.valo_platform.research_intake.discovery_record import (
    DiscoveryRecord,
    SourceIdentity,
    TrustClass,
)
from src.valo_platform.research_intake.source_manifest import (
    ResearchSourceManifest,
    SourceSnapshot,
)

PARSER_VERSION = "dair_prompt_guide/1.0.0"


def parse(
    snapshot: SourceSnapshot, manifest: ResearchSourceManifest
) -> List[DiscoveryRecord]:
    title = None
    for line in snapshot.content.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return [
        DiscoveryRecord(
            record_id=f"{manifest.source_id}:{snapshot.content_digest[:16]}",
            source_id=manifest.source_id,
            discovery_url=manifest.url,
            source_repository=manifest.repository,
            source_commit_sha=snapshot.commit_sha,
            publication_week=snapshot.content_digest[:12],  # page revision
            title=title or manifest.name,
            identity=SourceIdentity(
                repository=manifest.repository, primary_url=manifest.url
            ),
            parser_version=PARSER_VERSION,
            content_digest=snapshot.content_digest,
            trust_class=TrustClass.DISCOVERY_SUMMARY,
            summary_text=snapshot.content[:2000],
        )
    ]
