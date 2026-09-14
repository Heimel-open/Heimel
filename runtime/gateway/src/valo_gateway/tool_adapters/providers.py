from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import FunctionTool

ProviderDispatch = Callable[[str, dict[str, Any]], Any]


class ProviderEffectTool(FunctionTool):
    """Boundary-only provider effector."""

    def __init__(
        self,
        provider: str,
        dispatch: ProviderDispatch,
        *,
        capabilities: list[str] | None = None,
    ) -> None:
        if not provider:
            raise ValueError("provider must be explicit")
        self.provider = provider
        self._dispatch_provider = dispatch
        super().__init__(
            f"{provider}-effect",
            self._dispatch,
            capabilities=capabilities,
        )

    def _dispatch(self, operation: str, **parameters: Any) -> Any:
        if not isinstance(operation, str) or not operation:
            raise ValueError("provider operation must be explicit")
        return self._dispatch_provider(operation, dict(parameters))


class DomainEffectTool(ProviderEffectTool):
    """Boundary-only effector for a consequence domain."""

    def __init__(
        self,
        domain: str,
        dispatch: ProviderDispatch,
        *,
        capabilities: list[str] | None = None,
    ) -> None:
        if not domain:
            raise ValueError("domain must be explicit")
        self.domain = domain
        super().__init__(f"domain:{domain}", dispatch, capabilities=capabilities)


class GitHubEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("github", dispatch)


class StripeEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("stripe", dispatch)


class SlackEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("slack", dispatch)


class GoogleWorkspaceEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("google-workspace", dispatch)


class GmailEffectTool(GoogleWorkspaceEffectTool):
    """Explicit Gmail alias while keeping one Workspace provider boundary."""


class DatabaseEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("database", dispatch)


class AWSEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("aws", dispatch)


class AzureEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("azure", dispatch)


class GCPEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("gcp", dispatch)


class OpenRouterEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("openrouter", dispatch)


class BedrockEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("aws-bedrock", dispatch)


class AzureOpenAIEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("azure-openai", dispatch)


class VertexAIEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("vertex-ai", dispatch)


class TogetherEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("together", dispatch)


class GroqEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("groq", dispatch)


class HuggingFaceEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("huggingface", dispatch)


class OllamaEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("ollama", dispatch)


class FinancialRailsEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("financial-rails", dispatch)


class LendingEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("lending", dispatch)


class UnderwritingEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("underwriting", dispatch)


class InsuranceEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("insurance", dispatch)


class CapitalMarketsEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("capital-markets", dispatch)


class AccountingEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("accounting-finance-ops", dispatch)


class ProcurementEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("procurement-supply-chain", dispatch)


class LegalContractEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("legal-contract", dispatch)


class IdentityAccessEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("identity-access", dispatch)


class HRPayrollEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("hr-payroll", dispatch)


class HealthcareEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare", dispatch)


class ClinicalOrderEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:clinical-order", dispatch)


class MedicationEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:medication", dispatch)


class HealthcareClaimsEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:claims", dispatch)


class ClinicalRecordWriteEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:record-write", dispatch)


class MedicalDeviceEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:medical-device", dispatch)


class PublicSectorEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("public-sector", dispatch)


class PhysicalWorldEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("physical-world", dispatch)


class CommunicationsEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("communications-representation", dispatch)


class CommercialCRMEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("commercial-crm", dispatch)
