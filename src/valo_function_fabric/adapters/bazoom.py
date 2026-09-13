from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class BazoomIssue(str, Enum):
    AI_PRODUCTION_PROHIBITED = "ai_production_prohibited"
    TITLE_MISMATCH = "title_mismatch"
    WORD_COUNT_LOW = "word_count_low"
    WORD_COUNT_HIGH = "word_count_high"
    TARGET_URL_MISSING = "target_url_missing"
    TARGET_URL_TOO_LATE = "target_url_too_late"
    TARGET_URL_OCCURRENCES_LOW = "target_url_occurrences_low"
    ANCHOR_TEXT_MISSING = "anchor_text_missing"
    INTERNAL_LINK_MISSING = "internal_link_missing"
    TRUST_LINK_MISSING = "trust_link_missing"
    MEDIA_DOMAIN_LINK_USED_AS_TRUST = "media_domain_link_used_as_trust"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class BazoomDecision(str, Enum):
    BLOCK = "block"
    REVIEW = "review"
    READY = "ready"


@dataclass(frozen=True)
class ArticleLink:
    text: str
    url: str
    relation: str = "external"

    @property
    def host(self) -> str:
        return (urlparse(self.url).hostname or "").lower().removeprefix("www.")


@dataclass(frozen=True)
class BazoomBrief:
    anchor_text: str
    target_url: str
    target_placement_fraction: float = 1 / 3
    target_url_min_occurrences: int = 1
    internal_links_required: int = 0
    trust_links_required: int = 0
    media_domain: str | None = None
    exact_title: str | None = None
    target_words: int | None = None
    word_tolerance_fraction: float = 0.10
    manual_writing_required: bool = False

    def __post_init__(self) -> None:
        if not 0 < self.target_placement_fraction <= 1:
            raise ValueError("target_placement_fraction must be in (0, 1]")
        if self.target_url_min_occurrences < 1:
            raise ValueError("target_url_min_occurrences must be >= 1")
        if self.internal_links_required < 0 or self.trust_links_required < 0:
            raise ValueError("link requirements cannot be negative")
        if self.target_words is not None and self.target_words < 1:
            raise ValueError("target_words must be >= 1")
        if not 0 <= self.word_tolerance_fraction < 1:
            raise ValueError("word_tolerance_fraction must be in [0, 1)")


@dataclass(frozen=True)
class ArticleDraft:
    title: str
    body: str
    links: tuple[ArticleLink, ...] = ()
    generated_with_ai: bool = False

    @property
    def words(self) -> tuple[str, ...]:
        return tuple(self.body.split())

    @property
    def word_count(self) -> int:
        return len(self.words)


@dataclass(frozen=True)
class BazoomValidation:
    decision: BazoomDecision
    issues: tuple[BazoomIssue, ...]
    word_count: int
    target_url_occurrences: int
    first_target_word_index: int | None

    @property
    def can_submit(self) -> bool:
        return self.decision is BazoomDecision.READY


def _normalise_url(url: str) -> str:
    return url.rstrip("/")


def _count_target_occurrences(article: ArticleDraft, target_url: str) -> int:
    target = _normalise_url(target_url)
    return sum(
        1
        for link in article.links
        if _normalise_url(link.url) == target
    )


def _first_target_word_index(article: ArticleDraft, target_url: str) -> int | None:
    target = _normalise_url(target_url)
    linked_texts = [
        link.text.strip()
        for link in article.links
        if _normalise_url(link.url) == target and link.text.strip()
    ]
    if not linked_texts:
        return None

    body_lower = article.body.lower()
    earliest_char: int | None = None
    for text in linked_texts:
        pos = body_lower.find(text.lower())
        if pos >= 0 and (earliest_char is None or pos < earliest_char):
            earliest_char = pos
    if earliest_char is None:
        return None
    return len(article.body[:earliest_char].split())


def _is_media_internal(link: ArticleLink, media_domain: str | None) -> bool:
    if link.relation == "internal":
        return True
    if media_domain is None:
        return False
    media = media_domain.lower().removeprefix("www.")
    return link.host == media or link.host.endswith(f".{media}")


