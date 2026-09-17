from datetime import UTC, datetime, timedelta

import pytest

from valo_external_adapters.contracts import Authority, Delegation, TimeWindow
from valo_external_adapters.paseo import (
    PaseoAgentContext,
    PaseoEffectCandidate,
    bind_paseo_effect_for_reht,
)

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=UTC)


def _authority(*, principal: str = "agent-parent", delegable: bool = True) -> Authority:
    return Authority(
        authority_id="authority-1",
        principal=principal,
        capability="WRITE_REPOSITORY",
        scope=["repo:Heimel-open/Heimel"],
        constraints={"branch": "feat/paseo-authority-adapter"},
        basis="human-principal-approval-1",
        validity=TimeWindow(
            valid_from=NOW - timedelta(minutes=5),
            valid_until=NOW + timedelta(minutes=5),
        ),
        delegable=delegable,
    )


def _candidate(*, agent_id: str = "agent-child") -> PaseoEffectCandidate:
    return PaseoEffectCandidate(
        agent_id=agent_id,
        workspace_id="workspace-1",
        provider_id="codex",
        action="WRITE_REPOSITORY",
        resource="repo:Heimel-open/Heimel",
        parameters={"branch": "feat/paseo-authority-adapter"},
        proposed_at=NOW - timedelta(seconds=30),
    )


def test_child_provider_policy_does_not_inherit_parent_authority() -> None:
    context = PaseoAgentContext(
        agent_id="agent-child",
        parent_agent_id="agent-parent",
        workspace_id="workspace-1",
        provider_id="codex",
        exposed_tools=("send_terminal_keys", "create_agent"),
    )

    with pytest.raises(ValueError, match="explicit active delegation"):
        bind_paseo_effect_for_reht(
            context=context,
            candidate=_candidate(),
            authority=_authority(),
            delegation=None,
            consequence_at=NOW,
        )


def test_explicit_delegation_may_narrow_but_never_expand_parent_authority() -> None:
    context = PaseoAgentContext(
        agent_id="agent-child",
        parent_agent_id="agent-parent",
        workspace_id="workspace-1",
        provider_id="codex",
        exposed_tools=("send_terminal_keys",),
    )
    delegation = Delegation(
        delegation_id="delegation-1",
        delegator="agent-parent",
        delegate="agent-child",
        authority_ref="authority-1",
        scope_reduction=["repo:Heimel-open/Heimel"],
        validity=TimeWindow(
            valid_from=NOW - timedelta(minutes=1),
            valid_until=NOW + timedelta(minutes=1),
        ),
    )

    binding = bind_paseo_effect_for_reht(
        context=context,
        candidate=_candidate(),
        authority=_authority(),
        delegation=delegation,
        consequence_at=NOW,
    )

    assert binding.authority_ref == "authority-1"
    assert binding.delegation_ref == "delegation-1"
    assert binding.requires_fresh_reht_evaluation is True
    assert binding.paseo_tool_policy_is_authority is False
    assert binding.can_execute_external_effects is False
    assert binding.authority_effect == "NO_AUTHORITY_CREATION"


def test_consequence_time_guard_rejects_stale_authority() -> None:
    expired = Authority(
        authority_id="authority-expired",
        principal="agent-child",
        capability="WRITE_REPOSITORY",
        scope=["repo:Heimel-open/Heimel"],
        constraints={},
        basis="approval-1",
        validity=TimeWindow(
            valid_from=NOW - timedelta(minutes=10),
            valid_until=NOW - timedelta(seconds=1),
        ),
    )
    context = PaseoAgentContext(
        agent_id="agent-child",
        workspace_id="workspace-1",
        provider_id="codex",
    )

    with pytest.raises(ValueError, match="not active at consequence time"):
        bind_paseo_effect_for_reht(
            context=context,
            candidate=_candidate(),
            authority=expired,
            delegation=None,
            consequence_at=NOW,
        )


def test_tool_visibility_never_grants_effect_authority() -> None:
    context = PaseoAgentContext(
        agent_id="agent-child",
        workspace_id="workspace-1",
        provider_id="codex",
        exposed_tools=("send_terminal_keys", "kill_terminal", "create_agent"),
    )

    with pytest.raises(ValueError, match="principal does not match Paseo agent"):
        bind_paseo_effect_for_reht(
            context=context,
            candidate=_candidate(),
            authority=_authority(principal="different-agent"),
            delegation=None,
            consequence_at=NOW,
        )
