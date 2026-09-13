from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import racs_v02
import valo_gateway
import valo_gateway.tool_adapters
import veritas
from valo_kernel.kernel.context_origin import (
    Ed25519KernelContextSigner,
    execution_context_digest,
    seal_execution_context,
)

from valo_reht import (
    Ed25519KernelExecutionContextVerifier,
    RealReht,
    TrustedKernelContextKey,
)

BASE = datetime(2026, 8, 16, 16, 0, tzinfo=UTC)


def _kernel_digest(value) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _signer() -> Ed25519KernelContextSigner:
    return Ed25519KernelContextSigner.from_private_key_bytes(
        kernel_id="kernel-1",
        key_id="key-1",
        private_key_bytes=b"\x01" * 32,
    )


def _verifier(signer: Ed25519KernelContextSigner) -> Ed25519KernelExecutionContextVerifier:
    return Ed25519KernelExecutionContextVerifier(
        (
            TrustedKernelContextKey(
                kernel_id="kernel-1",
                key_id="key-1",
                tenant_ids=frozenset({"tenant-1"}),
                public_key=signer.public_key(),
                valid_from=BASE - timedelta(hours=1),
                valid_until=BASE + timedelta(hours=1),
            ),
        )
    )


def _fixture(*, context_time: datetime = BASE):
    signer = _signer()
    verifier = _verifier(signer)
    proposed_action = {
        "action_id": "action-1",
        "capability": "order.update",
        "target": "order:42",
        "purpose_id": "purpose-1",
        "parameters": {"status": "approved"},
        "declared_effects": ["external:erp"],
    }
    dependency_digest = _kernel_digest([])
    binding = {
        "schema_version": "workspace_execution_binding.v1",
        "tenant_id": "tenant-1",
        "work_unit_id": "work-1",
        "workspace_id": "workspace-1",
        "workspace_digest": "a" * 64,
        "workspace_expires_at": (BASE + timedelta(minutes=5)).isoformat(),
        "program_ref": "function:order-update",
        "program_digest": "b" * 64,
        "governing_contract_ids": [],
        "invocation_id": "invocation-1",
        "candidate_id": "candidate-1",
        "candidate_digest": "c" * 64,
        "proposed_action": proposed_action,
        "proposed_action_digest": _kernel_digest(proposed_action),
        "conformance_report_id": "conformance-1",
        "conformance_digest": "d" * 64,
        "source_state_root": "e" * 64,
        "conformed_state_root": "e" * 64,
        "source_event_position": 7,
        "conformed_at": BASE.isoformat(),
        "dependency_digest": dependency_digest,
        "dependencies": [],
        "conformance_outcome": "PASS",
        "authority_effect": "NO_AUTHORITY_CREATION",
        "can_issue_clearance": False,
    }
    unsigned = {
        "tenant_id": "tenant-1",
        "actor": "actor-1",
        "identity": "identity-1",
        "authority": [
            {
                "authority_id": "authority-1",
                "principal": "actor-1",
                "capability": "order.update",
                "scope": ["order:42"],
                "constraints": {"purpose_id": "purpose-1"},
                "status": "ACTIVE",
                "validity": {
                    "valid_from": (BASE - timedelta(minutes=1)).isoformat(),
                    "valid_until": (BASE + timedelta(minutes=10)).isoformat(),
                },
            }
        ],
        "delegation": [],
        "purpose": {
            "purpose_id": "purpose-1",
            "purpose_type": "operations",
            "scope": ["order:42"],
            "basis": "contract",
            "permitted_data": [],
            "permitted_actions": ["order.update"],
            "validity": {
                "valid_from": (BASE - timedelta(minutes=1)).isoformat(),
                "valid_until": (BASE + timedelta(minutes=10)).isoformat(),
            },
        },
        "rights": [],
        "obligations": [],
        "current_state": None,
        "evidence": [],
        "contracts": [],
        "constraints": [],
        "time": {"now": context_time.isoformat()},
        "state_ref": dependency_digest,
        "state_root": "e" * 64,
        "sequence": 7,
        "execution_nonce": "nonce-1",
        "workspace_binding": binding,
        "requested_transition": {
            "tenant_id": "tenant-1",
            "event_id": "event-1",
        },
    }
    context = seal_execution_context(unsigned, signer=signer)
    action_contract = {
        "governed_workspace_required": True,
        "tenant_id": "tenant-1",
        "action_id": "action-1",
        "capability": "order.update",
        "target": "order:42",
        "purpose_id": "purpose-1",
        "parameters": {"status": "approved"},
        "workspace_binding_digest": execution_context_digest(binding),
        "kernel_context_digest": execution_context_digest(context),
    }
    return signer, verifier, context, action_contract


def _runtime(verifier, *, now: datetime = BASE) -> RealReht:
    return RealReht(kernel_context_verifier=verifier, clock=lambda: now)


