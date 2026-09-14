from datetime import UTC, datetime, timedelta
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_runtime import ConsequenceRejected, LocalPermit, LocalRuntime


def test_never_issued_permit_is_rejected_before_effect():
    runtime = LocalRuntime()
    action_id = runtime.submit({"type": "transfer", "amount": 20, "to": "X"})
    runtime.grant(action_id)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    digest = runtime._actions[action_id]["effect_digest"]

    forged = LocalPermit(
        permit_id="sha256:forged",
        action_id=action_id,
        effect_digest=digest,
        authority_revision=runtime._authority_revision,
        reht_ref="forged",
        racs_ref="forged",
        expires_at=now + timedelta(minutes=1),
    )

    with pytest.raises(ConsequenceRejected, match="not issued"):
        runtime.execute(action_id, forged, now=now)

    assert runtime.receipt(action_id) is None
    assert "EFFECT_EXECUTED" not in [event.kind for event in runtime.stream(action_id)]


def test_issued_id_with_mutated_fields_is_rejected_before_effect():
    runtime = LocalRuntime()
    action_id = runtime.submit({"type": "transfer", "amount": 20, "to": "X"})
    runtime.grant(action_id)
    now = datetime(2026, 9, 14, tzinfo=UTC)
    issued = runtime.authorize(action_id, now=now)
    tampered = LocalPermit(
        permit_id=issued.permit_id,
        action_id=issued.action_id,
        effect_digest=issued.effect_digest,
        authority_revision=issued.authority_revision,
        reht_ref="tampered",
        racs_ref=issued.racs_ref,
        expires_at=issued.expires_at,
    )

    with pytest.raises(ConsequenceRejected, match="does not match issued"):
        runtime.execute(action_id, tampered, now=now + timedelta(seconds=1))

    assert runtime.receipt(action_id) is None
