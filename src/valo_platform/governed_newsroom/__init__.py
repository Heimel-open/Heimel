"""VALO Governed Newsroom shadow package.

Scout acquires. BARO models. Verification Factory verifies. VAIG evaluates.
REHT clears. RACS binds and enforces. This package stops before clearance.
"""

from .evaluator import evaluate_newsroom_shadow
from .models import (
    NewsroomActionType,
    NewsroomGovernanceInputs,
    NewsroomRiskTier,
    NewsroomShadowEvaluation,
)
from .persistence import persist_newsroom_shadow
from .pilot_future_newsroom import (
    AUDIENCERS_URL,
    STUDY_URL,
    FutureNewsroomPilotCase,
    build_future_newsroom_pilot,
)

__all__ = [
    "AUDIENCERS_URL",
    "STUDY_URL",
    "FutureNewsroomPilotCase",
    "NewsroomActionType",
    "NewsroomGovernanceInputs",
    "NewsroomRiskTier",
    "NewsroomShadowEvaluation",
    "build_future_newsroom_pilot",
    "evaluate_newsroom_shadow",
    "persist_newsroom_shadow",
]
