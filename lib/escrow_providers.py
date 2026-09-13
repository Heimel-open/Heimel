from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class EscrowProviderKind(str, Enum):
    TRUE_ESCROW = "true_escrow"
    MARKETPLACE_BALANCE_PLATFORM = "marketplace_balance_platform"


@dataclass(frozen=True)
class EscrowProviderCandidate:
    name: str
    kind: EscrowProviderKind
    api_available: bool
    service_acceptance_supported: bool
    marketplace_scale_fit: bool
    priority: int
    notes: str


PROVIDERS: Mapping[str, EscrowProviderCandidate] = {
    "escrow_com": EscrowProviderCandidate(
        name="Escrow.com",
        kind=EscrowProviderKind.TRUE_ESCROW,
        api_available=True,
        service_acceptance_supported=True,
        marketplace_scale_fit=True,
        priority=1,
        notes="MVP first choice: regulated escrow with API and buyer acceptance/rejection flow for goods or services.",
    ),
    "adyen": EscrowProviderCandidate(
        name="Adyen for Platforms",
        kind=EscrowProviderKind.MARKETPLACE_BALANCE_PLATFORM,
        api_available=True,
        service_acceptance_supported=False,
        marketplace_scale_fit=True,
        priority=2,
        notes="Scale candidate: balance accounts, verification and controlled payouts; not treated as legal escrow by default.",
    ),
    "mangopay": EscrowProviderCandidate(
        name="Mangopay",
        kind=EscrowProviderKind.MARKETPLACE_BALANCE_PLATFORM,
        api_available=True,
        service_acceptance_supported=False,
        marketplace_scale_fit=True,
        priority=3,
        notes="EU marketplace candidate: wallets/balances and payout infrastructure; acceptance semantics remain ours unless provider contract says otherwise.",
    ),
    "lemonway": EscrowProviderCandidate(
        name="Lemonway",
        kind=EscrowProviderKind.MARKETPLACE_BALANCE_PLATFORM,
        api_available=True,
        service_acceptance_supported=False,
        marketplace_scale_fit=True,
        priority=4,
        notes="EU marketplace candidate: regulated payment institution with marketplace payment infrastructure; not assumed to be escrow.",
    ),
}


def ranked_providers() -> tuple[EscrowProviderCandidate, ...]:
    return tuple(sorted(PROVIDERS.values(), key=lambda provider: provider.priority))


def mvp_provider() -> EscrowProviderCandidate:
    return ranked_providers()[0]