def _is_trust_link(link: ArticleLink, brief: BazoomBrief) -> bool:
    if link.relation == "trust":
        return True
    if _is_media_internal(link, brief.media_domain):
        return False
    return link.host not in {"", _host(brief.target_url)}


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def validate_bazoom_article(
    brief: BazoomBrief,
    article: ArticleDraft,
    *,
    human_review_complete: bool = False,
) -> BazoomValidation:
    """Deterministically validate Bazoom article requirements.

    This adapter validates mechanical constraints only. Semantic topic relevance,
    factual quality, tone, and editorial judgement remain human/model review
    concerns and are intentionally not converted into fake deterministic checks.
    """

    issues: list[BazoomIssue] = []

    if brief.manual_writing_required and article.generated_with_ai:
        issues.append(BazoomIssue.AI_PRODUCTION_PROHIBITED)

    if brief.exact_title is not None and article.title.strip() != brief.exact_title.strip():
        issues.append(BazoomIssue.TITLE_MISMATCH)

    if brief.target_words is not None:
        low = int(brief.target_words * (1 - brief.word_tolerance_fraction))
        high = int(brief.target_words * (1 + brief.word_tolerance_fraction))
        if article.word_count < low:
            issues.append(BazoomIssue.WORD_COUNT_LOW)
        elif article.word_count > high:
            issues.append(BazoomIssue.WORD_COUNT_HIGH)

    target_occurrences = _count_target_occurrences(article, brief.target_url)
    first_target_index = _first_target_word_index(article, brief.target_url)

    if target_occurrences == 0:
        issues.append(BazoomIssue.TARGET_URL_MISSING)
    elif target_occurrences < brief.target_url_min_occurrences:
        issues.append(BazoomIssue.TARGET_URL_OCCURRENCES_LOW)

    if target_occurrences:
        anchor_matches = any(
            _normalise_url(link.url) == _normalise_url(brief.target_url)
            and link.text.strip().lower() == brief.anchor_text.strip().lower()
            for link in article.links
        )
        if not anchor_matches:
            issues.append(BazoomIssue.ANCHOR_TEXT_MISSING)

    if first_target_index is not None and article.word_count:
        latest_allowed = article.word_count * brief.target_placement_fraction
        if first_target_index >= latest_allowed:
            issues.append(BazoomIssue.TARGET_URL_TOO_LATE)

    internal_count = sum(
        1 for link in article.links if _is_media_internal(link, brief.media_domain)
    )
    if internal_count < brief.internal_links_required:
        issues.append(BazoomIssue.INTERNAL_LINK_MISSING)

    trust_count = sum(1 for link in article.links if _is_trust_link(link, brief))
    if trust_count < brief.trust_links_required:
        issues.append(BazoomIssue.TRUST_LINK_MISSING)

    if brief.media_domain and any(
        link.relation == "trust" and _is_media_internal(link, brief.media_domain)
        for link in article.links
    ):
        issues.append(BazoomIssue.MEDIA_DOMAIN_LINK_USED_AS_TRUST)

    blockers = {
        BazoomIssue.AI_PRODUCTION_PROHIBITED,
        BazoomIssue.TITLE_MISMATCH,
        BazoomIssue.WORD_COUNT_LOW,
        BazoomIssue.WORD_COUNT_HIGH,
        BazoomIssue.TARGET_URL_MISSING,
        BazoomIssue.TARGET_URL_TOO_LATE,
        BazoomIssue.TARGET_URL_OCCURRENCES_LOW,
        BazoomIssue.ANCHOR_TEXT_MISSING,
        BazoomIssue.INTERNAL_LINK_MISSING,
        BazoomIssue.TRUST_LINK_MISSING,
        BazoomIssue.MEDIA_DOMAIN_LINK_USED_AS_TRUST,
    }

    if any(issue in blockers for issue in issues):
        decision = BazoomDecision.BLOCK
    elif not human_review_complete:
        issues.append(BazoomIssue.HUMAN_REVIEW_REQUIRED)
        decision = BazoomDecision.REVIEW
    else:
        decision = BazoomDecision.READY

    return BazoomValidation(
        decision=decision,
        issues=tuple(issues),
        word_count=article.word_count,
        target_url_occurrences=target_occurrences,
        first_target_word_index=first_target_index,
    )
