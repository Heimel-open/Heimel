from __future__ import annotations

from .providers import AccountingEffectTool, ProviderDispatch


class AccountingVendorEffectTool(AccountingEffectTool):
    """Boundary-only accounting effector bound to one vendor/system."""

    vendor: str

    def __init__(self, vendor: str, dispatch: ProviderDispatch) -> None:
        if not vendor:
            raise ValueError("vendor must be explicit")
        self.vendor = vendor
        super().__init__(dispatch)
        self.provider = f"accounting:{vendor}"
        self.name = f"accounting:{vendor}-effect"


class TripletexEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("tripletex", dispatch)


class VismaEAccountingEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("visma-eaccounting", dispatch)


class PowerOfficeGoEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("poweroffice-go", dispatch)


class FikenEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("fiken", dispatch)


class TwentyFourSevenOfficeEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("24sevenoffice", dispatch)


class UniMicroEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("uni-micro", dispatch)


class FortnoxEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("fortnox", dispatch)


class DineroEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("dinero", dispatch)


class XeroEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("xero", dispatch)


class QuickBooksOnlineEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("quickbooks-online", dispatch)


class SageEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("sage", dispatch)


class ZohoBooksEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("zoho-books", dispatch)


class FreshBooksEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("freshbooks", dispatch)


class ExactOnlineEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("exact-online", dispatch)


class SAPS4HANAEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("sap-s4hana", dispatch)


class OracleFusionEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("oracle-fusion", dispatch)


class NetSuiteEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("netsuite", dispatch)


class Dynamics365FinanceEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("dynamics-365-finance", dispatch)


class WorkdayFinancialsEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("workday-financials", dispatch)


class InforEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("infor", dispatch)


class CoupaEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("coupa", dispatch)


class TipaltiEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("tipalti", dispatch)


class BillEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("bill", dispatch)


class RampEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("ramp", dispatch)


class BrexEffectTool(AccountingVendorEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("brex", dispatch)
