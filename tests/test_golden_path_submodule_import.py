"""Ensure the golden-path runtime is exposed as a canonical l2_orchestrator submodule."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _bootstrap_l2() -> None:
    l2_dir = ROOT / "l2-orchestrator"
    pkg_spec = importlib.util.spec_from_file_location(
        "l2_orchestrator",
        l2_dir / "__init__.py",
        submodule_search_locations=[str(l2_dir)],
    )
    pkg = importlib.util.module_from_spec(pkg_spec)
    sys.modules["l2_orchestrator"] = pkg
    assert pkg_spec.loader is not None
    pkg_spec.loader.exec_module(pkg)


_bootstrap_l2()
from l2_orchestrator import BridgeFactory  # noqa: E402


def test_golden_path_is_importable_as_a_package_submodule():
    BridgeFactory.load()

    import l2_orchestrator.golden_path as golden_path  # noqa: E402

    assert hasattr(golden_path, "RacsGoldenPathRuntime")
    assert golden_path.RacsGoldenPathRuntime.__name__ == "RacsGoldenPathRuntime"
