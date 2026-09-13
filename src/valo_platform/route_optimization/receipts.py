"""Separate, signed route-planning receipts for the existing receipt ledger."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping

import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel, ConfigDict

from src.valo_platform.action_envelope.receipt_ledger import (
    LedgerEntry,
    SQLiteReceiptLedger,
    TrustedReceiptIssuer,
)
from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import (
    PrunedCandidate,
    RoutePivot,
    RouteSelection,
    SelectionStatus,
)
from src.valo_platform.route_optimization.metrics import (
    RoutePlanningMetrics,
    planning_metrics_from_selection,
)


ROUTE_PLANNING_ARTIFACT_TYPE = "ROUTE_PLANNING_RECEIPT"
ROUTE_OUTCOME_ARTIFACT_TYPE = "ROUTE_OUTCOME_RECEIPT"


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("receipt timestamp must include timezone")
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class RoutePlanningReceipt(BaseModel):
    """Evidence of route generation, pruning and selection; never clearance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "route_planning_receipt.v1"
    receipt_id: str
    tenant_id: str
    execution_id: str
    route_request_id: str
    route_request_fingerprint: str
    graph_fingerprint: str
    selection_status: SelectionStatus
    selection_fingerprint: str
    route_digest: str | None = None
    selected_candidate_id: str | None = None
    selected_node_ids: tuple[str, ...] = ()
    active_frontier: tuple[str, ...] = ()
    pivot_set: tuple[RoutePivot, ...] = ()
    pruned_candidates: tuple[PrunedCandidate, ...] = ()
    metrics: RoutePlanningMetrics
    estimate_versions: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    valid_until: datetime | None = None
    previous_receipt_hash: str
    issued_at: datetime
    receipt_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"receipt_digest": ""}))


def seal_route_planning_receipt(
    *,
    receipt_id: str,
    tenant_id: str,
    execution_id: str,
    route_request_fingerprint: str,
    graph_fingerprint: str,
    selection: RouteSelection,
    input_candidate_count: int,
    previous_receipt_hash: str,
    issued_at: datetime,
) -> RoutePlanningReceipt:
    if not receipt_id or not tenant_id or not execution_id:
        raise ValueError("receipt, tenant and execution identities are required")
    if not route_request_fingerprint or not graph_fingerprint:
        raise ValueError("route request and graph fingerprints are required")
    if selection.status is SelectionStatus.SELECTED and not selection.route_digest:
        raise ValueError("selected route requires route digest")
    metrics = planning_metrics_from_selection(
        selection,
        input_candidate_count=input_candidate_count,
    )
    provisional = RoutePlanningReceipt(
        receipt_id=receipt_id,
        tenant_id=tenant_id,
        execution_id=execution_id,
        route_request_id=selection.route_request_id,
        route_request_fingerprint=route_request_fingerprint,
        graph_fingerprint=graph_fingerprint,
        selection_status=selection.status,
        selection_fingerprint=selection.fingerprint,
        route_digest=selection.route_digest,
        selected_candidate_id=selection.selected_candidate_id,
        selected_node_ids=selection.selected_node_ids,
        active_frontier=selection.active_frontier,
        pivot_set=selection.pivot_set,
        pruned_candidates=selection.pruned_candidates,
        metrics=metrics,
        estimate_versions=selection.estimate_versions,
        assumptions=selection.assumptions,
        valid_until=selection.valid_until,
        previous_receipt_hash=previous_receipt_hash,
        issued_at=issued_at,
        receipt_digest="",
    )
    return provisional.model_copy(
        update={"receipt_digest": provisional.computed_digest}
    )


def sign_route_artifact(
    *,
    payload: BaseModel | Mapping[str, Any],
    artifact_id: str,
    artifact_type: str,
    private_key: Ed25519PrivateKey,
    issuer: TrustedReceiptIssuer,
    issued_at: datetime,
    expires_at: datetime,
    profile_id: str = "racs-core-0.2",
) -> dict[str, Any]:
    """Create the existing signed RACS-JCS-1 artifact envelope."""
    if expires_at <= issued_at:
        raise ValueError("artifact expiry must follow issue time")
    payload_value = (
        payload.model_dump(mode="json")
        if isinstance(payload, BaseModel)
        else dict(payload)
    )
    payload_digest = "sha256:" + hashlib.sha256(
        rfc8785.dumps(payload_value)
    ).hexdigest()
    artifact: dict[str, Any] = {
        "artifact_type": artifact_type,
        "schema_version": "0.2.0",
        "profile_id": profile_id,
        "artifact_id": artifact_id,
        "tenant_id": issuer.tenant_id,
        "trust_domain": issuer.trust_domain,
        "issuer_id": issuer.issuer_id,
        "issuer_role": issuer.issuer_role,
        "issued_at": _utc_text(issued_at),
        "expires_at": _utc_text(expires_at),
        "payload": payload_value,
        "payload_digest": payload_digest,
        "canonicalization": "RACS-JCS-1",
        "signature": {
            "algorithm": "Ed25519",
            "key_id": issuer.key_id,
            "value": "",
        },
    }
    artifact["signature"]["value"] = base64.urlsafe_b64encode(
        private_key.sign(rfc8785.dumps(artifact))
    ).rstrip(b"=").decode("ascii")
    return artifact


def append_route_planning_receipt(
    *,
    ledger: SQLiteReceiptLedger,
    receipt: RoutePlanningReceipt,
    private_key: Ed25519PrivateKey,
    trusted_issuer: TrustedReceiptIssuer,
    expires_at: datetime,
    recorded_at: datetime | None = None,
) -> LedgerEntry:
    if receipt.tenant_id != trusted_issuer.tenant_id:
        raise ValueError("route receipt tenant differs from trusted issuer")
    if receipt.computed_digest != receipt.receipt_digest:
        raise ValueError("route planning receipt digest mismatch")
    artifact = sign_route_artifact(
        payload=receipt,
        artifact_id=receipt.receipt_id,
        artifact_type=ROUTE_PLANNING_ARTIFACT_TYPE,
        private_key=private_key,
        issuer=trusted_issuer,
        issued_at=receipt.issued_at,
        expires_at=expires_at,
    )
    return ledger.append(
        execution_id=receipt.execution_id,
        artifact=artifact,
        trusted_issuer=trusted_issuer,
        recorded_at=recorded_at,
    )


__all__ = [
    "ROUTE_OUTCOME_ARTIFACT_TYPE",
    "ROUTE_PLANNING_ARTIFACT_TYPE",
    "RoutePlanningReceipt",
    "append_route_planning_receipt",
    "seal_route_planning_receipt",
    "sign_route_artifact",
]
