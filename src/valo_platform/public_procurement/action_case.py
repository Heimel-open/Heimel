"""ProcurementActionCaseV1 — typed specialization of canonical ActionCase.

Carries procurement action evidence, procedure ID, tender ID, contract ID, amount, and supplier identity.
Contains NO authorization logic and does NOT grant execution authority.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Tuple, Optional


def _canonical_digest(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ProcurementActionCaseV1:
    """Immutable data container for public procurement action evidence."""

    case_id: str
    tenant_id: str
    procedure_id: str
    action_type: str  # e.g., "NEEDS_PLAN", "AWARD_RECOMMENDATION", "CONTRACT_SIGNATURE", "PAYMENT_RELEASE"
    supplier_id: Optional[str]
    contract_id: Optional[str]
    amount_nok: Optional[float]
    evidence_digests: Tuple[str, ...]
    policy_snapshot_digest: str
    mandate_ref: str
    schema_version: str = "v1"

    def canonical_payload(self) -> Mapping[str, object]:
        return asdict(self)

    @property
    def computed_digest(self) -> str:
        return _canonical_digest(self.canonical_payload())
