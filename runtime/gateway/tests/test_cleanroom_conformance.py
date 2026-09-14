import pytest

from valo_gateway.cleanroom_conformance import (
    CleanRoomConformanceError,
    InternalTransfer,
    TransferKind,
    require_clean_room_transfers,
    verify_clean_room_transfers,
)


def transfer(**overrides):
    values = {
        "source_principal": "agent-a",
        "source_workspace": "ws-a",
        "target_principal": "agent-b",
        "target_workspace": "ws-a",
        "kind": TransferKind.MESSAGE,
        "mediated": True,
        "explicitly_authorized": False,
    }
    values.update(overrides)
    return InternalTransfer(**values)


def test_mediated_same_workspace_message_is_allowed():
    result = verify_clean_room_transfers([transfer()])
    assert result.conformant is True


def test_tool_does_not_transfer_merely_because_agents_can_communicate():
    item = transfer(kind=TransferKind.TOOL, mediated=True)
    result = verify_clean_room_transfers([item])
    assert result.conformant is False
    assert result.implicit_capability_transfers == (item,)


@pytest.mark.parametrize(
    "kind",
    [TransferKind.TOOL, TransferKind.AUTHORITY, TransferKind.SECRET, TransferKind.CAPABILITY],
)
def test_capability_bearing_transfer_requires_mediation_and_explicit_authorization(kind):
    item = transfer(kind=kind, mediated=True, explicitly_authorized=True)
    assert verify_clean_room_transfers([item]).conformant is True


def test_ungoverned_cross_workspace_message_is_rejected():
    item = transfer(target_workspace="ws-b", mediated=False)
    result = verify_clean_room_transfers([item])
    assert result.conformant is False
    assert result.ungoverned_cross_workspace_paths == (item,)


def test_cross_workspace_message_may_flow_only_through_mediated_path():
    item = transfer(target_workspace="ws-b", mediated=True)
    assert verify_clean_room_transfers([item]).conformant is True


def test_fail_closed_error_names_both_invariants_when_both_are_broken():
    item = transfer(
        target_workspace="ws-b",
        kind=TransferKind.AUTHORITY,
        mediated=False,
        explicitly_authorized=False,
    )
    with pytest.raises(CleanRoomConformanceError) as exc:
        require_clean_room_transfers([item])
    text = str(exc.value)
    assert "NO_IMPLICIT_CAPABILITY_TRANSFER" in text
    assert "NO_UNGOVERNED_CROSS_WORKSPACE_PATH" in text
