"""VALO Company Voice — governed multi-audience communication infrastructure.

Issue #674. This package is introduced incrementally. The minimal slice landed
here is Phase 1 of the issue:

  - disabled-by-default activation gate (fails CLOSED)
  - canonical organizational record (the canonical reality every audience
    projection derives from)
  - audience + personal context projections
  - communication envelope (every artifact must carry one)
  - claim taxonomy + classification + regulated-advice boundary

Later phases (governance integration, script/audio providers, delivery,
corrections, subscriptions, demos) build on this foundation and MUST route
every generation attempt through the activation gate and envelope.
"""

from .activation import (
    CompanyVoiceActivationState,
    CompanyVoiceGenerationError,
    CompanyVoicePreferences,
    require_generation_allowed,
)
from .models import (
    AudienceType,
    ChannelType,
    ClaimType,
    CommunicationEnvelope,
    PersonalContextProjection,
    SensitivityLevel,
    CanonicalOrganizationRecord,
    AudienceContext,
    PublicationMode,
)
from .claims import (
    ClaimSpec,
    classify_claim,
)
from .audience_context import (
    AudienceContextResolver,
)

__all__ = [
    "CompanyVoiceActivationState",
    "CompanyVoiceGenerationError",
    "CompanyVoicePreferences",
    "require_generation_allowed",
    "AudienceType",
    "ChannelType",
    "ClaimType",
    "CommunicationEnvelope",
    "PersonalContextProjection",
    "SensitivityLevel",
    "CanonicalOrganizationRecord",
    "AudienceContext",
    "PublicationMode",
    "ClaimSpec",
    "classify_claim",
    "AudienceContextResolver",
]
