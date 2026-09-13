"""Minimal deployment bootstrap for the canonical VAIG Coherence evaluator.

The bootstrap deliberately avoids importing ``vaig.__init__``. It exposes the
repository's canonical Coherence modules as a package path and then imports the
existing FastAPI application unchanged.
"""
from __future__ import annotations

from pathlib import Path
import sys
import types

_package = types.ModuleType("vaig")
_package.__path__ = [str(Path(__file__).resolve().parent / "vaig")]
_package.__package__ = "vaig"
sys.modules.setdefault("vaig", _package)

from vaig.coherence_api import app  # noqa: E402

__all__ = ["app"]
