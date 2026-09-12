from __future__ import annotations

import pytest

from valo_workflow_isa.testing import (
    DictKernel,
    FakeBaro,
    FakeGateway,
    FakePorts,
    FakeReht,
    FakeVeritas,
)

__all__ = [
    "DictKernel",
    "FakeBaro",
    "FakeGateway",
    "FakePorts",
    "FakeReht",
    "FakeVeritas",
]


@pytest.fixture
def fake_ports() -> FakePorts:
    return FakePorts(
        kernel=DictKernel(),
        reht=FakeReht(),
        gateway=FakeGateway(),
        veritas=FakeVeritas(),
        baro=FakeBaro(),
    )
