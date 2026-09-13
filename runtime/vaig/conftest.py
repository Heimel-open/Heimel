"""Root pytest import configuration.

The repository still contains legacy experimental modules under ``src/`` and a
self-contained VACS implementation under ``vacs/src``. They are not installed as
part of the canonical ``vaig`` package, but their retained tests must remain
collectable from a clean CI environment.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_VACS_SRC = _REPO_ROOT / "vacs" / "src"

for path in (_REPO_ROOT, _VACS_SRC):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
