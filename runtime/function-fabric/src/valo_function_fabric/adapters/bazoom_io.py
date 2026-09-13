from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .bazoom import ArticleDraft, ArticleLink, BazoomBrief, BazoomValidation, validate_bazoom_article


@dataclass(frozen=True)
class BazoomPageSnapshot:
    """Normalized Bazoom page state captured by a browser/operator layer.

    The I/O adapter deliberately does not own browser credentials or navigation.
    A browser layer captures visible fields and links, then passes them here.
    """

    fields: Mapping[str, str]
    article_title: str = ""
    article_body: str = ""
    article_links: tuple[ArticleLink, ...] = ()


@dataclass(frozen=True)
class FormWrite:
    field: str
    value: str


@dataclass(frozen=True)
class BazoomWritePlan:
    writes: tuple[FormWrite, ...]
    validation: BazoomValidation
    requires_human_submit: bool = True

    @property
    def submit_allowed(self) -> bool:
        return self.validation.can_submit and not self.requires_human_submit


def _value(fields: Mapping[str, str], *names: str) -> str | None:
    lowered = {key.strip().lower(): value.strip() for key, value in fields.items()}
    for name in names:
        value = lowered.get(name.strip().lower())
        if value:
            return value
    return None


def _int_value(fields: Mapping[str, str], *names: str, default: int = 0) -> int:
    raw = _value(fields, *names)
    if raw is None:
        return default
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else default


def _bool_value(fields: Mapping[str, str], *names: str) -> bool:
    raw = (_value(fields, *names) or "").strip().lower()
    return raw in {"yes", "true", "1", "required", "manual", "write manually"}


def parse_bazoom_brief(snapshot: BazoomPageSnapshot) -> BazoomBrief:
    fields = snapshot.fields
    anchor = _value(fields, "anchor text", "anchor")
    target = _value(fields, "target url", "anchor url", "target")
    if not anchor:
        raise ValueError("Bazoom snapshot missing anchor text")
    if not target:
        raise ValueError("Bazoom snapshot missing target URL")

    placement = (_value(fields, "placement of target url", "target url placement") or "").lower()
    placement_fraction = 1 / 3 if "first third" in placement else 1.0

    target_min = _int_value(
        fields,
        "target url minimum occurrences",
        "target url occurrences",
        default=1,
    )
    if "at least twice" in " ".join(fields.values()).lower():
        target_min = max(target_min, 2)

    return BazoomBrief(
        anchor_text=anchor,
        target_url=target,
        target_placement_fraction=placement_fraction,
        target_url_min_occurrences=max(1, target_min),
        internal_links_required=_int_value(fields, "internal links", "internal link", default=0),
        trust_links_required=_int_value(fields, "trust links", "trust link", default=0),
        media_domain=_value(fields, "media domain", "media"),
        exact_title=_value(fields, "exact title", "article title"),
        target_words=_int_value(fields, "target words", "word count", default=0) or None,
        manual_writing_required=_bool_value(fields, "write manually", "manual writing", "no use of ai"),
    )


def parse_article_draft(
    snapshot: BazoomPageSnapshot,
    *,
    generated_with_ai: bool = False,
) -> ArticleDraft:
    if not snapshot.article_title.strip():
        raise ValueError("Bazoom snapshot missing article title")
    if not snapshot.article_body.strip():
        raise ValueError("Bazoom snapshot missing article body")
    return ArticleDraft(
        title=snapshot.article_title.strip(),
        body=snapshot.article_body.strip(),
        links=snapshot.article_links,
        generated_with_ai=generated_with_ai,
    )


def build_article_write_plan(
    brief: BazoomBrief,
    article: ArticleDraft,
    *,
    human_review_complete: bool = False,
) -> BazoomWritePlan:
    validation = validate_bazoom_article(
        brief,
        article,
        human_review_complete=human_review_complete,
    )
    return BazoomWritePlan(
        writes=(
            FormWrite("article_title", article.title),
            FormWrite("article_body", article.body),
        ),
        validation=validation,
        requires_human_submit=True,
    )


def build_review_write_plan(
    *,
    category_issues: Mapping[str, bool],
    editorial_feedback: str,
    approve: bool,
) -> tuple[FormWrite, ...]:
    """Map review output to form writes without performing the submit effect."""

    writes: list[FormWrite] = []
    for category, issue in category_issues.items():
        writes.append(FormWrite(f"issue:{category}", "Yes" if issue else "No"))
    writes.extend(
        (
            FormWrite("editorial_feedback", editorial_feedback.strip()),
            FormWrite("final_answer", "Approve" if approve else "Reject"),
        )
    )
    return tuple(writes)


def snapshot_from_pairs(
    fields: Mapping[str, str],
    *,
    article_title: str = "",
    article_body: str = "",
    links: Sequence[ArticleLink] = (),
) -> BazoomPageSnapshot:
    """Small convenience boundary for browser DOM extractors and fixtures."""

    return BazoomPageSnapshot(
        fields=dict(fields),
        article_title=article_title,
        article_body=article_body,
        article_links=tuple(links),
    )
