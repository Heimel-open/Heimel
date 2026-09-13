#!/usr/bin/env python3
"""Demonstrator: Autonomous High-Value Procurement with valo-insurance-pack."""

from datetime import timedelta
from uuid import uuid4

from examples.mock_erp import MockErpSapTool
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


def _demo_reht_authorizer(action: dict) -> dict:
    return {
        "clearance_id": f"clr-{uuid4()}",
        "action_digest": sha256_digest(action),
        "authority_envelope_id": f"auth-{uuid4()}",
        "decision_contract": {
            "decision": "ALLOW",
            "principal_id": action.get("principal_id", "principal:corp-officer"),
            "actor_id": action.get("actor_id", "agent:procurement-worker"),
            "action_type": action.get("action_type", "PROCUREMENT_ORDER_CREATE"),
            "target": action.get("target", "erp:sap/po/create"),
        },
        "decided_at": utcnow().isoformat(),
        "valid_until": (utcnow() + timedelta(minutes=5)).isoformat(),
        "reht_ref": f"reht-decision-{uuid4()}",
        "policy_refs": ["cond-procurement-high-value-v1"],
    }


def _demo_gateway_executor(*, action: dict, clearance: dict, tool, now=None) -> dict:
    now = now or utcnow()
    tool_resp = tool.invoke(action.get("parameters", {}))
    return {
        "execution_id": f"exec-{uuid4()}",
        "permit_id": f"permit-{uuid4()}",
        "clearance_id": clearance["clearance_id"],
        "action_digest": sha256_digest(action),
        "executor_id": action.get("actor_id", "agent:procurement-worker"),
        "started_at": now.isoformat(),
        "completed_at": now.isoformat(),
        "status": "succeeded",
        "response_digest": sha256_digest(tool_resp),
        "tool_response": tool_resp,
    }


def _demo_veritas_recorder(exec_output: dict) -> dict:
    """Synthetic Veritas recorder for the demonstrator only.

    A real deployment injects a Veritas WORM writer here; the demonstrator
    uses an explicit mock so no fabricated attestation is implied.
    """
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
    print("=== VALO INSURANCE PACK DEMONSTRATOR ===")
    now = utcnow()
    profile = PROCUREMENT_HIGH_VALUE
    print(f"Loaded Profile: {profile.profile_id} (Version: {profile.profile_version})")
    print(f"Carrier Ref: {profile.insurer_reference}")
    print(f"Required Sources: {profile.required_authoritative_sources}")

    erp_tool = MockErpSapTool()
    pipeline = GovernedProcurementPipeline(
        profile=profile,
        reht_authorizer=_demo_reht_authorizer,
        gateway_executor=_demo_gateway_executor,
        veritas_recorder=_demo_veritas_recorder,
        policy_reference="pol-procurement-demo-2026",
    )

    action = {
        "action_type": "PROCUREMENT_ORDER_CREATE",
        "target": "erp:sap/po/create",
        "parameters": {
            "po_number": "PO-DEMO-2026-01",
            "amount": 120000,
            "supplier": "SUPPLIER-DEMO",
        },
        "principal_id": "principal:procurement-officer",
        "actor_id": "agent:procurement-worker",
    }

    evidences = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="principal:procurement-officer",
            observed_at=now - timedelta(seconds=10),
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-demo",
            observed_at=now - timedelta(seconds=20),
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_po_state",
            subject="po:PO-DEMO-2026-01",
            observed_at=now - timedelta(seconds=15),
            attestation_type="ERP_COMMITTED_STATE",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]

    print("\nExecuting governed procurement pipeline...")
    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )

    print(f"Pipeline Success: {result.success}")
    print(f"Assurance Result: {result.assurance_evaluation.assurance_result.value}")
    print(f"Committed ERP Documents: {list(erp_tool.committed_pos.keys())}")

    if result.claims_pack:
        print("\nVerifying generated ClaimsEvidencePackV1...")
        report = verify_claims_evidence_pack(result.claims_pack)
        print(f"Claims Pack ID: {result.claims_pack.pack_id}")
        print(f"Offline Verification Valid: {report.is_valid}")
        print(f"Checks Performed: {len(report.checks_performed)}")
        print(f"Errors: {report.errors}")

    print("\nUnderwriting Telemetry Snapshot:")
    snapshot = pipeline.telemetry.snapshot()
    print(f"Total Evaluations: {snapshot.total_evaluations}")
    print(f"Clearance Rate: {snapshot.clearance_rate}")
    print(f"Control Effectiveness: {snapshot.control_effectiveness_score}")
    print("\nDemonstrator completed successfully.")


if __name__ == "__main__":
    main()
