"""NPPDS / PPDS Procurement Data Space Export Adapter.

Exports verifiable, schema-versioned procurement lifecycle events to National and Union
Procurement Data Spaces with immutable receipt_digest chain links to Veritas proof records.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Tuple


def _canonical_digest(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ProcurementDataSpaceExportRecordV1:
    """Immutable data space export record with Veritas receipt chain links."""

    export_id: str
    tenant_id: str
    procedure_id: str
    action_type: str
    veritas_receipt_digest: str
    reht_clearance_outcome: str
    data_space_target: str  # "NPPDS_NO" | "PPDS_EU"
    exported_at: str
    schema_version: str = "v1"

    def canonical_payload(self) -> Mapping[str, object]:
        return asdict(self)

    @property
    def computed_digest(self) -> str:
        return _canonical_digest(self.canonical_payload())
