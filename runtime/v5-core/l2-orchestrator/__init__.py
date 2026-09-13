# l2-orchestrator/__init__.py
# BridgeFactory: thread-safe singleton loader for ValoBridge.
# Fase 3: registers codec + observability in sys.modules before loading
# bridge.py so its package-relative imports resolve correctly.

import sys
import pathlib
from typing import Tuple, Type
import importlib.util
from threading import Lock


class BridgeFactory:
    """
    Singleton factory for loading ValoBridge + Decision.

    Thread-safe for async/multi-threaded contexts (asyncio, threading).
    Registers l2_orchestrator.codec and l2_orchestrator.observability in
    sys.modules before executing bridge.py, so bridge.py's
    `from l2_orchestrator.codec import Transport` resolves correctly.

    Usage:
        ValoBridge, Decision = BridgeFactory.load()
    """

    _lock = Lock()
    _loaded_module = None
    _bridge_class = None
    _decision_class = None

    @classmethod
    def load(cls, bridge_path: pathlib.Path = None) -> Tuple[Type, Type]:
        """
        Load ValoBridge + Decision once, then cache. Thread-safe.

        Args:
            bridge_path: Custom path to bridge.py (defaults to sibling bridge.py).

        Returns:
            (ValoBridge class, Decision enum)
        """
        if cls._bridge_class is not None:
            return cls._bridge_class, cls._decision_class

        with cls._lock:
            if cls._bridge_class is not None:
                return cls._bridge_class, cls._decision_class

            l2_dir = pathlib.Path(__file__).parent

            # Register package itself
            if "l2_orchestrator" not in sys.modules:
                pkg_spec = importlib.util.spec_from_file_location(
                    "l2_orchestrator",
                    l2_dir / "__init__.py",
                    submodule_search_locations=[str(l2_dir)],
                )
                pkg = importlib.util.module_from_spec(pkg_spec)
                sys.modules["l2_orchestrator"] = pkg

            # Register submodules codec + observability + golden_path BEFORE bridge.py.
            # bridge.py imports codec/observability by top-level name, and the
            # permit runtime imports golden_path through the package.
            # Register each module under both the package name and the bare
            # name it is imported by.
            for sub in ("codec", "observability"):
                mod_name = f"l2_orchestrator.{sub}"
                if mod_name not in sys.modules:
                    sub_spec = importlib.util.spec_from_file_location(
                        mod_name, l2_dir / f"{sub}.py"
                    )
                    sub_mod = importlib.util.module_from_spec(sub_spec)
                    sys.modules[mod_name] = sub_mod
                    sub_spec.loader.exec_module(sub_mod)
                sys.modules.setdefault(sub, sys.modules[mod_name])

            golden_mod_name = "l2_orchestrator.golden_path"
            if golden_mod_name not in sys.modules:
                golden_spec = importlib.util.spec_from_file_location(
                    golden_mod_name, l2_dir / "src" / "golden_path.py"
                )
                golden_mod = importlib.util.module_from_spec(golden_spec)
                sys.modules[golden_mod_name] = golden_mod
                golden_spec.loader.exec_module(golden_mod)
            sys.modules.setdefault("golden_path", sys.modules[golden_mod_name])

            # Now load bridge.py — its imports resolve from sys.modules
            if bridge_path is None:
                bridge_path = l2_dir / "bridge.py"

            bridge_spec = importlib.util.spec_from_file_location(
                "l2_orchestrator.bridge", bridge_path
            )
            bridge_mod = importlib.util.module_from_spec(bridge_spec)
            sys.modules["l2_orchestrator.bridge"] = bridge_mod
            bridge_spec.loader.exec_module(bridge_mod)

            cls._loaded_module = bridge_mod
            cls._bridge_class = bridge_mod.ValoBridge
            cls._decision_class = bridge_mod.Decision

            return cls._bridge_class, cls._decision_class


__all__ = ["BridgeFactory"]
