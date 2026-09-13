"""Parser for dair-ai/AI-Papers-of-the-Week markdown.

Extracts one DiscoveryRecord per paper entry. Output is a DISCOVERY_SUMMARY
with full provenance; it never carries evaluation or execution authority.
"""

from __future__ import annotations

import hashlib
import re
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

PARSER_VERSION = "dair_weekly/1.0.0"

_ARXIV_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE
)
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_WEEK_RE = re.compile(r"(?:Week|week of)\s+([\w\s\-–,]+\d{4})")


def parse(
    snapshot: SourceSnapshot, manifest: ResearchSourceManifest
) -> List[DiscoveryRecord]:
    records: List[DiscoveryRecord] = []
    week_match = _WEEK_RE.search(snapshot.content)
    week = week_match.group(1).strip() if week_match else None
    seen: set = set()
    for line in snapshot.content.splitlines():
        link = _LINK_RE.search(line)
        if not link:
            continue
        title, url = link.group(1).strip(), link.group(2).strip()
        arxiv = _ARXIV_RE.search(url) or _ARXIV_RE.search(line)
        arxiv_id = arxiv.group(1) if arxiv else None
        key = arxiv_id or url
        if key in seen:
            continue
        seen.add(key)
        digest = hashlib.sha256(line.strip().encode("utf-8")).hexdigest()
        records.append(
            DiscoveryRecord(
                record_id=f"{manifest.source_id}:{digest[:16]}",
                source_id=manifest.source_id,
                discovery_url=manifest.url,
                source_repository=manifest.repository,
                source_commit_sha=snapshot.commit_sha,
                publication_week=week,
                title=title,
                identity=SourceIdentity(arxiv_id=arxiv_id, primary_url=url),
                parser_version=PARSER_VERSION,
                content_digest=digest,
                trust_class=TrustClass.DISCOVERY_SUMMARY,
                summary_text=line.strip(),
            )
        )
    return records
