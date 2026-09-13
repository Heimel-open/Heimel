from __future__ import annotations

import pytest

from valo_function_fabric.adapters.bazoom import BazoomDecision, BazoomValidation
from valo_function_fabric.adapters.bazoom_dom import BazoomDomRuntime, BazoomDomSelectors
from valo_function_fabric.adapters.bazoom_io import BazoomPageSnapshot, BazoomWritePlan, FormWrite


class FakePage:
    def __init__(self) -> None:
        self.text_values = {
            "#anchor": "zamsino.com",
            "#target": "https://zamsino.com/",
            "#placement": "First third",
        }
        self.input_values = {
            "#title": "How Technology Is Changing the iGaming Experience",
            "#body": "Body text",
        }
        self.link_values = {
            "#article a": [
                ("zamsino.com", "https://zamsino.com/"),
                ("TMCnet", "https://www.tmcnet.com/"),
            ]
        }
        self.fills: list[tuple[str, str]] = []
        self.clicks: list[str] = []

    def text(self, selector: str) -> str:
        return self.text_values.get(selector, "")

    def value(self, selector: str) -> str:
        return self.input_values.get(selector, "")

    def links(self, selector: str):
        return self.link_values.get(selector, [])

    def fill(self, selector: str, value: str) -> None:
        self.fills.append((selector, value))

    def click(self, selector: str) -> None:
        self.clicks.append(selector)


@pytest.fixture
def selectors() -> BazoomDomSelectors:
    return BazoomDomSelectors(
        field_selectors={
            "anchor text": "#anchor",
            "target url": "#target",
            "target url placement": "#placement",
        },
        article_title="#title",
        article_body="#body",
        article_links="#article a",
        write_selectors={
            "article_title": "#title",
            "article_body": "#body",
            "editorial_feedback": "#feedback",
            "final_answer": "#final",
            "issue:topic relevance": "#topic",
        },
        submit_selector="#submit",
    )


def test_capture_snapshot(selectors: BazoomDomSelectors) -> None:
    page = FakePage()
    runtime = BazoomDomRuntime(page, selectors)

    snapshot = runtime.capture_snapshot()

    assert isinstance(snapshot, BazoomPageSnapshot)
    assert snapshot.fields["anchor text"] == "zamsino.com"
    assert snapshot.article_title.startswith("How Technology")
    assert snapshot.article_links[0].url == "https://zamsino.com/"


def test_apply_write_plan_without_submit(selectors: BazoomDomSelectors) -> None:
    page = FakePage()
    runtime = BazoomDomRuntime(page, selectors)
    validation = BazoomValidation(
        decision=BazoomDecision.READY,
        issues=(),
        word_count=400,
        target_url_occurrences=1,
        first_target_word_index=40,
    )
    plan = BazoomWritePlan(
        writes=(FormWrite("article_title", "New title"), FormWrite("article_body", "New body")),
        validation=validation,
        requires_human_submit=True,
    )

    runtime.apply_write_plan(plan)

    assert page.fills == [("#title", "New title"), ("#body", "New body")]
    assert page.clicks == []


def test_submit_is_blocked_by_human_gate(selectors: BazoomDomSelectors) -> None:
    page = FakePage()
    runtime = BazoomDomRuntime(page, selectors)
    validation = BazoomValidation(
        decision=BazoomDecision.READY,
        issues=(),
        word_count=400,
        target_url_occurrences=1,
        first_target_word_index=40,
    )
    plan = BazoomWritePlan(
        writes=(FormWrite("article_title", "New title"),),
        validation=validation,
        requires_human_submit=True,
    )

    with pytest.raises(PermissionError):
        runtime.apply_write_plan(plan, allow_submit=True)

    assert page.clicks == []


def test_review_writes_map_to_fields(selectors: BazoomDomSelectors) -> None:
    page = FakePage()
    runtime = BazoomDomRuntime(page, selectors)

    runtime.apply_review_writes(
        (
            FormWrite("issue:topic relevance", "Yes"),
            FormWrite("editorial_feedback", "Revise topic."),
            FormWrite("final_answer", "Reject"),
        )
    )

    assert page.fills == [
        ("#topic", "Yes"),
        ("#feedback", "Revise topic."),
        ("#final", "Reject"),
    ]
