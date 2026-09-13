"""Governed external acquisition for Speider.

Canonical boundary: Apify collects; Speider controls collection and provenance;
BARO receives candidate facts for contextual analysis; VAIG evaluates; REHT clears;
ACS records execution and receipts.
"""

from .anakin import (
    AnakinAcquisitionProvider,
    AnakinProviderConfig,
    AnakinProviderError,
    _AnakinClientLike,
)
from .apify import (
    ApifyAcquisitionProvider,
    ApifyClientLike,
    ApifyProviderConfig,
    ApifyProviderError,
)
from .models import (
    AcquisitionEvent,
    AcquisitionRequest,
    ActorLifecycleState,
    ActorLifecycleTransition,
    ActorRegistryEntry,
    CostEstimate,
    ProviderRunHandle,
    ProviderRunState,
    ProviderRunStatus,
    ProvenanceStep,
    RawAcquisitionRecord,
    RegistryExecutionGrant,
    RetentionRule,
    RunFrequencyLimit,
)
from .provider import (
    AcquisitionProvider,
    AcquisitionProviderError,
    ProviderAcquisitionRequest,
)
from .registry import AcquisitionConstraintError, ActorRegistry
from .service import SpeiderAcquisitionService

__all__ = [
    "AcquisitionConstraintError",
    "AcquisitionEvent",
    "AcquisitionProvider",
    "AcquisitionProviderError",
    "AcquisitionRequest",
    "AnakinAcquisitionProvider",
    "AnakinProviderConfig",
    "AnakinProviderError",
    "_AnakinClientLike",
    "ApifyAcquisitionProvider",
    "ApifyClientLike",
    "ApifyProviderConfig",
    "ApifyProviderError",
    "ActorLifecycleState",
    "ActorLifecycleTransition",
    "ActorRegistry",
    "ActorRegistryEntry",
    "CostEstimate",
    "ProviderAcquisitionRequest",
    "ProviderRunHandle",
    "ProviderRunState",
    "ProviderRunStatus",
    "ProvenanceStep",
    "RawAcquisitionRecord",
    "RegistryExecutionGrant",
    "RetentionRule",
    "RunFrequencyLimit",
    "SpeiderAcquisitionService",
]
