import pytest

from valo_gateway.tool_adapters import (
    BillEffectTool,
    BrexEffectTool,
    CoupaEffectTool,
    DineroEffectTool,
    Dynamics365FinanceEffectTool,
    ExactOnlineEffectTool,
    FikenEffectTool,
    FortnoxEffectTool,
    FreshBooksEffectTool,
    InforEffectTool,
    NetSuiteEffectTool,
    OracleFusionEffectTool,
    PowerOfficeGoEffectTool,
    QuickBooksOnlineEffectTool,
    RampEffectTool,
    SAPS4HANAEffectTool,
    SageEffectTool,
    TipaltiEffectTool,
    TripletexEffectTool,
    TwentyFourSevenOfficeEffectTool,
    UniMicroEffectTool,
    VismaEAccountingEffectTool,
    WorkdayFinancialsEffectTool,
    XeroEffectTool,
    ZohoBooksEffectTool,
)


TOOLS = [
    TripletexEffectTool,
    VismaEAccountingEffectTool,
    PowerOfficeGoEffectTool,
    FikenEffectTool,
    TwentyFourSevenOfficeEffectTool,
    UniMicroEffectTool,
    FortnoxEffectTool,
    DineroEffectTool,
    XeroEffectTool,
    QuickBooksOnlineEffectTool,
    SageEffectTool,
    ZohoBooksEffectTool,
    FreshBooksEffectTool,
    ExactOnlineEffectTool,
    SAPS4HANAEffectTool,
    OracleFusionEffectTool,
    NetSuiteEffectTool,
    Dynamics365FinanceEffectTool,
    WorkdayFinancialsEffectTool,
    InforEffectTool,
    CoupaEffectTool,
    TipaltiEffectTool,
    BillEffectTool,
    RampEffectTool,
    BrexEffectTool,
]


@pytest.mark.parametrize("tool_cls", TOOLS)
def test_accounting_vendor_effectors_block_direct_invocation(tool_cls):
    tool = tool_cls(lambda operation, parameters: {"operation": operation, **parameters})

    with pytest.raises(PermissionError, match="NO_DIRECT_EFFECT_PATH"):
        tool.invoke(operation="post_journal", amount=100)


def test_tripletex_vendor_identity_is_explicit():
    tool = TripletexEffectTool(lambda operation, parameters: None)

    assert tool.vendor == "tripletex"
    assert tool.provider == "accounting:tripletex"
    assert tool.name == "accounting:tripletex-effect"
