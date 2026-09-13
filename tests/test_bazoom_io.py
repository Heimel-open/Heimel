from valo_function_fabric.adapters.bazoom import ArticleLink, BazoomDecision, BazoomIssue
from valo_function_fabric.adapters.bazoom_io import (
    BazoomPageSnapshot,
    build_article_write_plan,
    build_review_write_plan,
    parse_article_draft,
    parse_bazoom_brief,
)


def _body_with_anchor(anchor: str, *, words: int = 120) -> str:
    prefix = " ".join(f"w{i}" for i in range(20))
    suffix = " ".join(f"x{i}" for i in range(max(0, words - 21)))
    return f"{prefix} {anchor} {suffix}".strip()


def test_parse_brief_from_trial_style_snapshot():
    snapshot = BazoomPageSnapshot(
        fields={
            "Anchor text": "best ea forex robot",
            "Target URL": "https://fxibot.com/",
            "Target URL placement": "First third of the article",
            "Trust link": "1 required",
            "Internal link": "1 required",
            "Media domain": "economicsonline.co.uk",
            "Article title": "Why Expert Advisors Continue to Shape Automated Forex Trading",
            "Comments": "The client tracked URL should be inserted at least twice into the article.",
        }
    )

    brief = parse_bazoom_brief(snapshot)

    assert brief.anchor_text == "best ea forex robot"
    assert brief.target_url_min_occurrences == 2
    assert brief.target_placement_fraction == 1 / 3
    assert brief.trust_links_required == 1
    assert brief.internal_links_required == 1
    assert brief.media_domain == "economicsonline.co.uk"


def test_parse_brief_requires_anchor_and_target():
    try:
        parse_bazoom_brief(BazoomPageSnapshot(fields={"Anchor text": "x"}))
    except ValueError as exc:
        assert "target URL" in str(exc)
    else:
        raise AssertionError("missing target URL must fail closed")


def test_manual_writing_signal_is_preserved():
    brief = parse_bazoom_brief(
        BazoomPageSnapshot(
            fields={
                "Anchor text": "zamsino.com",
                "Target URL": "https://zamsino.com/",
                "Write manually": "Yes",
            }
        )
    )
    assert brief.manual_writing_required is True


def test_article_write_plan_stops_at_human_submit_boundary():
    anchor = "zamsino.com"
    target = "https://zamsino.com/"
    body = _body_with_anchor(anchor)
    snapshot = BazoomPageSnapshot(
        fields={"Anchor text": anchor, "Target URL": target},
        article_title="How Technology Is Changing the iGaming Experience",
        article_body=body,
        article_links=(ArticleLink(anchor, target),),
    )
    brief = parse_bazoom_brief(snapshot)
    article = parse_article_draft(snapshot)

    plan = build_article_write_plan(brief, article, human_review_complete=True)

    assert plan.validation.decision is BazoomDecision.READY
    assert plan.requires_human_submit is True
    assert plan.submit_allowed is False
    assert [write.field for write in plan.writes] == ["article_title", "article_body"]


def test_ai_generated_manual_task_is_blocked_before_write():
    anchor = "zamsino.com"
    target = "https://zamsino.com/"
    snapshot = BazoomPageSnapshot(
        fields={
            "Anchor text": anchor,
            "Target URL": target,
            "Write manually": "Yes",
        },
        article_title="Technology focus",
        article_body=_body_with_anchor(anchor),
        article_links=(ArticleLink(anchor, target),),
    )
    brief = parse_bazoom_brief(snapshot)
    article = parse_article_draft(snapshot, generated_with_ai=True)

    plan = build_article_write_plan(brief, article, human_review_complete=True)

    assert plan.validation.decision is BazoomDecision.BLOCK
    assert BazoomIssue.AI_PRODUCTION_PROHIBITED in plan.validation.issues


def test_review_plan_maps_all_categories_and_final_answer():
    writes = build_review_write_plan(
        category_issues={
            "Topic relevance": True,
            "Client guideline compliance": False,
            "Anchor implementation": True,
        },
        editorial_feedback="Rewrite the anchor context.",
        approve=False,
    )

    values = {write.field: write.value for write in writes}
    assert values["issue:Topic relevance"] == "Yes"
    assert values["issue:Client guideline compliance"] == "No"
    assert values["issue:Anchor implementation"] == "Yes"
    assert values["editorial_feedback"] == "Rewrite the anchor context."
    assert values["final_answer"] == "Reject"
