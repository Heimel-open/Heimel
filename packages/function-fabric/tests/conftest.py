from __future__ import annotations

import pytest

from valo_function_fabric.stdlib import build_stdlib


@pytest.fixture
def stdlib_registry():
    return build_stdlib()


@pytest.fixture
def snapshot(stdlib_registry):
    return stdlib_registry.snapshot()

