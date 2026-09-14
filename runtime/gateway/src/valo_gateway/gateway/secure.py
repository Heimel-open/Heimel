from __future__ import annotations

from typing import Any

from .core import ToolExecutionResult, ValoGateway as _CoreValoGateway


class ValoGateway(_CoreValoGateway):
    """Public Gateway that requires authoritative live control state at effect time.

    The legacy core implementation accepted execution when no RuntimeControlPlane
    was supplied. That makes a caller-held AuthorityEnvelope the effective source
    of truth and permits stale-authority execution after canonical revocation.

    Public Gateway execution therefore fails closed unless an authoritative
    RuntimeControlPlane is supplied either at construction time or per execute().
    """

    def execute(self, *args: Any, **kwargs: Any) -> ToolExecutionResult:
        active = kwargs.get("control_plane") or self._control_plane
        if active is None:
            raise ValueError(
                "fresh authoritative control plane is required at consequence time"
            )
        return super().execute(*args, **kwargs)
