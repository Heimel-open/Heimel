from datetime import UTC, datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_runtime import LocalRuntime


def test_required_evidence_fail_closes_before_authorization():
    runtime = LocalRuntime()
    aid = runtime.submit({
        "type": "payment",
        "actor_id": "agent-1",
        "target": "merchant-1",
        "payload": {"amount": 10, "currency": "EUR"},
        "evidence_requirement": "REQUIRED",
    })
    runtime.grant(aid)

    with pytest.raises(RuntimeError, match="evidence .*admissible"):
        runtime.authorize(aid, now=datetime(2026, 9, 18, tzinfo=UTC))
