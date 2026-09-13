"""RiskContract: human-defined risk classifications for RRP evidence validation."""

from enum import Enum
from typing import Dict


class RiskDomain(Enum):
    FINANCIAL = "financial"
    MEDICAL = "medical"
    AVIATION = "aviation"
    LEGAL = "legal"
    SAFETY_CRITICAL = "safety_critical"
    GENERAL = "general"


class RiskTier(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    ELEVATED = "elevated"
    LOW = "low"
    MINIMAL = "minimal"


RISK_CONTRACT: Dict[str, Dict] = {
    "LARGE_TRANSFER": {
        "domain": RiskDomain.FINANCIAL.value,
        "tier": RiskTier.CRITICAL.value,
        "requires_evidence": True,
        "requires_corroboration": True,
        "freshness_seconds": 300,
        "override_allowed": True,
        "override_min_authority": "BOA-FINANCIAL-L2",
        "segmentation_rule": "ISOLATED",
    },
    "FLIGHT_CLEARANCE": {
        "domain": RiskDomain.AVIATION.value,
        "tier": RiskTier.CRITICAL.value,
        "requires_evidence": True,
        "requires_corroboration": True,
        "freshness_seconds": 900,
        "override_allowed": True,
        "override_min_authority": "ATC-SUPERVISOR-L3",
        "segmentation_rule": "ISOLATED",
    },
    "MEDICAL_INTERVENTION": {
        "domain": RiskDomain.MEDICAL.value,
        "tier": RiskTier.CRITICAL.value,
        "requires_evidence": True,
        "requires_corroboration": False,
        "freshness_seconds": 600,
        "override_allowed": True,
        "override_min_authority": "PHYSICIAN-ON-CALL",
        "segmentation_rule": "ISOLATED",
    },
    "LEGAL_FILING": {
        "domain": RiskDomain.LEGAL.value,
        "tier": RiskTier.HIGH.value,
        "requires_evidence": True,
        "requires_corroboration": True,
        "freshness_seconds": 86400,
        "override_allowed": True,
        "override_min_authority": "LEGAL-REVIEWER-L2",
        "segmentation_rule": "ISOLATED",
    },
    "STATUS_CHECK": {
        "domain": RiskDomain.GENERAL.value,
        "tier": RiskTier.LOW.value,
        "requires_evidence": False,
        "requires_corroboration": False,
        "freshness_seconds": None,
        "override_allowed": False,
        "override_min_authority": None,
        "segmentation_rule": "OPEN",
    },
}

DEFAULT_CONTRACT: Dict = {
    "domain": RiskDomain.GENERAL.value,
    "tier": RiskTier.ELEVATED.value,
    "requires_evidence": True,
    "requires_corroboration": False,
    "freshness_seconds": 3600,
    "override_allowed": True,
    "override_min_authority": "BOA-GENERAL-L1",
    "segmentation_rule": "OPEN",
}

ISOLATED_DOMAIN_PAIRS = {
    (RiskDomain.FINANCIAL.value, RiskDomain.MEDICAL.value),
    (RiskDomain.MEDICAL.value, RiskDomain.FINANCIAL.value),
    (RiskDomain.AVIATION.value, RiskDomain.FINANCIAL.value),
    (RiskDomain.FINANCIAL.value, RiskDomain.AVIATION.value),
    (RiskDomain.AVIATION.value, RiskDomain.MEDICAL.value),
    (RiskDomain.MEDICAL.value, RiskDomain.AVIATION.value),
    (RiskDomain.LEGAL.value, RiskDomain.MEDICAL.value),
    (RiskDomain.MEDICAL.value, RiskDomain.LEGAL.value),
}


def get_risk_contract(action_type: str) -> Dict:
    return dict(RISK_CONTRACT.get(action_type, DEFAULT_CONTRACT))


def _domain_value(domain):
    return domain.value if isinstance(domain, RiskDomain) else domain


def is_domain_isolated(source, target) -> bool:
    source_value = _domain_value(source)
    target_value = _domain_value(target)
    if source_value == target_value:
        return False
    return (source_value, target_value) in ISOLATED_DOMAIN_PAIRS
