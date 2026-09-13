from __future__ import annotations

from typing import Any
from uuid import uuid4

from valo_insurance_pack.utils.crypto import utcnow


class MockErpSapTool:
    """Example SAP ERP backend connector for demonstrators and integration tests.

    CRITICAL INVARIANT: This tool is consequence-bearing and should ONLY be reached
    via the ValoGateway PEP with a valid, unconsumed ExecutionPermit.
    """

    def __init__(self) -> None:
        self.committed_pos: dict[str, dict[str, Any]] = {}
        self.invocations: list[dict[str, Any]] = []

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        po_number = arguments.get("po_number", f"PO-{uuid4().hex[:6].upper()}")
        amount = arguments.get("amount", 0)
        supplier = arguments.get("supplier", "DEFAULT_SUPPLIER")
        record = {
            "po_number": po_number,
            "amount": amount,
            "supplier": supplier,
            "status": "COMMITTED",
            "sap_document_id": f"DOC-{uuid4().hex[:8].upper()}",
            "committed_at": utcnow().isoformat(),
        }
        self.committed_pos[po_number] = record
        self.invocations.append(record)
        return record

    def _invoke_from_boundary(self, arguments: dict[str, Any], proof: Any = None) -> dict[str, Any]:
        return self.invoke(arguments)
