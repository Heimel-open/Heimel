from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
HEIMEL_TERMS = {
    "authority": 5,
    "authorization": 5,
    "delegation": 5,
    "mandate": 4,
    "consequence": 5,
    "effect": 3,
    "evidence": 4,
    "provenance": 4,
    "sandbox": 4,
    "regulatory": 3,
    "agent": 2,
    "autonomous": 2,
    "governance": 3,
    "audit": 3,
    "runtime": 3,
    "constraint": 4,
    "revocation": 5,
    "permit": 4,
    "liability": 3,
    "conformity": 3,
    "standardisation": 2,
    "standardization": 2,
    "fundamental rights": 3,
}


class ResearchIntelligenceError(ValueError):
    pass


@dataclass(frozen=True)
class SourcePolicy:
    source_id: str
    feed_url: str
    allowed_domains: tuple[str, ...]
    trust: str = "authoritative"


@dataclass(frozen=True)
class Candidate:
    discovered_via: str
    url: str
    title: str = ""
    published_at: str | None = None


@dataclass(frozen=True)
class EvidenceRecord:
    schema_version: str
    source_id: str
    discovered_via: str
    canonical_url: str
    final_url: str
    title: str
    published_at: str | None
    retrieved_at: str
    content_sha256: str
    content_bytes: int
    media_type: str
    relevance_score: int
    matched_terms: tuple[str, ...]
    disposition: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ResearchIntelligenceError("candidate URL must be absolute http(s)")
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ]
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def _domain_allowed(url: str, domains: tuple[str, ...]) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)


class _VisibleTextParser(HTMLParser):
    """Extract visible text without relying on regex HTML parsing."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)


def _visible_html_text(document: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(document)
    parser.close()
    return " ".join(parser.parts)


def extract_text(content: bytes, media_type: str) -> str:
    media_type = media_type.lower().split(";", 1)[0].strip()
    if media_type in {"text/html", "application/xhtml+xml"}:
        raw = content.decode("utf-8", errors="replace")
        return _visible_html_text(raw)
    if media_type.startswith("text/") or media_type in {"application/json", "application/xml"}:
        return content.decode("utf-8", errors="replace")
    return ""


def score_relevance(title: str, text: str) -> tuple[int, tuple[str, ...]]:
    haystack = f"{title}\n{text[:250000]}".lower()
    hits = tuple(sorted(term for term in HEIMEL_TERMS if term in haystack))
    score = min(100, sum(HEIMEL_TERMS[t] for t in hits))
    return score, hits


def parse_feed(xml_bytes: bytes, source_id: str) -> list[Candidate]:
    root = ET.fromstring(xml_bytes)
    out: list[Candidate] = []
    for item in root.findall(".//item"):
        link = (item.findtext("link") or "").strip()
        if link:
            out.append(Candidate(source_id, link, (item.findtext("title") or "").strip(), item.findtext("pubDate")))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns):
        link_el = entry.find("a:link", ns)
        link = (link_el.get("href") if link_el is not None else "") or ""
        if link:
            out.append(Candidate(source_id, link.strip(), (entry.findtext("a:title", default="", namespaces=ns) or "").strip(), entry.findtext("a:updated", default=None, namespaces=ns)))
    return out


Fetch = Callable[[str], tuple[bytes, str, str]]


def default_fetch(url: str) -> tuple[bytes, str, str]:
    req = Request(url, headers={"User-Agent": "HeimelResearchIntelligence/0.1"})
    with urlopen(req, timeout=20) as response:
        body = response.read(20 * 1024 * 1024 + 1)
        if len(body) > 20 * 1024 * 1024:
            raise ResearchIntelligenceError("source exceeds 20 MiB limit")
        return body, response.headers.get_content_type(), response.geturl()


def ingest(candidate: Candidate, policy: SourcePolicy, fetch: Fetch = default_fetch, threshold: int = 12) -> EvidenceRecord:
    canonical = canonicalize_url(candidate.url)
    if not _domain_allowed(canonical, policy.allowed_domains):
        raise ResearchIntelligenceError("candidate domain is not allowed by source policy")
    content, media_type, final_url = fetch(canonical)
    final_url = canonicalize_url(final_url)
    if not _domain_allowed(final_url, policy.allowed_domains):
        raise ResearchIntelligenceError("redirect escaped allowed source domains")
    digest = sha256(content).hexdigest()
    score, terms = score_relevance(candidate.title, extract_text(content, media_type))
    return EvidenceRecord(
        schema_version="heimel.research.evidence.v1",
        source_id=policy.source_id,
        discovered_via=candidate.discovered_via,
        canonical_url=canonical,
        final_url=final_url,
        title=candidate.title,
        published_at=candidate.published_at,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        content_sha256="sha256:" + digest,
        content_bytes=len(content),
        media_type=media_type,
        relevance_score=score,
        matched_terms=terms,
        disposition="ACCEPT" if score >= threshold else "DROP_LOW_RELEVANCE",
    )


def deduplicate(records: Iterable[EvidenceRecord]) -> list[EvidenceRecord]:
    seen: set[str] = set()
    out: list[EvidenceRecord] = []
    for record in records:
        if record.content_sha256 in seen:
            continue
        seen.add(record.content_sha256)
        out.append(record)
    return out
