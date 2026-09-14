from __future__ import annotations

from typing import Any

from ..harness_conformance import HarnessAdmissionEvidence, require_harness_admission
from .runtime import RuntimeAdapter


class HarnessRouter:
    def __init__(self, runtimes: dict[str, RuntimeAdapter], default: str = "local") -> None:
        if default not in runtimes:
            raise ValueError("default runtime is not registered")
        self._runtimes = dict(runtimes)
        self.default = default

    def select(self, name: str | None = None) -> RuntimeAdapter:
        key = name or self.default
        try:
            return self._runtimes[key]
        except KeyError as exc:
            raise KeyError(f"runtime adapter not registered: {key}") from exc

    def submit(
        self,
        action: dict[str, Any],
        runtime: str | None = None,
        *,
        harness_admission: HarnessAdmissionEvidence | None = None,
    ) -> str:
        """Submit internal work, governing harness admission when consequence-bearing.

        Non-consequence-bearing analysis/simulation may run without a harness
        admission receipt. Any action marked ``consequence_bearing=True`` must
        pass the governed harness airlock before reaching a runtime adapter.
        """
        if action.get("consequence_bearing") is True:
            if harness_admission is None:
                raise ValueError(
                    "consequence-bearing harness action requires governed harness admission"
                )
            require_harness_admission(harness_admission)
        return self.select(runtime).submit(action)
