"""Provider-neutral acquisition boundary for Speider-controlled collection.

Providers receive an already-authorized, version-pinned collection plan. The public
contract deliberately exposes no Actor discovery and no governance-decision methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .models import (
    CostEstimate,
    ProviderRunHandle,
    ProviderRunStatus,
    RawAcquisitionRecord,
    RegistryExecutionGrant,
)


class AcquisitionProviderError(RuntimeError):
    """Provider state or evidence cannot be verified; collection fails closed."""


@dataclass(frozen=True)
class ProviderAcquisitionRequest:
    """Provider input created only after ActorRegistry authorization."""

    request_id: str
    registry_entry_ref: str
    actor_id: str
    actor_version: str
    actor_input: dict[str, Any]
    requested_source: str
    source_platform: str
    tenant_id: str
    correlation_id: str
    timeout_seconds: int
    max_cost_usd: float
    resource_limits: dict[str, Any]
    authorization_grant: RegistryExecutionGrant


@runtime_checkable
class AcquisitionProvider(Protocol):
    """Infrastructure protocol beneath Speider; collection operations only."""

    provider_name: str

    def validate_request(self, request: ProviderAcquisitionRequest) -> None: ...

    def start_run(self, request: ProviderAcquisitionRequest) -> ProviderRunHandle: ...

    def get_run_status(self, handle: ProviderRunHandle) -> ProviderRunStatus: ...

    def fetch_dataset(self, handle: ProviderRunHandle) -> RawAcquisitionRecord: ...

    def cancel_run(self, handle: ProviderRunHandle) -> None: ...

    def estimate_cost(self, request: ProviderAcquisitionRequest) -> CostEstimate: ...
