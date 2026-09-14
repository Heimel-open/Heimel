from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..effect_contract import AdapterCapabilityManifest, ConsequenceOperation
from .base import FunctionTool


ProviderDispatch = Callable[[str, dict[str, Any]], Any]


def _manifest(adapter_id: str, provider: str, *operations: ConsequenceOperation) -> AdapterCapabilityManifest:
    return AdapterCapabilityManifest(
        adapter_id=adapter_id,
        provider=provider,
        operations=frozenset(operations),
    )


class ProviderEffectTool(FunctionTool):
    """Boundary-only provider effector. A manifest makes operation dispatch fail-closed."""

    def __init__(
        self,
        provider: str,
        dispatch: ProviderDispatch,
        *,
        capabilities: list[str] | None = None,
        manifest: AdapterCapabilityManifest | None = None,
    ) -> None:
        if not provider:
            raise ValueError("provider must be explicit")
        if manifest is not None and manifest.provider != provider:
            raise ValueError("adapter manifest provider must match effector provider")
        self.provider = provider
        self.manifest = manifest
        self._dispatch_provider = dispatch
        super().__init__(f"{provider}-effect", self._dispatch, capabilities=capabilities)

    def _dispatch(self, operation: str, **parameters: Any) -> Any:
        if not isinstance(operation, str) or not operation:
            raise ValueError("provider operation must be explicit")
        if self.manifest is not None:
            operation = self.manifest.assert_operation(operation).value
        return self._dispatch_provider(operation, dict(parameters))


class DomainEffectTool(ProviderEffectTool):
    def __init__(
        self,
        domain: str,
        dispatch: ProviderDispatch,
        *,
        operations: tuple[ConsequenceOperation, ...],
    ) -> None:
        if not domain:
            raise ValueError("domain must be explicit")
        self.domain = domain
        provider = f"domain:{domain}"
        super().__init__(
            provider,
            dispatch,
            manifest=_manifest(provider, provider, *operations),
        )


class GitHubEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("github", dispatch)
class StripeEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("stripe", dispatch)
class SlackEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("slack", dispatch)
class GoogleWorkspaceEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("google-workspace", dispatch)
class GmailEffectTool(GoogleWorkspaceEffectTool):
    """Explicit Gmail alias while keeping one Workspace provider boundary."""
class DatabaseEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("database", dispatch)
class AWSEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("aws", dispatch)
class AzureEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("azure", dispatch)
class GCPEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("gcp", dispatch)
class OpenRouterEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("openrouter", dispatch)
class BedrockEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("aws-bedrock", dispatch)
class AzureOpenAIEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("azure-openai", dispatch)
class VertexAIEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("vertex-ai", dispatch)
class TogetherEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("together", dispatch)
class GroqEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("groq", dispatch)
class HuggingFaceEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("huggingface", dispatch)
class OllamaEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None: super().__init__("ollama", dispatch)


class FinancialRailsEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("financial-rails", dispatch, operations=(ConsequenceOperation.PAYMENT_RELEASE,))
class LendingEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("lending", dispatch, operations=(ConsequenceOperation.CREDIT_APPROVE,))
class UnderwritingEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("underwriting", dispatch, operations=(ConsequenceOperation.INSURANCE_BIND, ConsequenceOperation.CREDIT_APPROVE))
class InsuranceEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("insurance", dispatch, operations=(ConsequenceOperation.INSURANCE_BIND, ConsequenceOperation.INSURANCE_CLAIM_PAY))
class CapitalMarketsEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("capital-markets", dispatch, operations=(ConsequenceOperation.TRADE_SUBMIT, ConsequenceOperation.TRADE_CANCEL))
class AccountingEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("accounting-finance-ops", dispatch, operations=(
            ConsequenceOperation.PAYMENT_RELEASE,
            ConsequenceOperation.VENDOR_BANK_CHANGE,
            ConsequenceOperation.INVOICE_CREATE,
            ConsequenceOperation.INVOICE_APPROVE,
            ConsequenceOperation.JOURNAL_POST,
            ConsequenceOperation.CREDIT_NOTE_ISSUE,
            ConsequenceOperation.VENDOR_CREATE,
        ))
class ProcurementEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("procurement-supply-chain", dispatch, operations=(ConsequenceOperation.INVOICE_APPROVE, ConsequenceOperation.VENDOR_CREATE, ConsequenceOperation.PAYMENT_RELEASE))
class LegalContractEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("legal-contract", dispatch, operations=(ConsequenceOperation.CONTRACT_SIGN, ConsequenceOperation.REGULATORY_FILE))
class IdentityAccessEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("identity-access", dispatch, operations=(ConsequenceOperation.USER_PRIVILEGE_GRANT, ConsequenceOperation.USER_PRIVILEGE_REVOKE))
class HRPayrollEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("hr-payroll", dispatch, operations=(ConsequenceOperation.PAYMENT_RELEASE, ConsequenceOperation.USER_PRIVILEGE_GRANT, ConsequenceOperation.USER_PRIVILEGE_REVOKE))
class HealthcareEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare", dispatch, operations=(ConsequenceOperation.CLINICAL_ORDER_CREATE, ConsequenceOperation.MEDICATION_PRESCRIBE, ConsequenceOperation.CLINICAL_RECORD_WRITE, ConsequenceOperation.HEALTHCARE_CLAIM_SUBMIT))
class ClinicalOrderEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:clinical-order", dispatch, operations=(ConsequenceOperation.CLINICAL_ORDER_CREATE,))
class MedicationEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:medication", dispatch, operations=(ConsequenceOperation.MEDICATION_PRESCRIBE,))
class HealthcareClaimsEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:claims", dispatch, operations=(ConsequenceOperation.HEALTHCARE_CLAIM_SUBMIT,))
class ClinicalRecordWriteEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:record-write", dispatch, operations=(ConsequenceOperation.CLINICAL_RECORD_WRITE,))
class MedicalDeviceEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("healthcare:medical-device", dispatch, operations=(ConsequenceOperation.PHYSICAL_ACTUATE,))
class PublicSectorEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("public-sector", dispatch, operations=(ConsequenceOperation.REGULATORY_FILE, ConsequenceOperation.PAYMENT_RELEASE, ConsequenceOperation.USER_PRIVILEGE_GRANT, ConsequenceOperation.USER_PRIVILEGE_REVOKE))
class PhysicalWorldEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("physical-world", dispatch, operations=(ConsequenceOperation.PHYSICAL_ACTUATE,))
class CommunicationsEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("communications-representation", dispatch, operations=(ConsequenceOperation.COMMUNICATION_SEND,))
class CommercialCRMEffectTool(DomainEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("commercial-crm", dispatch, operations=(ConsequenceOperation.CRM_COMMIT, ConsequenceOperation.CONTRACT_SIGN))
