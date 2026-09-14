from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class CleanRoomConformanceError(ValueError):
    pass


class TransferKind(str, Enum):
    MESSAGE = "MESSAGE"
    TOOL = "TOOL"
    AUTHORITY = "AUTHORITY"
    SECRET = "SECRET"
    CAPABILITY = "CAPABILITY"


_CAPABILITY_BEARING = frozenset(
    {
        TransferKind.TOOL,
        TransferKind.AUTHORITY,
        TransferKind.SECRET,
        TransferKind.CAPABILITY,
    }
)


@dataclass(frozen=True)
class InternalTransfer:
    source_principal: str
    source_workspace: str
    target_principal: str
    target_workspace: str
    kind: TransferKind
    mediated: bool
    explicitly_authorized: bool = False

    @property
    def cross_workspace(self) -> bool:
        return self.source_workspace != self.target_workspace

    @property
    def capability_bearing(self) -> bool:
        return self.kind in _CAPABILITY_BEARING


@dataclass(frozen=True)
class CleanRoomConformanceResult:
    conformant: bool
    implicit_capability_transfers: tuple[InternalTransfer, ...]
    ungoverned_cross_workspace_paths: tuple[InternalTransfer, ...]


def verify_clean_room_transfers(
    transfers: Iterable[InternalTransfer],
) -> CleanRoomConformanceResult:
    """Verify internal clean-room communication and capability boundaries.

    Messages may flow when mediated. Capability-bearing material never becomes
    transferable merely because two principals can communicate: it requires an
    explicit authorization in addition to mediation. Cross-workspace traffic
    must always be mediated, regardless of payload type.
    """
    items = tuple(transfers)
    implicit = tuple(
        item
        for item in items
        if item.capability_bearing
        and (not item.mediated or not item.explicitly_authorized)
    )
    cross_workspace = tuple(
        item for item in items if item.cross_workspace and not item.mediated
    )
    return CleanRoomConformanceResult(
        conformant=not implicit and not cross_workspace,
        implicit_capability_transfers=implicit,
        ungoverned_cross_workspace_paths=cross_workspace,
    )


def require_clean_room_transfers(
    transfers: Iterable[InternalTransfer],
) -> None:
    result = verify_clean_room_transfers(transfers)
    violations: list[str] = []
    for item in result.implicit_capability_transfers:
        violations.append(
            "NO_IMPLICIT_CAPABILITY_TRANSFER: "
            f"{item.source_principal}@{item.source_workspace}->"
            f"{item.target_principal}@{item.target_workspace}({item.kind.value})"
        )
    for item in result.ungoverned_cross_workspace_paths:
        violations.append(
            "NO_UNGOVERNED_CROSS_WORKSPACE_PATH: "
            f"{item.source_principal}@{item.source_workspace}->"
            f"{item.target_principal}@{item.target_workspace}({item.kind.value})"
        )
    if violations:
        raise CleanRoomConformanceError("; ".join(violations))


__all__ = [
    "CleanRoomConformanceError",
    "CleanRoomConformanceResult",
    "InternalTransfer",
    "TransferKind",
    "require_clean_room_transfers",
    "verify_clean_room_transfers",
]
