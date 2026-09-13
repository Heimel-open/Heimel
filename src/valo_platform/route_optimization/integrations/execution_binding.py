"""Exact route binding around canonical REHT and RACS artifacts.

Planning remains advisory. The wrappers cryptographically bind one selected
frontier step and payload to the existing REHT clearance and RACS commit
artifacts; they never create authority independently.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, MutableSet, Optional

from pydantic import BaseModel, ConfigDict

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.governance.pre_execution import Decision
from src.valo_platform.governance.reht_racs_binding import (
    RACSCommitEnvelope,
    REHTClearanceInput,
    REHTClearanceReceipt,
    REHTRACSBinding,
    verify_commit_envelope,
)
from src.valo_platform.route_optimization.contracts import (
    RouteRequest,
    RouteSelection,
    SelectionStatus,
)


def _same_hash(left: str, right: str) -> bool:
    return left.removeprefix("sha256:") == right.removeprefix("sha256:")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _minimum_time(*values: Optional[datetime]) -> Optional[datetime]:
    present = [value for value in values if value is not None]
    return min(present) if present else None


class RouteBoundClearanceInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "route_bound_reht_clearance_input.v1"
    route_request_id: str
    route_request_fingerprint: str
    route_digest: str
    route_version: str
    selected_candidate_id: str
    route_step_id: str
    current_state_digest: str
    action_ref: str
    action_payload_digest: str
    reht_clearance_input_digest: str
    valid_until: datetime
    binding_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"binding_digest": ""}))


class RouteBoundClearanceReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "route_bound_reht_clearance_receipt.v1"
    route_binding_digest: str
    reht_clearance_digest: str
    action_ref: str
    decision: Decision
    executable: bool
    receipt_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"receipt_digest": ""}))


class RouteBoundCommitEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "route_bound_racs_commit_envelope.v1"
    route_binding_digest: str
    route_clearance_receipt_digest: str
    racs_commit_digest: str
    route_request_id: str
    route_request_fingerprint: str
    route_digest: str
    route_version: str
    selected_candidate_id: str
    route_step_id: str
    current_state_digest: str
    action_ref: str
    action_payload_digest: str
    valid_until: datetime
    commit_binding_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(
            self.model_copy(update={"commit_binding_digest": ""})
        )


def bind_route_to_clearance(
    *,
    selection: RouteSelection,
    request: RouteRequest,
    route_version: str,
    route_step_id: str,
    action_payload: Any,
    reht_clearance_input: REHTClearanceInput,
    now: Optional[datetime] = None,
) -> RouteBoundClearanceInput:
    """Bind one currently executable route step to an existing REHT input."""
    current = now or request.as_of
    if selection.status is not SelectionStatus.SELECTED:
        raise ValueError("route selection is not executable")
    if selection.route_request_id != request.route_request_id:
        raise ValueError("route selection is bound to another request")
    if not selection.route_digest or not selection.selected_candidate_id:
        raise ValueError("selected route requires digest and candidate identity")
    if route_step_id not in selection.active_frontier:
        raise ValueError("route step is not in the current active frontier")
    if route_step_id not in selection.selected_node_ids:
        raise ValueError("route step is not part of the selected route")
    if not route_version:
        raise ValueError("route_version is required")
    if not _same_hash(
        reht_clearance_input.context_digest,
        request.context_snapshot_hash,
    ):
        raise ValueError("REHT context digest differs from route request")
    if not _same_hash(
        reht_clearance_input.mandate_digest,
        request.authority_snapshot_hash,
    ):
        raise ValueError("REHT mandate digest differs from route request")

    evaluation_expiry = _parse_utc(
        reht_clearance_input.evaluation_expires_at
    )
    valid_until = _minimum_time(selection.valid_until, evaluation_expiry)
    if valid_until is None or valid_until <= current:
        raise ValueError("route-bound clearance input is stale")

    provisional = RouteBoundClearanceInput(
        route_request_id=request.route_request_id,
        route_request_fingerprint=request.fingerprint,
        route_digest=selection.route_digest,
        route_version=route_version,
        selected_candidate_id=selection.selected_candidate_id,
        route_step_id=route_step_id,
        current_state_digest=request.current_state_digest,
        action_ref=reht_clearance_input.action_ref,
        action_payload_digest=canonical_digest(action_payload),
        reht_clearance_input_digest=(
            reht_clearance_input.clearance_input_digest
        ),
        valid_until=valid_until,
        binding_digest="",
    )
    return provisional.model_copy(
        update={"binding_digest": provisional.computed_digest}
    )


def clear_route_bound_input(
    *,
    route_input: RouteBoundClearanceInput,
    reht_clearance_input: REHTClearanceInput,
    binding: REHTRACSBinding,
    consumed_replay_keys: Optional[MutableSet[str]] = None,
    now: Optional[datetime] = None,
) -> tuple[REHTClearanceReceipt, RouteBoundClearanceReceipt]:
    """Call existing REHT clearance only after exact route binding verifies."""
    current = now or datetime.now(timezone.utc)
    if route_input.computed_digest != route_input.binding_digest:
        raise ValueError("route clearance binding digest mismatch")
    if route_input.valid_until <= current:
        raise ValueError("route clearance binding expired")
    if (
        route_input.reht_clearance_input_digest
        != reht_clearance_input.clearance_input_digest
    ):
        raise ValueError("route binding references another REHT input")
    if route_input.action_ref != reht_clearance_input.action_ref:
        raise ValueError("route binding action differs from REHT input")

    reht_receipt = binding.clear(
        reht_clearance_input,
        consumed_replay_keys=consumed_replay_keys,
    )
    provisional = RouteBoundClearanceReceipt(
        route_binding_digest=route_input.binding_digest,
        reht_clearance_digest=reht_receipt.clearance_digest,
        action_ref=reht_receipt.action_ref,
        decision=reht_receipt.decision,
        executable=reht_receipt.executable,
        receipt_digest="",
    )
    route_receipt = provisional.model_copy(
        update={"receipt_digest": provisional.computed_digest}
    )
    return reht_receipt, route_receipt


def create_route_bound_commit(
    *,
    route_input: RouteBoundClearanceInput,
    route_receipt: RouteBoundClearanceReceipt,
    reht_clearance_input: REHTClearanceInput,
    reht_receipt: REHTClearanceReceipt,
    binding: REHTRACSBinding,
) -> tuple[RACSCommitEnvelope, RouteBoundCommitEnvelope]:
    """Create the existing RACS commit and bind it to the exact route step."""
    if route_input.computed_digest != route_input.binding_digest:
        raise ValueError("route clearance binding digest mismatch")
    if route_receipt.computed_digest != route_receipt.receipt_digest:
        raise ValueError("route clearance receipt digest mismatch")
    if route_receipt.route_binding_digest != route_input.binding_digest:
        raise ValueError("route receipt is bound to another route input")
    if route_receipt.reht_clearance_digest != reht_receipt.clearance_digest:
        raise ValueError("route receipt references another REHT clearance")
    if not route_receipt.executable:
        raise ValueError("route clearance is not executable")

    racs_commit = binding.create_commit_envelope(
        reht_clearance_input,
        reht_receipt,
    )
    provisional = RouteBoundCommitEnvelope(
        route_binding_digest=route_input.binding_digest,
        route_clearance_receipt_digest=route_receipt.receipt_digest,
        racs_commit_digest=racs_commit.commit_digest,
        route_request_id=route_input.route_request_id,
        route_request_fingerprint=route_input.route_request_fingerprint,
        route_digest=route_input.route_digest,
        route_version=route_input.route_version,
        selected_candidate_id=route_input.selected_candidate_id,
        route_step_id=route_input.route_step_id,
        current_state_digest=route_input.current_state_digest,
        action_ref=route_input.action_ref,
        action_payload_digest=route_input.action_payload_digest,
        valid_until=route_input.valid_until,
        commit_binding_digest="",
    )
    route_commit = provisional.model_copy(
        update={"commit_binding_digest": provisional.computed_digest}
    )
    return racs_commit, route_commit


def assert_route_bound_commit(
    *,
    route_commit: RouteBoundCommitEnvelope,
    racs_commit: RACSCommitEnvelope,
    selection: RouteSelection,
    request: RouteRequest,
    route_version: str,
    route_step_id: str,
    action_ref: str,
    action_payload: Any,
    now: Optional[datetime] = None,
) -> None:
    """Fail closed unless execution exactly matches the current cleared route."""
    current = now or request.as_of
    if route_commit.computed_digest != route_commit.commit_binding_digest:
        raise ValueError("route commit binding digest mismatch")
    if not verify_commit_envelope(racs_commit):
        raise ValueError("RACS commit digest mismatch")
    if route_commit.racs_commit_digest != racs_commit.commit_digest:
        raise ValueError("route commit references another RACS envelope")
    if route_commit.valid_until <= current:
        raise ValueError("route commit expired")
    if selection.status is not SelectionStatus.SELECTED:
        raise ValueError("current route is not selected")

    expected = {
        "route_request_id": request.route_request_id,
        "route_request_fingerprint": request.fingerprint,
        "route_digest": selection.route_digest,
        "route_version": route_version,
        "selected_candidate_id": selection.selected_candidate_id,
        "route_step_id": route_step_id,
        "current_state_digest": request.current_state_digest,
        "action_ref": action_ref,
        "action_payload_digest": canonical_digest(action_payload),
    }
    observed = {
        "route_request_id": route_commit.route_request_id,
        "route_request_fingerprint": route_commit.route_request_fingerprint,
        "route_digest": route_commit.route_digest,
        "route_version": route_commit.route_version,
        "selected_candidate_id": route_commit.selected_candidate_id,
        "route_step_id": route_commit.route_step_id,
        "current_state_digest": route_commit.current_state_digest,
        "action_ref": route_commit.action_ref,
        "action_payload_digest": route_commit.action_payload_digest,
    }
    if observed != expected:
        raise ValueError("execution differs from current route binding")
    if route_step_id not in selection.active_frontier:
        raise ValueError("execution step is no longer in the active frontier")
    if racs_commit.action_ref != action_ref:
        raise ValueError("RACS action differs from route-bound action")


def verify_route_bound_commit(**kwargs: Any) -> bool:
    try:
        assert_route_bound_commit(**kwargs)
    except (TypeError, ValueError):
        return False
    return True


__all__ = [
    "RouteBoundClearanceInput",
    "RouteBoundClearanceReceipt",
    "RouteBoundCommitEnvelope",
    "assert_route_bound_commit",
    "bind_route_to_clearance",
    "clear_route_bound_input",
    "create_route_bound_commit",
    "verify_route_bound_commit",
]
