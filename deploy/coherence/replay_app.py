"""Minimal deployment bootstrap for canonical VAIG second-operator replay.

This starts only the dedicated Coherence replay surface and deliberately avoids
executing the broad ``vaig.__init__`` import surface.
"""
from __future__ import annotations

from pathlib import Path
import sys
import types

_package = types.ModuleType("vaig")
_package.__path__ = [str(Path(__file__).resolve().parent / "vaig")]
_package.__package__ = "vaig"
sys.modules.setdefault("vaig", _package)

from vaig.coherence_replay_api import app  # noqa: E402

__all__ = ["app"]