def _gateway_lineage(context, action):
    binding = context["workspace_binding"]
    return valo_gateway.GovernedWorkspaceLineage(
        tenant_id=binding["tenant_id"],
        work_unit_id=binding["work_unit_id"],
        workspace_id=binding["workspace_id"],
        workspace_digest=f"sha256:{binding['workspace_digest']}",
        workspace_expires_at=datetime.fromisoformat(binding["workspace_expires_at"]),
        program_ref=binding["program_ref"],
        program_digest=f"sha256:{binding['program_digest']}",
        invocation_id=binding["invocation_id"],
        candidate_id=binding["candidate_id"],
        candidate_digest=f"sha256:{binding['candidate_digest']}",
        proposed_action_digest=f"sha256:{binding['proposed_action_digest']}",
        conformance_report_id=binding["conformance_report_id"],
        conformance_digest=f"sha256:{binding['conformance_digest']}",
        source_state_digest=f"sha256:{binding['source_state_root']}",
        conformed_state_digest=f"sha256:{binding['conformed_state_root']}",
        source_event_position=binding["source_event_position"],
        conformed_at=datetime.fromisoformat(binding["conformed_at"]),
        dependency_digest=f"sha256:{binding['dependency_digest']}",
        workspace_binding_digest=action["workspace_binding_digest"],
        kernel_context_digest=action["kernel_context_digest"],
    )


def test_canonical_reht_allows_exact_fresh_workspace_action():
    _, verifier, context, action = _fixture()

    result = _runtime(verifier).authorize(context, action)

    assert result.decision == "ALLOW"
    assert result.clearance_ref is not None
    assert result.permit_ref is not None


def test_current_workspace_chain_reaches_gateway_once_and_veritas_worm():
    _, verifier, context, action_contract = _fixture()
    reht_result = _runtime(verifier).authorize(context, action_contract)
    assert reht_result.decision == "ALLOW"

    authority = valo_gateway.AuthorityEnvelope(
        envelope_id="authority:workspace-e2e",
        principal_id="actor-1",
        actor_id="actor-1",
        source=valo_gateway.AuthoritySource.INTERNAL,
        issuer="valo-kernel",
        capability_grants=["order.update"],
        resource_scope=["order:42"],
        purpose_scope=["purpose-1"],
        issued_at=BASE - timedelta(minutes=1),
        valid_until=BASE + timedelta(minutes=10),
    )
    action = valo_gateway.ActionEnvelope(
        action_type="order.update",
        target="order:42",
        parameters={"status": "approved"},
        context_digest=reht_result.execution_context_hash,
        policy_digest=veritas.canonical_digest({"policy": "workspace-e2e"}),
        authority_envelope_id=authority.envelope_id,
        workspace_binding=_gateway_lineage(context, action_contract),
        nonce="workspace-e2e-nonce",
    )
    racs_evaluation = racs_v02.GovernanceEvaluation(
        evaluation_id="racs-eval:workspace-e2e",
        action_id=action_contract["action_id"],
        action_envelope_digest=veritas.canonical_digest(
            {"action_digest": action.digest}
        ),
        tenant_id="tenant-1",
        evaluator_id="racs:workspace-e2e",
        evaluator_version="0.2",
        decision=racs_v02.Decision(reht_result.decision),
        authority_status=racs_v02.Status.PRESENT_AND_VALID,
        policy_status=racs_v02.Status.PRESENT_AND_VALID,
        evidence_status=racs_v02.Status.PRESENT_AND_VALID,
        purpose_status=racs_v02.Status.PRESENT_AND_VALID,
        state_status=racs_v02.Status.PRESENT_AND_VALID,
        risk_status=racs_v02.Status.PRESENT_AND_VALID,
        reason_codes=[],
        boundary_assessment_binding=racs_v02.BoundaryAssessmentBinding(
            assessment_ref="workspace:conformance-1",
            assessment_digest=veritas.canonical_digest(
                {"conformance": context["workspace_binding"]["conformance_digest"]}
            ),
        ),
        reasoning_authority=False,
        evaluated_at=BASE.isoformat(),
        valid_until=(BASE + timedelta(minutes=2)).isoformat(),
    )
    assert racs_evaluation.decision is racs_v02.Decision.ALLOW

    clearance = valo_gateway.Clearance(
        clearance_id="clearance:workspace-e2e",
        action_digest=action.digest,
        authority_envelope_id=authority.envelope_id,
        decision_contract=valo_gateway.DecisionContract(
            decision=valo_gateway.Decision(reht_result.decision),
            principal_id=authority.principal_id,
            actor_id=authority.actor_id,
            action_type=action.action_type,
            target=action.target,
            constraints={"reht_clearance_ref": reht_result.clearance_ref},
        ),
        decided_at=BASE,
        valid_until=BASE + timedelta(minutes=2),
        reht_ref=reht_result.clearance_ref,
        workspace_binding_digest=action_contract["workspace_binding_digest"],
        kernel_context_digest=action_contract["kernel_context_digest"],
        evidence_refs=[racs_evaluation.model_digest()],
    )
    permit = valo_gateway.issue_execution_permit(
        clearance=clearance,
        authority=authority,
        action=action,
        expires_at=BASE + timedelta(seconds=30),
        now=BASE,
    )
    calls: list[dict[str, str]] = []
    result = valo_gateway.ValoGateway().execute(
        authority=authority,
        clearance=clearance,
        permit=permit,
        action=action,
        executor_id="executor:workspace-e2e",
        tool=valo_gateway.tool_adapters.FunctionTool(
            "order-update",
            lambda **kwargs: calls.append(kwargs) or {"ok": True},
        ),
        arguments={"status": "approved"},
        now=BASE,
    )
    assert calls == [{"status": "approved"}]
    assert result.receipt.workspace_binding_digest == action_contract["workspace_binding_digest"]
    assert result.receipt.kernel_context_digest == action_contract["kernel_context_digest"]

    observation = valo_gateway.build_veritas_execution_observation(
        authority=authority,
        clearance=clearance,
        action=action,
        result=result,
    )
    service = veritas.VeritasChainService(veritas.WORMLog())
    service.store_gateway_execution_observation(observation, tenant_id="tenant-1")
    assert service.verify_chain()
    assert len(service.worm.read_all()) == 1


