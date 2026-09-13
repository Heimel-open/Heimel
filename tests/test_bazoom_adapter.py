from valo_function_fabric.adapters.bazoom import (
    ArticleDraft,
    ArticleLink,
    BazoomBrief,
    BazoomDecision,
    BazoomIssue,
    validate_bazoom_article,
)


def _body(words: int, anchor_at: int | None = None, anchor: str = "zamsino.com") -> str:
    tokens = [f"word{i}" for i in range(words)]
    if anchor_at is not None:
        tokens[anchor_at] = anchor
    return " ".join(tokens)


def test_ready_when_mechanical_requirements_and_human_review_pass() -> None:
    brief = BazoomBrief(
        anchor_text="zamsino.com",
        target_url="https://zamsino.com/",
        target_words=400,
        internal_links_required=1,
        trust_links_required=1,
        media_domain="tmcnet.com",
    )
    article = ArticleDraft(
        title="How Technology Is Changing the iGaming Experience",
        body=_body(415, anchor_at=60),
        links=(
            ArticleLink("zamsino.com", "https://zamsino.com/"),
            ArticleLink("TMCnet", "https://www.tmcnet.com/technology", relation="internal"),
            ArticleLink("Meta Quest", "https://www.meta.com/quest/", relation="trust"),
        ),
    )

    result = validate_bazoom_article(brief, article, human_review_complete=True)

    assert result.decision is BazoomDecision.READY
    assert result.issues == ()
    assert result.word_count == 415
    assert result.first_target_word_index == 60


def test_manual_writing_requirement_blocks_ai_generated_draft() -> None:
    brief = BazoomBrief(
        anchor_text="zamsino.com",
        target_url="https://zamsino.com/",
        manual_writing_required=True,
    )
    article = ArticleDraft(
        title="Technology",
        body=_body(100, anchor_at=10),
        links=(ArticleLink("zamsino.com", "https://zamsino.com/"),),
        generated_with_ai=True,
    )

    result = validate_bazoom_article(brief, article, human_review_complete=True)

    assert result.decision is BazoomDecision.BLOCK
    assert BazoomIssue.AI_PRODUCTION_PROHIBITED in result.issues


def test_target_must_be_in_first_third() -> None:
    brief = BazoomBrief(
        anchor_text="gtbet casino",
        target_url="https://gtbet.net/",
    )
    article = ArticleDraft(
        title="Example",
        body=_body(300, anchor_at=150, anchor="gtbet casino"),
        links=(ArticleLink("gtbet casino", "https://gtbet.net/"),),
    )

    result = validate_bazoom_article(brief, article, human_review_complete=True)

    assert result.decision is BazoomDecision.BLOCK
    assert BazoomIssue.TARGET_URL_TOO_LATE in result.issues


def test_two_target_occurrences_can_be_required() -> None:
    brief = BazoomBrief(
        anchor_text="best ea forex robot",
        target_url="https://fxibot.com/",
        target_url_min_occurrences=2,
    )
    article = ArticleDraft(
        title="Why Expert Advisors Continue to Shape Automated Forex Trading",
        body="best ea forex robot " + _body(199),
        links=(ArticleLink("best ea forex robot", "https://fxibot.com/"),),
    )

    result = validate_bazoom_article(brief, article, human_review_complete=True)

    assert result.decision is BazoomDecision.BLOCK
    assert BazoomIssue.TARGET_URL_OCCURRENCES_LOW in result.issues


def test_exact_title_is_enforced() -> None:
    brief = BazoomBrief(
        anchor_text="best ea forex robot",
        target_url="https://fxibot.com/",
        exact_title="Why Expert Advisors Continue to Shape Automated Forex Trading",
    )
    article = ArticleDraft(
        title="Expert Advisors and Forex",
        body="best ea forex robot " + _body(99),
        links=(ArticleLink("best ea forex robot", "https://fxibot.com/"),),
    )

    result = validate_bazoom_article(brief, article, human_review_complete=True)

    assert BazoomIssue.TITLE_MISMATCH in result.issues
    assert result.decision is BazoomDecision.BLOCK


def test_requires_human_review_even_when_deterministic_checks_pass() -> None:
    brief = BazoomBrief(
        anchor_text="zamsino.com",
        target_url="https://zamsino.com/",
    )
    article = ArticleDraft(
        title="Technology",
        body=_body(100, anchor_at=10),
        links=(ArticleLink("zamsino.com", "https://zamsino.com/"),),
    )

    result = validate_bazoom_article(brief, article)

    assert result.decision is BazoomDecision.REVIEW
    assert result.issues == (BazoomIssue.HUMAN_REVIEW_REQUIRED,)


def test_media_link_does_not_satisfy_trust_requirement() -> None:
    brief = BazoomBrief(
        anchor_text="zamsino.com",
        target_url="https://zamsino.com/",
        trust_links_required=1,
        media_domain="tmcnet.com",
    )
    article = ArticleDraft(
        title="Technology",
        body=_body(100, anchor_at=10),
        links=(
            ArticleLink("zamsino.com", "https://zamsino.com/"),
            ArticleLink("TMCnet", "https://www.tmcnet.com/news", relation="internal"),
        ),
    )

    result = validate_bazoom_article(brief, article, human_review_complete=True)

    assert BazoomIssue.TRUST_LINK_MISSING in result.issues
    assert result.decision is BazoomDecision.BLOCK
