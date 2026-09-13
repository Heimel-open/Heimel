from __future__ import annotations

from datetime import UTC, datetime, timedelta

import src.valo_platform.containment.gate
import src.valo_platform.containment.models
import veritas


def _sha(label: str) -> str:
    return veritas.canonical_digest({"label": label})


def test_alt_egress_001_compromised_sandbox_cannot_gain_effect_without_governed_path() -> None:
    """ALT-EGRESS-001: containment compromise must not create a direct effect path."""
    now = datetime.now(UTC)
    models = src.valo_platform.containment.models

    attestation = models.ContainmentAttestationV1(
        attestation_id="att:compromised-sandbox",
        tenant_id="tenant:alt-egress",
        containment_domain_id="domain:alt-egress",
        runtime_instance_id="runtime:compromised",
        sandbox_environment_digest=_sha("compromised-environment"),
        model_artifact_digest=_sha("model"),
        agent_artifact_digest=_sha("agent"),
        harness_config_digest=_sha("harness"),
        network_egress_policy_digest=_sha("governed-egress-policy"),
        mounted_capability_digests=(_sha("payment.submit"),),
        connector_digests=(_sha("payments"),),
        credential_broker_policy_digest=_sha("credential-policy"),
        approved_execution_adapters=("payments-adapter",),
        issuer_id="containment:issuer",
        issuer_signature="sig:fixture",
        issued_at=now - timedelta(seconds=5),
        expires_at=now + timedelta(minutes=10),
        generation=1,
        revocation_epoch=1,
    )
    binding = models.ExecutionPathBindingV1(
        binding_id="path:governed-only",
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

    # The compromised runtime discovers an alternate network route and attempts
    # to use it directly, outside the adapter named by the governed binding.
    decision = src.valo_platform.containment.gate.evaluate_egress(
        request=models.EgressRequestV1(
            request_id="egress:alternate-network",
            path_kind=models.EgressPathKind.NETWORK,
            destination="https://alternate-effect.invalid",
        ),
        binding=binding,
        attestation=attestation,
        checked_at=now,
    )

    external_effects: list[str] = []
    if decision.state is models.ContainmentClearanceState.ALLOW:
        external_effects.append("executed")

    assert decision.state is models.ContainmentClearanceState.DENY
    assert "EGRESS_PATH_DENY_BY_DEFAULT" in decision.reasons
    assert external_effects == []
