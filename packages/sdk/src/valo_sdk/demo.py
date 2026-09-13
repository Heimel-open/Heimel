from __future__ import annotations

from datetime import UTC, datetime

from valo_c_mcp import CMCPContractV1, CMCPInvocation, ProtocolStack
from valo_conformance import (
    SurfaceConformanceObservationV1,
    evaluate_surface_conformance,
)
from valo_mal import (
    FederationRequest,
    SignedPolicyPack,
    TrustRoot,
    canonical_digest,
    evaluate_import,
)
from valo_public_procurement import AwardRecommendation, ProcurementProcedure, Tender
from valo_vaig import DistrustLevel, GateDecision, level_to_gate_status


def run_demo() -> dict[str, object]:
    """Run the portable contract chain without network or external effects."""
    now = datetime(2026, 8, 14, 4, 0, tzinfo=UTC)
    policy = {"region": "eu-north", "rules": ["deny-unknown"]}
    root = TrustRoot(
        "root-1",
        "issuer-a",
        "fingerprint",
        ("tenant-b",),
        ("model-admissibility",),
        1,
        2_000_000_000,
    )
    pack = SignedPolicyPack(
        "pack-1",
        "issuer-a",
        "tenant-a",
        "model-admissibility",
        "1.0.0",
        policy,
        canonical_digest(policy),
        "reference-signature",
        "root-1",
        1,
        2_000_000_000,
    )
    mal = evaluate_import(
        pack,
        FederationRequest(
            "tenant-b",
            "model-admissibility",
            "eu-north",
            int(now.timestamp()),
            "demo-nonce",
        ),
        [root],
        set(),
    )

    invocation = CMCPInvocation(
        call_id="call-1",
        actor_id="agent-1",
        tenant_id="tenant-b",
        server_id="reference-mcp",
        tool_name="read_record",
        protocol_stack=ProtocolStack(transport="http", interaction_protocols=["mcp"]),
        target_resource="record:1",
        purpose_ref="purpose:demo",
    )
    cmcp = CMCPContractV1.bind(
        invocation,
        gcop_contract_id="gcop:demo",
        gcop_contract_hash="sha256:demo",
        now=now,
        contract_id="cmcp:demo",
    )
    cmcp_valid = cmcp.verify(invocation, now=now)

    conformance = evaluate_surface_conformance(
        SurfaceConformanceObservationV1(
            surface_id="demo-projection",
            surface_type="ui",
        )
    )
    gate = GateDecision(
        level_to_gate_status(DistrustLevel.TRUSTED), "PASS", 1.0, "fluid"
    )
    procedure = ProcurementProcedure(
        "proc-demo", "tenant-b", "OPEN_PROCEDURE", "PUBLISHED"
    )
    tender = Tender(
        "tender-demo",
        procedure.procedure_id,
        "supplier-demo",
        100.0,
        "sri:tender-demo",
        "2026-08-14T04:00:00Z",
    )
    recommendation = AwardRecommendation(
        "recommendation-demo",
        procedure.procedure_id,
        tender.tender_id,
        "reference",
        "criteria-v1",
        tender.computed_digest,
        "reference-evaluator",
        "2026-08-14T04:00:00Z",
    )
    return {
        "mal_decision": mal.decision,
        "c_mcp_verification": cmcp_valid,
        "conformance_passed": conformance.passed,
        "vaig_gate": gate.as_dict(),
        "procurement_recommendation_digest": recommendation.computed_digest,
        "authority_granted": False,
        "external_effect": False,
    }
