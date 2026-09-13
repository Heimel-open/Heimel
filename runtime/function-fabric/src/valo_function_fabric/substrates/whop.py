from __future__ import annotations

from ..contracts.common import RiskClass
from .contracts import (
    CapabilityStability,
    CredentialReference,
    ExternalCapability,
    ExternalSubstrate,
    OperationClass,
)

WHOP_CLI_DOCS = "https://docs.whop.com/developer/cli"
WHOP_TRANSFER_DOCS = "https://docs.whop.com/api-reference/beta/transfers/create-transfer"


def build_whop_substrate() -> ExternalSubstrate:
    """Reference integration for a business system that is directly agent-operable.

    Whop is deliberately treated as an external execution substrate. Function
    Fabric describes capabilities and surfaces; REHT remains the authorization
    boundary and Veritas/BARO remain responsible for downstream evidence.
    """

    return ExternalSubstrate(
        provider="whop",
        manifest_command=("whop", "--llms"),
        mcp_registration_command=("whop", "mcp", "add"),
        skill_generation_command=("whop", "skills", "add"),
        credential=CredentialReference(env_var="WHOP_API_KEY"),
        capabilities=(
            ExternalCapability(
                capability_id="whop.products.list",
                provider="whop",
                description="List products for the selected Whop business.",
                operation_class=OperationClass.OBSERVE,
                risk_class=RiskClass.R0_INFORMATIONAL,
                authority_capability="whop.business.read",
                scope_keys=("account_id",),
                provider_argv_prefix=("whop", "products", "list"),
                source_url=WHOP_CLI_DOCS,
            ),
            ExternalCapability(
                capability_id="whop.products.create",
                provider="whop",
                description="Create a product in the selected Whop business.",
                operation_class=OperationClass.MUTATE,
                risk_class=RiskClass.R2_OPERATIONAL,
                authority_capability="whop.catalog.write",
                scope_keys=("account_id",),
                provider_argv_prefix=("whop", "products", "create"),
                external_effects=("BUSINESS_STATE_WRITE",),
                verify_external_effect=True,
                source_url=WHOP_CLI_DOCS,
            ),
            ExternalCapability(
                capability_id="whop.plans.create",
                provider="whop",
                description="Create pricing for the selected Whop business.",
                operation_class=OperationClass.MUTATE,
                risk_class=RiskClass.R3_FINANCIAL_LEGAL,
                authority_capability="whop.pricing.write",
                scope_keys=("account_id",),
                provider_argv_prefix=("whop", "plans", "create"),
                external_effects=("PRICING_CHANGE",),
                requires_step_up=True,
                verify_external_effect=True,
                source_url=WHOP_CLI_DOCS,
            ),
            ExternalCapability(
                capability_id="whop.checkout-configurations.create",
                provider="whop",
                description="Create a shareable checkout configuration.",
                operation_class=OperationClass.MUTATE,
                risk_class=RiskClass.R2_OPERATIONAL,
                authority_capability="whop.checkout.write",
                scope_keys=("account_id", "plan_id"),
                provider_argv_prefix=("whop", "checkout-configurations", "create"),
                external_effects=("CHECKOUT_CONFIGURATION_WRITE",),
                verify_external_effect=True,
                source_url=WHOP_CLI_DOCS,
            ),
            ExternalCapability(
                capability_id="whop.stats.time_series",
                provider="whop",
                description="Read financial time-series statistics.",
                operation_class=OperationClass.OBSERVE,
                risk_class=RiskClass.R0_INFORMATIONAL,
                authority_capability="whop.financials.read",
                scope_keys=("account_id",),
                provider_argv_prefix=("whop", "stats", "time_series"),
                source_url=WHOP_CLI_DOCS,
            ),
            ExternalCapability(
                capability_id="whop.transfers.create",
                provider="whop",
                description="Move value between Whop identities or into a claim link.",
                operation_class=OperationClass.FINANCIAL,
                stability=CapabilityStability.EXPERIMENTAL,
                risk_class=RiskClass.R3_FINANCIAL_LEGAL,
                authority_capability="whop.money.move",
                scope_keys=("account_id", "destination", "amount", "currency"),
                provider_argv_prefix=("whop", "transfers", "create"),
                external_effects=("MONEY_MOVEMENT",),
                requires_step_up=True,
                verify_external_effect=True,
                source_url=WHOP_TRANSFER_DOCS,
            ),
            ExternalCapability(
                capability_id="whop.ad-campaigns.create",
                provider="whop",
                description="Create paid-acquisition campaign state.",
                operation_class=OperationClass.FINANCIAL,
                risk_class=RiskClass.R3_FINANCIAL_LEGAL,
                authority_capability="whop.ads.spend",
                scope_keys=("account_id", "budget"),
                provider_argv_prefix=("whop", "ad-campaigns", "create"),
                external_effects=("PAID_ACQUISITION_COMMITMENT",),
                requires_step_up=True,
                verify_external_effect=True,
                source_url=WHOP_CLI_DOCS,
            ),
            ExternalCapability(
                capability_id="whop.apps.deploy",
                provider="whop",
                description="Build, upload, and by default promote a Whop app.",
                operation_class=OperationClass.PRODUCTION,
                risk_class=RiskClass.R2_OPERATIONAL,
                authority_capability="whop.production.deploy",
                scope_keys=("app_id",),
                provider_argv_prefix=("whop", "apps", "deploy"),
                external_effects=("PRODUCTION_DEPLOYMENT",),
                requires_step_up=True,
                verify_external_effect=True,
                source_url=WHOP_CLI_DOCS,
            ),
            ExternalCapability(
                capability_id="whop.apps.builds.promote",
                provider="whop",
                description="Promote an uploaded Whop app build to production.",
                operation_class=OperationClass.PRODUCTION,
                risk_class=RiskClass.R2_OPERATIONAL,
                authority_capability="whop.production.promote",
                scope_keys=("app_id", "build_id"),
                provider_argv_prefix=("whop", "apps", "builds", "promote"),
                external_effects=("PRODUCTION_PROMOTION",),
                requires_step_up=True,
                verify_external_effect=True,
                source_url=WHOP_CLI_DOCS,
            ),
        ),
    )


WHOP_SUBSTRATE = build_whop_substrate()
