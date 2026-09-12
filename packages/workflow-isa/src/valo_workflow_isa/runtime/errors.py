from __future__ import annotations


class WorkflowError(RuntimeError):
    """Base class for workflow runtime failures."""


class NodeFailure(WorkflowError):
    """A node handler failed during execution."""


class AuthorizationDenied(NodeFailure):
    """REHT port did not grant authorization (DENY/DEFER/STEP_UP/HALT)."""


class PostconditionFailed(NodeFailure):
    """BARO found the expected postcondition did not arise."""


class WorkflowHalted(WorkflowError):
    """A HALT was encountered; execution stops."""


class NodeTimeout(WorkflowError):
    """A node exceeded its timeout."""


class TypeViolation(WorkflowError):
    """A produced value could not satisfy a required input type at runtime."""


class Deferred(WorkflowError):
    """A WAIT/DECIDE node needs external input; the workflow defers until it
    is resumed."""
