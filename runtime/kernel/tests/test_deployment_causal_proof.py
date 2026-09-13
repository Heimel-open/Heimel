from __future__ import annotations

from valo_kernel.causal_capacity import GovernedEffectBoundary, assess_causal_capacity
from valo_kernel.deployment_causal_proof import DeploymentCausalPathProof
from valo_kernel.effect_boundary import EffectChannel, EffectChannelKind


def _assessment():
    channel = EffectChannel(
        channel_id="human-relay",
        kind=EffectChannelKind.HUMAN_RELAY,
        source_domain="untrusted",
        target_domain="external",
        crosses_trust_boundary=True,
        governed_boundary_ref="reht",
    )
    boundary = GovernedEffectBoundary(
        boundary_ref="reht",
        explicit_declared=True,
        exact_effect_bound=True,
        authorized_now=True,
        deny_enforceable=True,
        fail_closed=True,
        evidence_capable=True,
    )
    return assess_causal_capacity((channel,), boundaries=(boundary,))


def _proof(**overrides: object) -> DeploymentCausalPathProof:
    values: dict[str, object] = {
        "deployment_id": "deployment-1",
        "assessed_source_commit": "abc123",
        "declared_reachable_channel_ids": ("human-relay",),
        "assessed_channel_ids": ("human-relay",),
        "unknown_paths_fail_closed": True,
        "boundary_assessment": _assessment(),
        "inventory_evidence_refs": ("inventory:1",),
        "enforcement_evidence_refs": ("enforcement:1",),
    }
    values.update(overrides)
    return DeploymentCausalPathProof(**values)


def test_complete_declared_scope_is_conformant() -> None:
    assert _proof().conformant_for_declared_scope is True


def test_inventory_mismatch_is_not_conformant() -> None:
    assert _proof(assessed_channel_ids=()).conformant_for_declared_scope is False


def test_unknown_paths_must_fail_closed() -> None:
    assert _proof(unknown_paths_fail_closed=False).conformant_for_declared_scope is False


def test_inventory_and_enforcement_evidence_are_required() -> None:
    assert _proof(inventory_evidence_refs=()).conformant_for_declared_scope is False
    assert _proof(enforcement_evidence_refs=()).conformant_for_declared_scope is False
