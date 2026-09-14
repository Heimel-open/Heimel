from __future__ import annotations

from typing import Any

from . import core as _core
from .core import ToolExecutionResult
from .core import ValoGateway as _CoreValoGateway


class ValoGateway(_CoreValoGateway):
    """Gateway requiring authoritative live control state at effect time."""

    def execute(self, *args: Any, **kwargs: Any) -> ToolExecutionResult:
        active = kwargs.get("control_plane") or self._control_plane
        if active is None:
            raise ValueError(
                "fresh authoritative control plane is required at consequence time"
            )
        return super().execute(*args, **kwargs)


_core.ValoGateway = ValoGateway

__all__ = ["ValoGateway"]
