from __future__ import annotations

from typing import Any

from . import core as _core
from .core import ToolExecutionResult, ValoGateway as _CoreValoGateway


class ValoGateway(_CoreValoGateway):
    """Gateway that requires authoritative live control state at effect time.

    The legacy core implementation accepted execution when no RuntimeControlPlane
    was supplied. That makes a caller-held AuthorityEnvelope the effective source
    of truth and permits stale-authority execution after canonical revocation.

    Gateway execution therefore fails closed unless an authoritative
    RuntimeControlPlane is supplied either at construction time or per execute().
    """

    def execute(self, *args: Any, **kwargs: Any) -> ToolExecutionResult:
        active = kwargs.get("control_plane") or self._control_plane
        if active is None:
            raise ValueError(
                "fresh authoritative control plane is required at consequence time"
            )
        return super().execute(*args, **kwargs)


# Importing valo_gateway.gateway.core necessarily initializes the gateway package
# first. Replace the module export too so direct core imports cannot recover the
# legacy fail-open class after package initialization.
_core.ValoGateway = ValoGateway
