from __future__ import annotations

from valo_reht import RealReht

NOW = "2026-08-19T18:40:00+00:00"


def authority(capability: str, target: str) -> dict:
    return {
        "authority_id": f"auth:{capability}:{target}",
        "principal": "agent-1",
        "capability": capability,
        "scope": [target],
        "constraints": {},
        "validity": {
            "valid_from": "2026-01-01T00:00:00+00:00",
            "valid_until": "2030-01-01T00:00:00+00:00",
        },
        "status": "ACTIVE",
    }


def ctx(authorities: list[dict]) -> dict:
    return {
        "actor": "agent-1",
        "identity": "id-agent-1",
        "time": {"now": NOW},
        "authority": authorities,
    }


def action(capability: str, target: str) -> dict:
    return {
        "capability": capability,
        "target": target,
        "action_type": capability,
    }


def test_individually_allowed_steps_do_not_compose_into_ungranted_effect() -> None:
    reht = RealReht()
    context = ctx(
        [
            authority("READ_REPORT", "report:1"),
            authority("WRITE_SUMMARY", "summary:1"),
        ]
    )

    first = reht.authorize(context, action("READ_REPORT", "report:1"))
    second = reht.authorize(context, action("WRITE_SUMMARY", "summary:1"))
    composed = reht.authorize(context, action("PUBLISH_EXTERNAL", "external:public"))

    assert first.decision == "ALLOW"
    assert second.decision == "ALLOW"
    assert composed.decision == "DENY"


def test_prior_allow_does_not_authorize_newly_visible_credential_effect() -> None:
    reht = RealReht()
    context = ctx([authority("READ_REPORT", "report:1")])

    prior = reht.authorize(context, action("READ_REPORT", "report:1"))
    credential_use = reht.authorize(
        context,
        action("USE_CREDENTIAL", "credential:service-account"),
    )

    assert prior.decision == "ALLOW"
    assert credential_use.decision == "DENY"


def test_material_authority_change_requires_fresh_authorization() -> None:
    reht = RealReht()
    active = ctx([authority("WRITE_SUMMARY", "summary:1")])

    prior = reht.authorize(active, action("WRITE_SUMMARY", "summary:1"))
    assert prior.decision == "ALLOW"

    revoked_authority = {
        **active["authority"][0],
        "status": "REVOKED",
    }
    changed = {**active, "authority": [revoked_authority]}

    continued = reht.authorize(changed, action("WRITE_SUMMARY", "summary:1"))
    assert continued.decision == "DENY"
