from datetime import datetime, timedelta, timezone

import pytest

from heimel_boundary import (
    InformationBoundary,
    InformationBoundaryError,
    InformationObject,
)


NOW = datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc)


def source() -> InformationObject:
    return InformationObject.from_payload(
        "customer-packet-1",
        "org:acme",
        {"pricing": [1, 2, 3], "note": "internal"},
        classification="CONFIDENTIAL",
    )


def grant(boundary: InformationBoundary, information: InformationObject, **overrides):
    params = {
        "actor_id": "actor:cole",
        "purpose": "account-analysis",
        "allowed_tools": ("model:external",),
        "now": NOW,
        "allow_derivation": True,
        "allow_egress": True,
        "allow_state_admission": False,
    }
    params.update(overrides)
    return boundary.issue_grant(information, **params)


def open_session(boundary: InformationBoundary, issued):
    return boundary.open_session(
        issued,
        actor_id="actor:cole",
        purpose="account-analysis",
        tool_id="model:external",
        now=NOW,
    )


def test_exact_object_actor_purpose_and_tool_are_bound_before_admission():
    boundary = InformationBoundary()
    information = source()
    issued = grant(boundary, information)
    session = open_session(boundary, issued)

    receipt = boundary.admit(
        session,
        issued,
        information,
        actor_id="actor:cole",
        purpose="account-analysis",
        tool_id="model:external",
        now=NOW,
    )
    assert receipt.event == "ADMIT"
    assert receipt.object_digest == information.digest

    other = InformationObject.from_payload("other", "org:acme", {"x": 1})
    with pytest.raises(InformationBoundaryError, match="exact information object"):
        boundary.admit(
            session,
            issued,
            other,
            actor_id="actor:cole",
            purpose="account-analysis",
            tool_id="model:external",
            now=NOW,
        )

    with pytest.raises(InformationBoundaryError, match="purpose mismatch"):
        boundary.admit(
            session,
            issued,
            information,
            actor_id="actor:cole",
            purpose="different-purpose",
            tool_id="model:external",
            now=NOW,
        )


def test_derivative_keeps_authority_and_source_lineage():
    boundary = InformationBoundary()
    information = source()
    issued = grant(boundary, information)
    session = open_session(boundary, issued)

    derivative, receipt = boundary.derive(
        session,
        issued,
        information,
        derived_object_id="summary-1",
        derived_payload={"summary": "bounded derivative"},
        actor_id="actor:cole",
        purpose="account-analysis",
        tool_id="model:external",
        now=NOW,
    )

    assert derivative.authority_id == information.authority_id
    assert derivative.parent_digests == (information.digest,)
    assert receipt.event == "DERIVE"
    assert receipt.result_digest == derivative.digest

    egress = boundary.egress(
        session,
        issued,
        derivative,
        actor_id="actor:cole",
        purpose="account-analysis",
        tool_id="model:external",
        now=NOW,
    )
    assert egress.event == "EGRESS"


def test_state_admission_is_separate_from_egress():
    boundary = InformationBoundary()
    information = source()
    issued = grant(boundary, information, allow_state_admission=False)
    session = open_session(boundary, issued)
    derivative, _ = boundary.derive(
        session,
        issued,
        information,
        derived_object_id="summary-1",
        derived_payload={"summary": "advice"},
        actor_id="actor:cole",
        purpose="account-analysis",
        tool_id="model:external",
        now=NOW,
    )

    boundary.egress(
        session,
        issued,
        derivative,
        actor_id="actor:cole",
        purpose="account-analysis",
        tool_id="model:external",
        now=NOW,
    )

    with pytest.raises(InformationBoundaryError, match="state admission not allowed"):
        boundary.admit_state(
            session,
            issued,
            derivative,
            actor_id="actor:cole",
            purpose="account-analysis",
            tool_id="model:external",
            now=NOW,
        )


def test_session_closure_ends_future_use():
    boundary = InformationBoundary()
    information = source()
    issued = grant(boundary, information)
    session = open_session(boundary, issued)

    close_receipt = boundary.close_session(session)
    assert close_receipt.event == "CLOSE"

    with pytest.raises(InformationBoundaryError, match="session closed"):
        boundary.admit(
            session,
            issued,
            information,
            actor_id="actor:cole",
            purpose="account-analysis",
            tool_id="model:external",
            now=NOW,
        )


def test_revocation_and_expiry_fail_closed():
    boundary = InformationBoundary()
    information = source()
    issued = grant(boundary, information)
    boundary.revoke_grant(issued.grant_id)

    with pytest.raises(InformationBoundaryError, match="revoked"):
        boundary.open_session(
            issued,
            actor_id="actor:cole",
            purpose="account-analysis",
            tool_id="model:external",
            now=NOW,
        )

    fresh_boundary = InformationBoundary()
    expiring = grant(fresh_boundary, information, ttl_seconds=1)
    with pytest.raises(InformationBoundaryError, match="expired"):
        fresh_boundary.open_session(
            expiring,
            actor_id="actor:cole",
            purpose="account-analysis",
            tool_id="model:external",
            now=NOW + timedelta(seconds=2),
        )


def test_unrelated_derivative_cannot_cross_or_enter_state():
    boundary = InformationBoundary()
    information = source()
    issued = grant(boundary, information, allow_state_admission=True)
    session = open_session(boundary, issued)
    unrelated = InformationObject.from_payload(
        "other-source",
        "org:other",
        {"summary": "not derived from granted source"},
    )

    with pytest.raises(InformationBoundaryError, match="outside granted lineage"):
        boundary.egress(
            session,
            issued,
            unrelated,
            actor_id="actor:cole",
            purpose="account-analysis",
            tool_id="model:external",
            now=NOW,
        )
