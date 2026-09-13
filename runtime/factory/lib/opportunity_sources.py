from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from lib.opportunity_factory import RawOpportunity, RevenueLane


@dataclass(frozen=True)
class SourceListing:
    external_id: str
    title: str
    payout: float
    currency: str = "USD"
    deadline: str | None = None
    requirements: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    automation_allowed: bool = False
    rights_clear: bool = True


class CallableSource:
    """Adapter for bounded read-only discovery functions.

    The fetcher must only retrieve listings. This adapter never applies,
    publishes, purchases, messages, or performs any consequence-bearing action.
    """

    def __init__(
        self,
        source_name: str,
        lane: RevenueLane,
        fetcher: Callable[[], Iterable[SourceListing]],
    ) -> None:
        if not source_name:
            raise ValueError("source_name is required")
        self.source_name = source_name
        self.lane = lane
        self.fetcher = fetcher

    def discover(self) -> tuple[RawOpportunity, ...]:
        return tuple(
            RawOpportunity(
                source=self.source_name,
                external_id=item.external_id,
                title=item.title,
                lane=self.lane,
                payout=item.payout,
                currency=item.currency,
                deadline=item.deadline,
                requirements=item.requirements,
                evidence_refs=item.evidence_refs,
                automation_allowed=item.automation_allowed,
                rights_clear=item.rights_clear,
            )
            for item in self.fetcher()
        )


class JsonFeedSource:
    """Provider-neutral adapter for already-retrieved JSON listing feeds."""

    def __init__(
        self,
        source_name: str,
        lane: RevenueLane,
        fetch_json: Callable[[], Sequence[Mapping[str, object]]],
        *,
        id_field: str = "id",
        title_field: str = "title",
        payout_field: str = "payout",
        currency_field: str = "currency",
        deadline_field: str = "deadline",
    ) -> None:
        self.source_name = source_name
        self.lane = lane
        self.fetch_json = fetch_json
        self.id_field = id_field
        self.title_field = title_field
        self.payout_field = payout_field
        self.currency_field = currency_field
        self.deadline_field = deadline_field

    def discover(self) -> tuple[RawOpportunity, ...]:
        found: list[RawOpportunity] = []
        for row in self.fetch_json():
            external_id = str(row[self.id_field]).strip()
            title = str(row[self.title_field]).strip()
            payout = float(row[self.payout_field])
            currency = str(row.get(self.currency_field, "USD")).strip() or "USD"
            deadline_value = row.get(self.deadline_field)
            deadline = None if deadline_value in (None, "") else str(deadline_value)
            evidence = row.get("evidence_refs", ())
            requirements = row.get("requirements", ())
            found.append(
                RawOpportunity(
                    source=self.source_name,
                    external_id=external_id,
                    title=title,
                    lane=self.lane,
                    payout=payout,
                    currency=currency,
                    deadline=deadline,
                    requirements=tuple(str(item) for item in requirements),
                    evidence_refs=tuple(str(item) for item in evidence),
                    automation_allowed=bool(row.get("automation_allowed", False)),
                    rights_clear=bool(row.get("rights_clear", True)),
                )
            )
        return tuple(found)


def ai_eval_source(fetcher: Callable[[], Iterable[SourceListing]], source_name: str = "ai-evals") -> CallableSource:
    return CallableSource(source_name, RevenueLane.AI_EVALS, fetcher)


def ugc_source(fetcher: Callable[[], Iterable[SourceListing]], source_name: str = "ugc") -> CallableSource:
    return CallableSource(source_name, RevenueLane.UGC_ADS, fetcher)


def clipping_source(fetcher: Callable[[], Iterable[SourceListing]], source_name: str = "clipping") -> CallableSource:
    return CallableSource(source_name, RevenueLane.CLIPPING, fetcher)


def lead_gen_source(fetcher: Callable[[], Iterable[SourceListing]], source_name: str = "lead-gen") -> CallableSource:
    return CallableSource(source_name, RevenueLane.LEAD_GEN, fetcher)
