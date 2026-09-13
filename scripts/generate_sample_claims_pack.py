#!/usr/bin/env python3
"""Generate the carrier pilot sample assets from the frozen valo-insurance-pack v0.1.0 core.

Produces:
  sample-profile/high-value-procurement.json
  sample-claims-pack/high-value-procurement-claims-pack.json

Run with the core on the path, e.g.:
  PYTHONPATH=/home/njaal/valo-insurance-pack/src python3 scripts/generate_sample_claims_pack.py
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from valo_insurance_pack.claims.verifier import verify_claims_evidence_pack
from valo_insurance_pack.contracts.source_evidence import (
    ChangedSinceStatus,
    RevocationVisibilityStatus,
    SourceAssuranceEvidenceV1,
)
from valo_insurance_pack.pipeline.procurement_scenario import (
    GovernedProcurementPipeline,
)
from valo_insurance_pack.profiles.carrier_examples import PROCUREMENT_HIGH_VALUE
from valo_insurance_pack.utils.crypto import sha256_digest, utcnow

ROOT = Path(__file__).resolve().parents[1]


class MockErpSapTool:
    """Synthetic SAP ERP consequence for pilot sample generation only.

    NOT a real integration: this mock exists solely to produce a deterministic
    sample ClaimsEvidencePack for carrier-facing material.
    """

    def __init__(self) -> None:
        self.committed_pos: dict[str, dict[str, Any]] = {}
        self.invocations: list[dict[str, Any]] = []

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        po_number = arguments["po_number"]
        record = {
            "po_number": po_number,
            "amount": arguments["amount"],
            "vendor": arguments["vendor"],
            "status": "COMMITTED",
            "sap_document_id": "DOC-PILOT-0001",
            "committed_at": utcnow().isoformat(),
        }
        self.committed_pos[po_number] = record
        self.invocations.append(record)
        return record


def _reht_authorizer(action: dict[str, Any]) -> dict[str, Any]:
    """Synthetic REHT authorizer for the pilot sample. Real REHT runs in shadow pilot."""
    return {
        "clearance_id": f"clr-pilot-{uuid4().hex[:8]}",
        "action_digest": sha256_digest(action),
        "authority_envelope_id": "auth-pilot-0001",
        "decision_contract": {
            "decision": "ALLOW",
            "principal_id": "principal:procurement-dir",
            "actor_id": "agent:procurement-worker-9",
            "action_type": action["action_type"],
            "target": action["target"],
            "constraints": {"max_amount": 500000},
        },
        "decided_at": utcnow().isoformat(),
        "valid_until": (utcnow() + timedelta(minutes=10)).isoformat(),
        "reht_ref": "reht-decision-pilot-0001",
        "policy_refs": ["cond-high-value-procurement-v1"],
    }


def _gateway_executor(*, action: dict[str, Any], clearance: dict[str, Any], tool, now=None) -> dict[str, Any]:
    """Synthetic Gateway/PEP for the pilot sample. Real Gateway runs in shadow pilot."""
    now = now or utcnow()
    tool_resp = tool.invoke(action["parameters"])
    return {
        "execution_id": "exec-pilot-0001",
        "permit_id": "permit-pilot-0001",
        "clearance_id": clearance["clearance_id"],
        "action_digest": sha256_digest(action),
        "executor_id": "agent:procurement-worker-9",
        "started_at": now.isoformat(),
        "completed_at": now.isoformat(),
        "status": "succeeded",
        "response_digest": sha256_digest(tool_resp),
        "tool_response": tool_resp,
    }


def _veritas_recorder(exec_output: dict[str, Any]) -> dict[str, Any]:
    """Synthetic Veritas recorder for pilot sample generation only."""
    return {
        "schema": "valo.gateway.execution-observation.v1",
        "package_id": f"obs-pkg-{exec_output.get('execution_id', 'unknown')}",
        "execution_id": exec_output.get("execution_id", "unknown"),
        "permit_id": exec_output.get("permit_id", "unknown"),
        "clearance_id": exec_output.get("clearance_id", "unknown"),
        "action_digest": exec_output.get("action_digest", "unknown"),
        "observation_digest": sha256_digest(exec_output),
        "recorded_at": utcnow().isoformat(),
        "worm_sequence": 1,
    }


def main() -> None:
    now = utcnow()
    profile = PROCUREMENT_HIGH_VALUE

    action = {
        "action_type": "PROCUREMENT_ORDER_CREATE",
        "target": "erp:sap/po/create",
        "parameters": {
            "po_number": "PO-2026-7701",
            "amount": 250000,
            "vendor": "SUPPLIER-BETA",
        },
        "principal_id": "principal:procurement-dir",
        "actor_id": "agent:procurement-worker-9",
    }

    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="principal:procurement-dir",
            observed_at=now - timedelta(seconds=30),
            source_version="entra-v2",
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={"assurance_level": "OIDC_FIDO2_BOUND"},
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-procure-2026",
            observed_at=now - timedelta(seconds=60),
            source_version="sap-erp-2026",
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={"assurance_level": "ERP_AUTHORITATIVE_API"},
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_po_state",
            subject="po:PO-2026-7701",
            observed_at=now - timedelta(seconds=45),
            source_version="po-draft-v1",
            attestation_type="ERP_COMMITTED_STATE",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={"assurance_level": "ERP_COMMITTED_STATE"},
        ),
    ]

    pipeline = GovernedProcurementPipeline(
        profile=profile,
        reht_authorizer=_reht_authorizer,
        gateway_executor=_gateway_executor,
        veritas_recorder=_veritas_recorder,
        policy_reference="pol-high-value-procurement-pilot",
    )
    tool = MockErpSapTool()
    result = pipeline.run(action=action, source_evidences=sources, tool=tool, now=now)
    if not result.success:
        raise RuntimeError(f"pilot sample generation failed: {result.error}")

    report = verify_claims_evidence_pack(result.claims_pack)
    if not report.is_valid:
        raise RuntimeError(f"sample claims pack failed verification: {report.errors}")

    profile_payload = profile.to_payload()
    pack_payload = result.claims_pack.model_dump(mode="json")

    profile_path = ROOT / "sample-profile" / "high-value-procurement.json"
    pack_path = ROOT / "sample-claims-pack" / "high-value-procurement-claims-pack.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(profile_payload, indent=2, sort_keys=True) + "\n")
    pack_path.write_text(json.dumps(pack_payload, indent=2, sort_keys=True) + "\n")

    print(f"wrote {profile_path}")
    print(f"wrote {pack_path}")
    print(f"offline verification: {report.is_valid} ({len(report.checks_performed)} checks)")


if __name__ == "__main__":
    main()
