from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import racs_v02
import src.valo_platform.containment.gate
import src.valo_platform.containment.models
import valo_gateway
import valo_gateway.tool_adapters
import veritas

from valo_reht.reht import RealReht


@dataclass
class AuthorizedChain:
    now: datetime
    reht_result: Any
    racs_evaluation: racs_v02.GovernanceEvaluation
    authority: valo_gateway.AuthorityEnvelope
    action: valo_gateway.ActionEnvelope
    clearance: valo_gateway.Clearance
    permit: Any
    containment: src.valo_platform.containment.models.ContainmentAttestationV1
    path_binding: src.valo_platform.containment.models.ExecutionPathBindingV1


def _sha(label: str) -> str:
    return veritas.canonical_digest({"label": label})


def _containment(
    now: datetime,
) -> tuple[
    src.valo_platform.containment.models.ContainmentAttestationV1,
    src.valo_platform.containment.models.ExecutionPathBindingV1,
]:
    models = src.valo_platform.containment.models
    attestation = models.ContainmentAttestationV1(
        attestation_id="att:stage1",
        tenant_id="tenant:stage1",
        containment_domain_id="domain:stage1",
        runtime_instance_id="runtime:stage1",
        sandbox_environment_digest=_sha("environment"),
        model_artifact_digest=_sha("model"),
        agent_artifact_digest=_sha("agent"),
        harness_config_digest=_sha("harness"),
        network_egress_policy_digest=_sha("egress-policy"),
        mounted_capability_digests=(_sha("payment.submit"),),
        connector_digests=(_sha("payments"),),
        credential_broker_policy_digest=_sha("credential-policy"),
        approved_execution_adapters=("payments-adapter",),
        issuer_id="containment:issuer",
        issuer_signature="sig:controlled-fixture",
        issued_at=now - timedelta(seconds=5),
        expires_at=now + timedelta(minutes=10),
        generation=1,
        revocation_epoch=1,
    )
    binding = models.ExecutionPathBindingV1(
        binding_id="path:stage1",
        action_ref="action:payment.submit",
        principal_id="human:owner",
        delegation_chain_digest=_sha("delegation"),
        containment_attestation_digest=attestation.computed_digest,
        runtime_instance_id=attestation.runtime_instance_id,
        approved_egress_adapter="payments-adapter",
        credential_lease_ref="lease:payment",
        policy_path_head_digest=_sha("policy-path"),
        valid_from=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=5),
        revocation_epoch=1,
    )
    return attestation, binding


def _execution_context(now: datetime) -> dict[str, Any]:
    return {
        "identity": {"verified": True, "principal": "human:owner"},
        "actor": "human:owner",
        "time": {"now": now.isoformat()},
        "authority": [
            {
                "authority_id": "authority:stage1",
                "principal": "human:owner",
                "capability": "payment.submit",
                "scope": ["invoice:123"],
                "constraints": {"purpose_id": "settle_invoice"},
                "status": "ACTIVE",
                "validity": {
                    "valid_from": (now - timedelta(minutes=1)).isoformat(),
                    "valid_until": (now + timedelta(minutes=10)).isoformat(),
                },
            }
        ],
    }


def _action_contract(
    *,
    capability: str = "payment.submit",
    target: str = "invoice:123",
    amount: int = 1250,
) -> dict[str, Any]:
    return {
        "action_id": "action:payment.submit",
        "capability": capability,
        "target": target,
        "purpose_id": "settle_invoice",
        "constraints": {"purpose_id": "settle_invoice"},
        "parameters": {"amount": amount, "currency": "EUR"},
    }


