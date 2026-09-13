from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_function_fabric.contracts.common import RiskClass
from valo_function_fabric.substrates import (
    WHOP_SUBSTRATE,
    CapabilityStability,
    ExternalCapability,
    OperationClass,
    SurfaceKind,
)


def test_whop_projects_one_canonical_capability_to_all_agent_surfaces() -> None:
    projected = WHOP_SUBSTRATE.project("whop.products.create")

    assert {surface.kind for surface in projected} == set(SurfaceKind)
    assert {surface.capability_id for surface in projected} == {"whop.products.create"}
    assert {surface.authority_capability for surface in projected} == {"whop.catalog.write"}
    assert all(surface.requires_reht for surface in projected)
    assert len({surface.source_manifest_hash for surface in projected}) == 1


def test_whop_manifest_exposes_discovery_without_secret_values() -> None:
    manifest = WHOP_SUBSTRATE.machine_manifest()

    assert manifest["discovery"] == {
        "manifest": ["whop", "--llms"],
        "mcp_registration": ["whop", "mcp", "add"],
        "skill_generation": ["whop", "skills", "add"],
    }
    assert manifest["credential"] == {"env_var": "WHOP_API_KEY"}
    assert set(manifest["credential"]) == {"env_var"}
    assert "=" not in manifest["credential"]["env_var"]


def test_every_whop_external_execution_is_reht_gated() -> None:
    assert WHOP_SUBSTRATE.capabilities
    assert all(capability.requires_reht for capability in WHOP_SUBSTRATE.capabilities)


def test_every_whop_mutation_requires_external_effect_verification() -> None:
    mutations = [capability for capability in WHOP_SUBSTRATE.capabilities if not capability.read_only]

    assert mutations
    assert all(capability.verify_external_effect for capability in mutations)


def test_financial_production_and_experimental_capabilities_step_up() -> None:
    sensitive = [
        capability
        for capability in WHOP_SUBSTRATE.capabilities
        if capability.operation_class in {OperationClass.FINANCIAL, OperationClass.PRODUCTION}
        or capability.stability == CapabilityStability.EXPERIMENTAL
    ]

    assert sensitive
    assert all(capability.requires_step_up for capability in sensitive)
    assert all(capability.verify_external_effect for capability in sensitive)


def test_observe_capabilities_cannot_smuggle_external_effects() -> None:
    with pytest.raises(ValidationError):
        ExternalCapability(
            capability_id="whop.bad.observe",
            provider="whop",
            description="Invalid read with a write effect.",
            operation_class=OperationClass.OBSERVE,
            risk_class=RiskClass.R0_INFORMATIONAL,
            authority_capability="whop.business.read",
            provider_argv_prefix=("whop", "products", "list"),
            external_effects=("BUSINESS_STATE_WRITE",),
            source_url="https://docs.whop.com/developer/cli",
        )


def test_external_capability_cannot_bypass_reht() -> None:
    with pytest.raises(ValidationError):
        ExternalCapability(
            capability_id="whop.bad.write",
            provider="whop",
            description="Invalid write that attempts to bypass REHT.",
            operation_class=OperationClass.MUTATE,
            risk_class=RiskClass.R2_OPERATIONAL,
            authority_capability="whop.catalog.write",
            provider_argv_prefix=("whop", "products", "create"),
            external_effects=("BUSINESS_STATE_WRITE",),
            requires_reht=False,
            source_url="https://docs.whop.com/developer/cli",
        )


def test_whop_transfer_is_explicitly_experimental_and_financial() -> None:
    transfer = WHOP_SUBSTRATE.capability("whop.transfers.create")

    assert transfer.operation_class == OperationClass.FINANCIAL
    assert transfer.stability == CapabilityStability.EXPERIMENTAL
    assert transfer.requires_step_up
    assert transfer.verify_external_effect
