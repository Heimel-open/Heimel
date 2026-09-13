"""Parser for dair-ai plugin/tool repos (dair-academy-plugins,
m2-deep-research and similar).

Repository code references are classified UNVERIFIED_REFERENCE until the
repository itself is retrieved and verified (then PRIMARY_CODE). Parser
output can never grant tool or execution authority.
"""

from __future__ import annotations

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

PARSER_VERSION = "dair_plugins/1.0.0"

_REPO_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((https?://github\.com/([\w.\-]+/[\w.\-]+))[/)#]?"
)


def parse(
    snapshot: SourceSnapshot, manifest: ResearchSourceManifest
) -> List[DiscoveryRecord]:
    records: List[DiscoveryRecord] = []
    seen: set = set()
    for match in _REPO_LINK_RE.finditer(snapshot.content):
        title, url, repo = match.group(1), match.group(2), match.group(3)
        if repo.lower() in seen:
            continue
        seen.add(repo.lower())
        records.append(
            DiscoveryRecord(
                record_id=f"{manifest.source_id}:{repo.replace('/', '_')}",
                source_id=manifest.source_id,
                discovery_url=manifest.url,
                source_repository=manifest.repository,
                source_commit_sha=snapshot.commit_sha,
                title=title.strip(),
                identity=SourceIdentity(repository=repo, primary_url=url),
                parser_version=PARSER_VERSION,
                content_digest=snapshot.content_digest,
                trust_class=TrustClass.UNVERIFIED_REFERENCE,
                summary_text=match.group(0),
            )
        )
    return records