def test_workspace_path_requires_canonical_kernel_verifier():
    _, _, context, action = _fixture()

    result = RealReht(clock=lambda: BASE).authorize(context, action)

    assert result.decision == "DENY"
    assert "verifier is required" in (result.reason or "")


def test_workspace_context_cannot_silently_downgrade_to_legacy_path():
    _, verifier, context, action = _fixture()
    action = {key: value for key, value in action.items() if key != "governed_workspace_required"}

    result = _runtime(verifier).authorize(context, action)

    assert result.decision == "DENY"
    assert "governed_workspace_required=true" in (result.reason or "")


def test_tampered_kernel_signature_denies_before_authority_allow():
    _, verifier, context, action = _fixture()
    tampered = deepcopy(context)
    tampered["origin_proof"]["signature"] = "AAAA"
    action["kernel_context_digest"] = execution_context_digest(tampered)

    result = _runtime(verifier).authorize(tampered, action)

    assert result.decision == "DENY"
    assert "signature" in (result.reason or "").lower()


def test_stale_kernel_context_denies():
    _, verifier, context, action = _fixture(context_time=BASE - timedelta(seconds=6))

    result = _runtime(verifier).authorize(context, action)

    assert result.decision == "DENY"
    assert "stale" in (result.reason or "").lower()


def test_action_drift_denies_even_with_valid_kernel_signature():
    _, verifier, context, action = _fixture()
    action["parameters"] = {"status": "cancelled"}

    result = _runtime(verifier).authorize(context, action)

    assert result.decision == "DENY"
    assert "parameters differ" in (result.reason or "")


def test_workspace_binding_digest_drift_denies():
    _, verifier, context, action = _fixture()
    action["workspace_binding_digest"] = "sha256:" + "0" * 64

    result = _runtime(verifier).authorize(context, action)

    assert result.decision == "DENY"
    assert "workspace binding digest mismatch" in (result.reason or "")


def test_signed_but_self_inconsistent_dependency_binding_denies():
    signer, verifier, original, action = _fixture()
    unsigned = deepcopy(original)
    unsigned.pop("origin_proof")
    unsigned["workspace_binding"]["dependencies"] = [
        {"kind": "object", "ref": "order:99", "digest": "f" * 64}
    ]
    context = seal_execution_context(unsigned, signer=signer)
    action["workspace_binding_digest"] = execution_context_digest(
        unsigned["workspace_binding"]
    )
    action["kernel_context_digest"] = execution_context_digest(context)

    result = _runtime(verifier).authorize(context, action)

    assert result.decision == "DENY"
    assert "dependency digest mismatch" in (result.reason or "")


def test_authority_revoked_by_actual_authorization_time_denies():
    signer, verifier, original, action = _fixture()
    unsigned = deepcopy(original)
    unsigned.pop("origin_proof")
    unsigned["authority"][0]["revoked_at"] = (BASE + timedelta(seconds=2)).isoformat()
    context = seal_execution_context(unsigned, signer=signer)
    action["kernel_context_digest"] = execution_context_digest(context)

    result = _runtime(verifier, now=BASE + timedelta(seconds=3)).authorize(context, action)

    assert result.decision == "DENY"
    assert "no active authority" in (result.reason or "")


def test_legacy_non_workspace_authorization_remains_compatible():
    context = {
        "actor": "actor-1",
        "identity": "identity-1",
        "authority": [
            {
                "authority_id": "authority-1",
                "principal": "actor-1",
                "capability": "read",
                "scope": ["resource-1"],
                "constraints": {},
                "status": "ACTIVE",
            }
        ],
        "time": {"now": BASE.isoformat()},
    }
    action = {"capability": "read", "target": "resource-1"}

    result = RealReht().authorize(context, action)

    assert result.decision == "ALLOW"
