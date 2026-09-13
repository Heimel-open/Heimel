"""valo-runtime-core — canonical interfaces (no implementation).

Every runtime adapter and tool adapter MUST implement these protocols exactly.
The contract test suites in tests/ enforce this across all vendors.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Decision(str, Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    STEP_UP = "STEP_UP"
    DEFER = "DEFER"
    DENY = "DENY"
    HALT = "HALT"


@dataclass
class Event:
    """Canonical event in the runtime event stream."""
    id: str
    kind: str                 # e.g. ACTION_REQUESTED, CHECKPOINT, RESULT, DECISION
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None


@dataclass
class Checkpoint:
    """Checkpoint contract — deterministic restart point."""
    id: str
    step: int
    state_ref: str            # opaque handle to serialized state
    digest: str              # sha256 of the serialized state
    parent: Optional[str] = None


@dataclass
class Result:
    """Result contract — what an executed action returns."""
    action_id: str
    status: str              # SUCCESS | FAILURE | PARTIAL
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    receipt_ref: Optional[str] = None


@dataclass
class AuthorizationReceipt:
    """Veritas receipt for an authorized action."""
    action_id: str
    decision: Decision
    reht_ref: str
    racs_ref: str
    veritas_ref: str
    timestamp: str
    chain: List[str] = field(default_factory=list)   # checkpoint chain ids


class RuntimeInterface(ABC):
    """Every runtime adapter implements this."""

    @abstractmethod
    def submit(self, action: Dict[str, Any]) -> str:
        """Submit an action request. Returns action_id. Does NOT execute."""
        ...

    @abstractmethod
    def stream(self, action_id: str) -> List[Event]:
        """Return the event stream for an action."""
        ...

    @abstractmethod
    def checkpoint(self, action_id: str) -> Checkpoint:
        """Create a checkpoint for restart."""
        ...

    @abstractmethod
    def restart(self, checkpoint_id: str) -> str:
        """Restart execution from a checkpoint. Returns action_id."""
        ...

    @abstractmethod
    def result(self, action_id: str) -> Result:
        """Return the result contract for an action."""
        ...


class ToolInterface(ABC):
    """Every tool adapter implements this. May NOT act directly — only via REHT."""

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def capabilities(self) -> List[str]:
        ...

    @abstractmethod
    def invoke(self, authorized_request: Dict[str, Any]) -> Result:
        """Execute ONLY an authorized (REHT-cleared, RACS-bound) request."""
        ...


class REHTGateway(ABC):
    """All actions pass through REHT. No adapter calls a tool directly."""

    @abstractmethod
    def evaluate(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """REHT evaluates evidence/risk/signal -> evaluation (no exec authority)."""
        ...


class RACSController(ABC):
    """RACS binds the decision. Does not originate authority."""

    @abstractmethod
    def decide(self, reht_evaluation: Dict[str, Any]) -> Decision:
        ...


class VeritasRecorder(ABC):
    """Veritas records every authorization and the checkpoint chain."""

    @abstractmethod
    def record(self, receipt: AuthorizationReceipt) -> str:
        ...

    @abstractmethod
    def replay(self, action_id: str) -> List[AuthorizationReceipt]:
        ...
