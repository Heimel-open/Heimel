"""External workflow adapters for Function Fabric."""

from .bazoom import (
    ArticleDraft,
    ArticleLink,
    BazoomBrief,
    BazoomDecision,
    BazoomIssue,
    BazoomValidation,
    validate_bazoom_article,
)
from .bazoom_dom import BazoomDomRuntime, BazoomDomSelectors, DomPage
from .bazoom_io import (
    BazoomPageSnapshot,
    BazoomWritePlan,
    FormWrite,
    build_article_write_plan,
    build_review_write_plan,
    parse_article_draft,
    parse_bazoom_brief,
    snapshot_from_pairs,
)

__all__ = [
    "ArticleDraft",
    "ArticleLink",
    "BazoomBrief",
    "BazoomDecision",
    "BazoomDomRuntime",
    "BazoomDomSelectors",
    "BazoomIssue",
    "BazoomPageSnapshot",
    "BazoomValidation",
    "BazoomWritePlan",
    "DomPage",
    "FormWrite",
    "build_article_write_plan",
    "build_review_write_plan",
    "parse_article_draft",
    "parse_bazoom_brief",
    "snapshot_from_pairs",
    "validate_bazoom_article",
]
