from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from typing import Callable

from lib.opportunity_factory import RawOpportunity, RevenueLane


TextFetcher = Callable[[str], str]


def _clean_text(document: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", document, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _money(value: str) -> float:
    return float(value.replace(",", ""))


@dataclass(frozen=True)
class PublicPageContract:
    source_name: str
    url: str
    lane: RevenueLane
    mode: str = "read_only"

    def __post_init__(self) -> None:
        if self.mode != "read_only":
            raise ValueError("public opportunity sources must remain read_only")
        if not self.url.startswith("https://"):
            raise ValueError("public opportunity source requires https URL")


MERCOR_EXPERTS = PublicPageContract(
    source_name="mercor-experts",
    url="https://www.mercor.com/experts/",
    lane=RevenueLane.AI_EVALS,
)

WHOP_CONTENT_REWARDS = PublicPageContract(
    source_name="whop-content-rewards",
    url="https://whop.com/contentrewards/",
    lane=RevenueLane.CLIPPING,
)


class MercorExpertsSource:
    """Parse public Mercor expert opportunities from a governed GET response."""

    _ROLE_RATE = re.compile(
        r"(?P<title>[A-Z][A-Za-z0-9 /&()'.,+–—-]{2,90}?)\s*"
        r"\$(?P<low>[0-9][0-9,]*(?:\.[0-9]+)?)"
        r"(?:\s*[-–—]\s*\$(?P<high>[0-9][0-9,]*(?:\.[0-9]+)?))?"
        r"\s*(?P<unit>/hr|per hour|hr)?",
        flags=re.I,
    )

    def __init__(self, fetch_text: TextFetcher, contract: PublicPageContract = MERCOR_EXPERTS) -> None:
        self.fetch_text = fetch_text
        self.contract = contract

    def discover(self) -> tuple[RawOpportunity, ...]:
        text = _clean_text(self.fetch_text(self.contract.url))
        found: list[RawOpportunity] = []
        seen: set[str] = set()
        for match in self._ROLE_RATE.finditer(text):
            title = match.group("title").strip(" -–—")
            low = _money(match.group("low"))
            high = _money(match.group("high")) if match.group("high") else low
            payout = (low + high) / 2.0
            key = f"{title.lower()}|{low}|{high}"
            if key in seen:
                continue
            seen.add(key)
            found.append(
                RawOpportunity(
                    source=self.contract.source_name,
                    external_id=_stable_id("mercor", key),
                    title=title,
                    lane=RevenueLane.AI_EVALS,
                    payout=payout,
                    currency="USD",
                    requirements=("public listing; eligibility and application terms must be checked before action",),
                    evidence_refs=(self.contract.url,),
                    automation_allowed=False,
                    rights_clear=True,
                )
            )
        return tuple(found)


class WhopContentRewardsSource:
    """Parse public clipping campaign budgets from a governed GET response."""

    _CAMPAIGN = re.compile(
        r"(?P<title>[A-Za-z0-9$][A-Za-z0-9 $&()'.,+!?:/–—-]{2,100}?)\s+"
        r"Budget:\s*\$(?P<budget>[0-9][0-9,]*(?:\.[0-9]+)?)"
        r"(?:\s+CPM:\s*\$(?P<cpm>[0-9][0-9,]*(?:\.[0-9]+)?)\s*per\s*1,?000\s*views)?",
        flags=re.I,
    )

    def __init__(self, fetch_text: TextFetcher, contract: PublicPageContract = WHOP_CONTENT_REWARDS) -> None:
        self.fetch_text = fetch_text
        self.contract = contract

    def discover(self) -> tuple[RawOpportunity, ...]:
        text = _clean_text(self.fetch_text(self.contract.url))
        found: list[RawOpportunity] = []
        seen: set[str] = set()
        for match in self._CAMPAIGN.finditer(text):
            title = match.group("title").strip(" -–—#")
            budget = _money(match.group("budget"))
            cpm = _money(match.group("cpm")) if match.group("cpm") else None
            key = f"{title.lower()}|{budget}|{cpm or 0}"
            if key in seen:
                continue
            seen.add(key)
            requirements = ["public campaign; platform rules and content rights must be checked before action"]
            if cpm is not None:
                requirements.append(f"published CPM: ${cpm:g} per 1000 views")
            found.append(
                RawOpportunity(
                    source=self.contract.source_name,
                    external_id=_stable_id("whop", key),
                    title=title,
                    lane=RevenueLane.CLIPPING,
                    payout=budget,
                    currency="USD",
                    requirements=tuple(requirements),
                    evidence_refs=(self.contract.url,),
                    automation_allowed=False,
                    rights_clear=True,
                )
            )
        return tuple(found)


def public_sources(fetch_text: TextFetcher) -> tuple[object, ...]:
    """Sources usable without credentials; network access remains externally governed."""
    return (
        MercorExpertsSource(fetch_text),
        WhopContentRewardsSource(fetch_text),
    )
