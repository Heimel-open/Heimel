from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .common import utcnow


class WorkflowEventType(str, Enum):
    WORKFLOW_STARTED = "WorkflowStarted"
    NODE_READY = "NodeReady"
    NODE_STARTED = "NodeStarted"
    NODE_COMPLETED = "NodeCompleted"
    NODE_DEFERRED = "NodeDeferred"
    NODE_FAILED = "NodeFailed"
    AUTHORIZATION_REQUESTED = "AuthorizationRequested"
    AUTHORIZATION_GRANTED = "AuthorizationGranted"
    AUTHORIZATION_DENIED = "AuthorizationDenied"
    ACTION_REQUESTED = "ActionRequested"
    ACTION_EXECUTED = "ActionExecuted"
    EFFECT_VERIFIED = "EffectVerified"
    COMPENSATION_STARTED = "CompensationStarted"
    WORKFLOW_COMPLETED = "WorkflowCompleted"
    WORKFLOW_FAILED = "WorkflowFailed"
    WORKFLOW_HALTED = "WorkflowHalted"


class WorkflowEvent(BaseModel):
    """Append-only workflow event. All events carry the instance and node
    identity plus correlation_id and an execution-context hash where relevant."""

    event_type: WorkflowEventType
    workflow_instance_id: str
    graph_id: str
    graph_version: str
    node_id: str | None = None
    attempt: int = 1
    correlation_id: str | None = None
    execution_context_hash: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(extra="forbid", frozen=True)