def _authorized_chain(now: datetime | None = None) -> AuthorizedChain:
    now = now or datetime.now(UTC)
    containment, path_binding = _containment(now)
    check = src.valo_platform.containment.gate.verify_containment_for_clearance(
        attestation=containment,
        required_runtime_instance_id=containment.runtime_instance_id,
        checked_at=now,
    )
    assert (
        check.state
        is src.valo_platform.containment.models.ContainmentClearanceState.ALLOW
    )

    action_contract = _action_contract()
    reht_result = RealReht().authorize(_execution_context(now), action_contract)
    assert reht_result.decision == "ALLOW"
    assert reht_result.clearance_ref
    assert reht_result.permit_ref

    authority = valo_gateway.AuthorityEnvelope(
        envelope_id="authority:stage1",
        principal_id="human:owner",
        actor_id="human:owner",
        source=valo_gateway.AuthoritySource.INTERNAL,
        issuer="valo-kernel",
        capability_grants=["payment.submit"],
        resource_scope=["invoice:123"],
        purpose_scope=["settle_invoice"],
        issued_at=now - timedelta(minutes=1),
        valid_until=now + timedelta(minutes=10),
    )
    action = valo_gateway.ActionEnvelope(
        action_type="payment.submit",
        target="invoice:123",
        parameters={"amount": 1250, "currency": "EUR"},
        context_digest=reht_result.execution_context_hash,
        policy_digest=_sha("policy"),
        authority_envelope_id=authority.envelope_id,
        nonce="stage1-action-nonce",
    )
    racs_evaluation = racs_v02.GovernanceEvaluation(
        evaluation_id="racs-eval:stage1",
        action_id="action:payment.submit",
        action_envelope_digest=_sha(action.digest),
        tenant_id="tenant:stage1",
        evaluator_id="racs:stage1",
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
            assessment_ref="containment:stage1",
            assessment_digest=check.computed_digest,
        ),
        reasoning_authority=False,
        evaluated_at=now.isoformat(),
        valid_until=(now + timedelta(minutes=5)).isoformat(),
    )
    assert racs_evaluation.decision is racs_v02.Decision.ALLOW

    clearance = valo_gateway.Clearance(
        clearance_id="clearance:stage1",
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
        decided_at=now,
        valid_until=now + timedelta(minutes=5),
        reht_ref=reht_result.clearance_ref,
        evidence_refs=[check.computed_digest, racs_evaluation.model_digest()],
    )
    permit = valo_gateway.issue_execution_permit(
        clearance=clearance,
        authority=authority,
        action=action,
        expires_at=now + timedelta(minutes=1),
        now=now,
    )
    return AuthorizedChain(
        now=now,
        reht_result=reht_result,
        racs_evaluation=racs_evaluation,
        authority=authority,
        action=action,
        clearance=clearance,
        permit=permit,
        containment=containment,
        path_binding=path_binding,
    )


def _record_negative(
    service: veritas.VeritasChainService,
    *,
    case: str,
    action: dict[str, Any],
    now: datetime,
) -> str:
    evidence = veritas.BoundaryNegativeEvidenceV1(
        evidence_id=f"negative:{case}",
        tenant_id="tenant:stage1",
        execution_id=f"blocked:{case}",
        authorization_ref=f"reht:{case}",
        authorization_digest=_sha(f"authorization:{case}"),
        boundary_ref=f"boundary:{case}",
        boundary_digest=_sha(f"boundary:{case}"),
        enforcement_ref=f"enforcement:{case}",
        enforcement_digest=_sha(f"enforcement:{case}"),
        coverage_ref="coverage:stage1-e2e",
        coverage_digest=_sha("coverage:stage1-e2e"),
        excluded_action=action,
        window_start=now,
        window_end=now + timedelta(seconds=1),
    )
    receipt_hash = service.store_boundary_negative_evidence(evidence)
    assert service.verify_chain()
    return receipt_hash


def test_stage1_positive_path_reaches_effect_once_and_veritas_verifies() -> None:
    chain = _authorized_chain()
    calls: list[dict[str, Any]] = []
    tool = valo_gateway.tool_adapters.FunctionTool(
        "payment", lambda **kwargs: calls.append(kwargs) or {"ok": True}
    )
    result = valo_gateway.ValoGateway().execute(
        authority=chain.authority,
        clearance=chain.clearance,
        permit=chain.permit,
        action=chain.action,
        executor_id="executor:stage1",
        tool=tool,
        arguments={"amount": 1250},
        now=chain.now,
    )
    assert len(calls) == 1
    assert result.consumed_permit.consumed_at is not None

    observation = valo_gateway.build_veritas_execution_observation(
        authority=chain.authority,
        clearance=chain.clearance,
        action=chain.action,
        result=result,
    )
    service = veritas.VeritasChainService(veritas.WORMLog())
    service.store_gateway_execution_observation(
        observation, tenant_id="tenant:stage1"
    )
    assert service.verify_chain()
    assert len(service.worm.read_all()) == 1


