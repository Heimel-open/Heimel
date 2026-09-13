from __future__ import annotations

from datetime import UTC, datetime, timedelta

from valo_kernel.contracts.common import canonical_digest
from valo_kernel.kernel.uniform import build_governed_uniform


def _digest(label: str) -> str:
    return canonical_digest({"label": label})


def _validity(now: datetime, minutes: int = 10) -> dict[str, str]:
    return {
        "valid_from": (now - timedelta(minutes=1)).isoformat(),
        "valid_until": (now + timedelta(minutes=minutes)).isoformat(),
    }


def _context(now: datetime) -> dict:
    return {
        "tenant_id": "tenant:1",
        "actor": "agent:1",
        "identity": "identity:1",
        "authority": [
            {
                "authority_id": "authority:2",
                "principal": "agent:1",
                "capability": "payment.submit",
                "validity": _validity(now),
            },
            {
                "authority_id": "authority:1",
                "principal": "agent:1",
                "capability": "payment.submit",
                "validity": _validity(now),
            },
            {
                "authority_id": "authority:unrelated",
                "principal": "agent:1",
                "capability": "invoice.read",
                "validity": _validity(now),
            },
        ],
        "delegation": [
            {
                "delegation_id": "delegation:1",
                "authority_ref": "authority:1",
                "validity": _validity(now, minutes=8),
            },
            {
                "delegation_id": "delegation:unrelated",
                "authority_ref": "authority:unrelated",
                "validity": _validity(now),
            },
        ],
        "purpose": {
            "purpose_id": "purpose:settle",
            "validity": _validity(now, minutes=7),
        },
        "constraints": [{"constraint_id": "constraint:limit"}],
        "evidence": [{"evidence_id": "evidence:standing"}],
        "time": {"now": now.isoformat()},
        "state_ref": "state:42",
    }


def test_build_governed_uniform_projects_existing_execution_context() -> None:
    now = datetime.now(UTC)
    context = _context(now)

    uniform = build_governed_uniform(
        context,
        uniform_id="uniform:1",
        capability="payment.submit",
        target="invoice:123",
        action_digest=_digest("action"),
        valid_until=now + timedelta(minutes=5),
        permitted_effect_classes=("PAYMENT",),
        consequence_ref="consequence:invoice-123",
        revocation_epoch=7,
    )

    assert uniform.actor_id == context["actor"]
    assert uniform.identity_ref == context["identity"]
    assert uniform.authority_refs == ("authority:1", "authority:2")
    assert uniform.delegation_refs == ("delegation:1",)
    assert uniform.purpose_ref == "purpose:settle"
    assert uniform.constraint_refs == ("constraint:limit",)
    assert uniform.evidence_refs == ("evidence:standing",)
    assert uniform.state_ref == "state:42"
    assert uniform.source_context_digest == canonical_digest(context)
    assert uniform.can_issue_clearance is False
    assert uniform.can_authorize_execution is False


def test_build_governed_uniform_rejects_missing_matching_authority() -> None:
    now = datetime.now(UTC)
    context = _context(now)

    try:
        build_governed_uniform(
            context,
            uniform_id="uniform:1",
            capability="payment.override",
            target="invoice:123",
            action_digest=_digest("action"),
            valid_until=now + timedelta(minutes=5),
        )
    except ValueError as exc:
        assert "no authority bound to actor and capability" in str(exc)
    else:
        raise AssertionError("uniform projection must fail without matching authority")


def test_build_governed_uniform_cannot_outlive_shortest_dependency() -> None:
    now = datetime.now(UTC)
    context = _context(now)

    try:
        build_governed_uniform(
            context,
            uniform_id="uniform:1",
            capability="payment.submit",
            target="invoice:123",
            action_digest=_digest("action"),
            valid_until=now + timedelta(minutes=9),
        )
    except ValueError as exc:
        assert "exceeds shortest authority/delegation/purpose validity" in str(exc)
    else:
        raise AssertionError("uniform must not widen dependency validity")
