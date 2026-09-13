"""Metadata-only parser for official APS Journals RSS feeds.

The parser records publisher metadata needed to locate an article. It does not
copy abstracts or full text, evaluate scientific claims, or grant authority.
Article content may be acquired separately only when open-access or covered by
a valid licence.
"""

from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from src.valo_platform.research_intake.discovery_record import (
    DiscoveryRecord,
    SourceIdentity,
    TrustClass,
)
from src.valo_platform.research_intake.source_manifest import (
    ResearchSourceManifest,
    SourceSnapshot,
)

PARSER_VERSION = "aps_rss/1.0.0"

_DOI_RE = re.compile(r"10\.1103/[^\s<>'\"&]+", re.IGNORECASE)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _first_text(element: ET.Element, *names: str) -> Optional[str]:
    wanted = {name.lower() for name in names}
    for child in element.iter():
        if child is element or _local_name(child.tag) not in wanted:
            continue
        text = "".join(child.itertext()).strip()
        if text:
            return text
    return None


def _entry_link(element: ET.Element) -> Optional[str]:
    for child in element.iter():
        if child is element or _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip()
        text = (child.text or "").strip()
        if href or text:
            return href or text
    return None


def _authors(element: ET.Element) -> List[str]:
    authors: List[str] = []
    for child in element.iter():
        name = _local_name(child.tag)
        if name == "creator":
            text = "".join(child.itertext()).strip()
        elif name == "author":
            text = _first_text(child, "name") or "".join(child.itertext()).strip()
        else:
            continue
        if text and text not in authors:
            authors.append(text)
    return authors


def _extract_doi(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if not value:
            continue
        match = _DOI_RE.search(html.unescape(value))
        if match:
            return match.group(0).rstrip(".,;:)]}")
    return None


def parse(
    snapshot: SourceSnapshot, manifest: ResearchSourceManifest
) -> List[DiscoveryRecord]:
    """Parse RSS 2.0 or Atom entries into metadata-only discovery records."""
    try:
        root = ET.fromstring(snapshot.content)
    except ET.ParseError:
        return []

    entries = [
        node for node in root.iter() if _local_name(node.tag) in {"item", "entry"}
    ]
    records: List[DiscoveryRecord] = []
    seen: set = set()

    for entry in entries:
        title = _first_text(entry, "title")
        link = _entry_link(entry)
        identifier = _first_text(entry, "doi", "identifier", "guid", "id")
        doi = _extract_doi(identifier, link)
        identity_key = doi or link
        if not identity_key or identity_key in seen:
            continue
        seen.add(identity_key)

        publication_date = _first_text(
            entry, "pubdate", "date", "published", "updated"
        )
        canonical = "|".join(
            [doi or "", link or "", title or "", publication_date or ""]
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        records.append(
            DiscoveryRecord(
                record_id=f"{manifest.source_id}:{digest[:16]}",
                source_id=manifest.source_id,
                discovery_url=manifest.url,
                title=title,
                authors=_authors(entry),
                identity=SourceIdentity(doi=doi, primary_url=link),
                parser_version=PARSER_VERSION,
                content_digest=digest,
                trust_class=TrustClass.UNVERIFIED_REFERENCE,
                summary_text=None,
                metadata={
                    "publisher": "American Physical Society",
                    "journal": manifest.metadata.get("journal"),
                    "journal_code": manifest.metadata.get("journal_code"),
                    "publication_date": publication_date,
                    "source_kind": "primary_publisher_metadata",
                    "ingestion_scope": "metadata_only",
                    "journal_access_model": manifest.metadata.get(
                        "journal_access_model", "unknown"
                    ),
                    "full_text_policy": "open_access_or_licensed_only",
                    "publisher_peer_reviewed": True,
                },
            )
        )

    return records
