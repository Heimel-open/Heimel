import pytest

from valo_gateway.tool_adapters import (
    AccountingEffectTool,
    CapitalMarketsEffectTool,
    ClinicalOrderEffectTool,
    ClinicalRecordWriteEffectTool,
    CommercialCRMEffectTool,
    CommunicationsEffectTool,
    FinancialRailsEffectTool,
    HRPayrollEffectTool,
    HealthcareClaimsEffectTool,
    HealthcareEffectTool,
    IdentityAccessEffectTool,
    InsuranceEffectTool,
    LegalContractEffectTool,
    LendingEffectTool,
    MedicalDeviceEffectTool,
    MedicationEffectTool,
    PhysicalWorldEffectTool,
    ProcurementEffectTool,
    PublicSectorEffectTool,
    UnderwritingEffectTool,
)


DOMAIN_TOOLS = [
    FinancialRailsEffectTool,
    LendingEffectTool,
    UnderwritingEffectTool,
    InsuranceEffectTool,
    CapitalMarketsEffectTool,
    AccountingEffectTool,
    ProcurementEffectTool,
    LegalContractEffectTool,
    IdentityAccessEffectTool,
    HRPayrollEffectTool,
    HealthcareEffectTool,
    ClinicalOrderEffectTool,
    MedicationEffectTool,
    HealthcareClaimsEffectTool,
    ClinicalRecordWriteEffectTool,
    MedicalDeviceEffectTool,
    PublicSectorEffectTool,
    PhysicalWorldEffectTool,
    CommunicationsEffectTool,
    CommercialCRMEffectTool,
]


@pytest.mark.parametrize("tool_cls", DOMAIN_TOOLS)
def test_domain_effectors_cannot_be_invoked_directly(tool_cls):
    calls = []
    tool = tool_cls(lambda operation, parameters: calls.append((operation, parameters)))

    with pytest.raises(PermissionError, match="NO_DIRECT_EFFECT_PATH"):
        tool.invoke({"operation": "PAYMENT_RELEASE"})

    assert calls == []


def test_underwriting_and_healthcare_have_explicit_domains():
    dispatch = lambda operation, parameters: None

    assert UnderwritingEffectTool(dispatch).domain == "underwriting"
    assert ClinicalOrderEffectTool(dispatch).domain == "healthcare:clinical-order"
    assert MedicationEffectTool(dispatch).domain == "healthcare:medication"
    assert HealthcareClaimsEffectTool(dispatch).domain == "healthcare:claims"
    assert ClinicalRecordWriteEffectTool(dispatch).domain == "healthcare:record-write"
    assert MedicalDeviceEffectTool(dispatch).domain == "healthcare:medical-device"
