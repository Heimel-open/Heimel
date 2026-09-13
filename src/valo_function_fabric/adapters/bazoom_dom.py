from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from .bazoom_io import BazoomPageSnapshot, BazoomWritePlan, FormWrite


class DomPage(Protocol):
    def text(self, selector: str) -> str: ...
    def value(self, selector: str) -> str: ...
    def links(self, selector: str) -> Sequence[tuple[str, str]]: ...
    def fill(self, selector: str, value: str) -> None: ...
    def click(self, selector: str) -> None: ...


@dataclass(frozen=True)
class BazoomDomSelectors:
    field_selectors: Mapping[str, str]
    article_title: str
    article_body: str
    article_links: str
    write_selectors: Mapping[str, str]
    submit_selector: str | None = None


class BazoomDomRuntime:
    """Browser/DOM boundary for Bazoom.

    This layer only reads visible page state and applies a precomputed write plan.
    It does not own credentials, generate content, bypass task restrictions, or
    submit unless the caller explicitly enables the submit effect.
    """

    def __init__(self, page: DomPage, selectors: BazoomDomSelectors) -> None:
        self.page = page
        self.selectors = selectors

    def capture_snapshot(self) -> BazoomPageSnapshot:
        fields = {
            name: self.page.text(selector).strip()
            for name, selector in self.selectors.field_selectors.items()
        }

        from .bazoom import ArticleLink

        links = tuple(
            ArticleLink(text=text.strip(), url=url.strip())
            for text, url in self.page.links(self.selectors.article_links)
            if url.strip()
        )

        return BazoomPageSnapshot(
            fields=fields,
            article_title=self.page.value(self.selectors.article_title).strip(),
            article_body=self.page.value(self.selectors.article_body).strip(),
            article_links=links,
        )

    def apply_write_plan(
        self,
        plan: BazoomWritePlan,
        *,
        allow_submit: bool = False,
    ) -> None:
        for write in plan.writes:
            self._apply_write(write)

        if allow_submit:
            if plan.requires_human_submit:
                raise PermissionError("write plan requires explicit human submit")
            if not plan.submit_allowed:
                raise PermissionError("write plan is not validated for submission")
            if not self.selectors.submit_selector:
                raise RuntimeError("no submit selector configured")
            self.page.click(self.selectors.submit_selector)

    def apply_review_writes(self, writes: Sequence[FormWrite]) -> None:
        for write in writes:
            self._apply_write(write)

    def _apply_write(self, write: FormWrite) -> None:
        selector = self.selectors.write_selectors.get(write.field)
        if selector is None and write.field.startswith("issue:"):
            selector = self.selectors.write_selectors.get(write.field)
        if selector is None:
            raise KeyError(f"no DOM selector configured for write field {write.field!r}")
        self.page.fill(selector, write.value)
