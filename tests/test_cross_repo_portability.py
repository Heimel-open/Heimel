"""Cross-repo portability: valo-edge canonical digest must match platform.

This test only runs when the valo-platform checkout is available on the same
machine (it imports platform's canonical module directly). In CI it is skipped
so valo-edge stays self-contained.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from valo_edge.governance.canonical import canonical_digest as edge_digest

_PLATFORM_ROOT = Path(__file__).resolve().parents[1] / ".." / "valo-platform" / "src"

_HAS_PLATFORM = (
    _PLATFORM_ROOT.is_dir()
    and (_PLATFORM_ROOT / "valo_platform" / "canonical.py").exists()
)


@pytest.mark.skipif(not _HAS_PLATFORM, reason="valo-platform checkout not available")
def test_canonical_digest_portable_with_platform():
    if str(_PLATFORM_ROOT) not in sys.path:
        sys.path.insert(0, str(_PLATFORM_ROOT))
    from valo_platform.canonical import canonical_digest as platform_digest

    payloads = [
        {"a": 1, "b": [1, 2], "c": {"x": "y"}},
        {"source": "sensor", "value": 0.5},
        ["list", "of", "strings"],
        {"nested": {"deep": {"key": "value"}}, "arr": [True, False, None]},
    ]
    for payload in payloads:
        assert edge_digest(payload) == platform_digest(payload), payload