def test_stage1_prompt_injection_cannot_mint_capability_or_reach_effect() -> None:
    now = datetime.now(UTC)
    action = _action_contract(capability="payment.override")
    result = RealReht().authorize(_execution_context(now), action)
    assert result.decision == "DENY"
    assert result.clearance_ref is None
    assert result.permit_ref is None

    service = veritas.VeritasChainService(veritas.WORMLog())
    _record_negative(service, case="prompt-injection", action=action, now=now)


def test_stage1_revoked_authority_blocks_before_gateway_invocation() -> None:
    chain = _authorized_chain()
    revoked = chain.authority.model_copy(
        update={"revoked_at": chain.now, "revocation_ref": "revocation:stage1"}
    )
    calls: list[int] = []
    tool = valo_gateway.tool_adapters.FunctionTool(
        "payment", lambda **_: calls.append(1)
    )
    with pytest.raises(ValueError, match="inactive or revoked"):
        valo_gateway.ValoGateway().execute(
            authority=revoked,
            clearance=chain.clearance,
            permit=chain.permit,
            action=chain.action,
            executor_id="executor:stage1",
            tool=tool,
            now=chain.now,
        )
    assert calls == []
    assert chain.permit.consumed_at is None
    service = veritas.VeritasChainService(veritas.WORMLog())
    _record_negative(
        service,
        case="revoked-authority",
        action=chain.action.model_dump(mode="json"),
        now=chain.now,
    )


def test_stage1_mutated_action_after_clearance_is_blocked_before_effect() -> None:
    chain = _authorized_chain()
    mutated = chain.action.model_copy(
        update={"parameters": {"amount": 999999, "currency": "EUR"}}
    )
    calls: list[int] = []
    with pytest.raises(ValueError, match="action binding mismatch"):
        valo_gateway.ValoGateway().execute(
            authority=chain.authority,
            clearance=chain.clearance,
            permit=chain.permit,
            action=mutated,
            executor_id="executor:stage1",
            tool=valo_gateway.tool_adapters.FunctionTool(
                "payment", lambda **_: calls.append(1)
            ),
            now=chain.now,
        )
    assert calls == []
    assert chain.permit.consumed_at is None


def test_stage1_replayed_permit_cannot_repeat_external_effect() -> None:
    chain = _authorized_chain()
    gateway = valo_gateway.ValoGateway()
    calls: list[int] = []
    tool = valo_gateway.tool_adapters.FunctionTool(
        "payment", lambda **_: calls.append(1) or "ok"
    )
    gateway.execute(
        authority=chain.authority,
        clearance=chain.clearance,
        permit=chain.permit,
        action=chain.action,
        executor_id="executor:stage1",
        tool=tool,
        now=chain.now,
    )
    with pytest.raises(ValueError, match="already consumed"):
        gateway.execute(
            authority=chain.authority,
            clearance=chain.clearance,
            permit=chain.permit,
            action=chain.action,
            executor_id="executor:stage1",
            tool=tool,
            now=chain.now,
        )
    assert calls == [1]


def test_stage1_direct_egress_bypass_is_denied_before_effect() -> None:
    chain = _authorized_chain()
    models = src.valo_platform.containment.models
    result = src.valo_platform.containment.gate.evaluate_egress(
        request=models.EgressRequestV1(
            request_id="egress:bypass",
            path_kind=models.EgressPathKind.NETWORK,
            destination="https://example.invalid",
        ),
        binding=chain.path_binding,
        attestation=chain.containment,
        checked_at=chain.now,
    )
    assert result.state is models.ContainmentClearanceState.DENY
    assert "EGRESS_PATH_DENY_BY_DEFAULT" in result.reasons


def test_stage1_tampered_completion_evidence_is_rejected_by_veritas() -> None:
    chain = _authorized_chain()
    result = valo_gateway.ValoGateway().execute(
        authority=chain.authority,
        clearance=chain.clearance,
        permit=chain.permit,
        action=chain.action,
        executor_id="executor:stage1",
        tool=valo_gateway.tool_adapters.FunctionTool(
            "payment", lambda **_: {"ok": True}
        ),
        now=chain.now,
    )
    observation = valo_gateway.build_veritas_execution_observation(
        authority=chain.authority,
        clearance=chain.clearance,
        action=chain.action,
        result=result,
    )
    tampered = dict(observation)
    tampered["status"] = "failed"
    with pytest.raises(
        veritas.GatewayExecutionObservationError, match="digest mismatch"
    ):
        veritas.GatewayExecutionObservationV1.verify(tampered)
