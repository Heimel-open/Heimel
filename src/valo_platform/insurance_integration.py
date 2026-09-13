"""
K.3: Insurance Integration Layer

Connects governance enforcement to D&O insurance value:
- Premium discount calculation based on synchronization fidelity
- Insurer audit interface with evidence chain
- Compliance certification and control effectiveness scoring
- Financial impact analysis for CFO
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from decimal import Decimal


class RiskType(str, Enum):
    """Insurance risk categories."""
    POLICY_DRIFT = "policy_drift"
    ENFORCEMENT_FAILURE = "enforcement_failure"
    AUDIT_GAP = "audit_gap"
    REGULATORY_VIOLATION = "regulatory_violation"
    DATA_BREACH = "data_breach"
    AI_MODEL_MISUSE = "ai_model_misuse"


class ClaimStatus(str, Enum):
    """Claim lifecycle status."""
    FILED = "filed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    SETTLED = "settled"


class ExecutiveRole(str, Enum):
    """C-level executive roles carrying personal liability."""
    CEO = "ceo"
    CFO = "cfo"
    CTO = "cto"
    COO = "coo"
    CHIEF_COMPLIANCE_OFFICER = "chief_compliance_officer"
    CHIEF_RISK_OFFICER = "chief_risk_officer"
    GENERAL_COUNSEL = "general_counsel"
    BOARD_CHAIR = "board_chair"
    BOARD_MEMBER = "board_member"


@dataclass
class InsurancePolicy:
    """D&O insurance policy metadata."""
    policy_id: str
    insurer_name: str
    policy_period_start: str
    policy_period_end: str
    base_premium: Decimal  # Annual premium in USD
    coverage_limit: Decimal  # Max claim amount
    deductible: Decimal  # Per-claim deductible
    covered_risk_types: List[RiskType]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
    last_premium_calculated: Optional[str] = None
    current_premium: Optional[Decimal] = None


@dataclass
class InsuranceClaim:
    """Insurance claim filing with governance evidence."""
    claim_id: str
    policy_id: str
    risk_type: RiskType
    description: str
    governance_evidence: Dict[str, Any]  # Enforcement records, drift data, audit logs
    estimated_impact: Decimal  # USD amount at risk
    status: ClaimStatus = ClaimStatus.FILED
    filed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
    approved_amount: Optional[Decimal] = None
    approval_date: Optional[str] = None


@dataclass
class PremiumDiscount:
    """Premium discount calculation breakdown."""
    sync_fidelity: float  # 0-1, 1 = perfect sync
    base_discount_percent: float  # Tier-based: 0-15%
    enforcement_multiplier: float  # Bonus for consistent enforcement
    audit_multiplier: float  # Bonus for regular audits
    drift_detection_bonus: float  # Bonus for proactive drift detection
    total_discount_percent: float  # Sum of all discounts, capped at 25%
    estimated_annual_savings: Decimal


@dataclass
class ControlEffectivenessScore:
    """Governance control effectiveness rating."""
    overall_score: float  # 0-100, higher = better
    sync_score: float  # Procedure-rule synchronization
    enforcement_score: float  # Enforcement consistency
    audit_score: float  # Audit trail completeness
    drift_detection_score: float  # Drift prevention capability
    recommended_premium_tier: str  # "standard", "preferred", "elite"


@dataclass
class FinancialImpact:
    """Financial impact analysis for CFO."""
    annual_base_premium: Decimal
    annual_premium_discount: Decimal
    annual_premium_after_discount: Decimal
    estimated_audit_cost_avoidance: Decimal  # Cost avoided through automation
    estimated_compliance_cost_reduction: Decimal
    estimated_breach_risk_reduction: Decimal  # Expected loss reduction
    total_first_year_value: Decimal
    multiyear_value_5years: Decimal


@dataclass
class PersonalRiskExposure:
    """Personal liability exposure for individual executive."""
    executive_name: str
    executive_role: ExecutiveRole
    company_sector: str  # energy, healthcare, finance, AI, etc.
    personal_net_worth: Decimal  # Approximate net worth
    annual_salary: Decimal
    D_and_O_coverage_limit: Decimal  # How much D&O insurance covers them
    estimated_annual_personal_risk: Decimal  # Annual EV of personal liability
    risk_factors: List[str]  # governance_gaps, audit_failures, enforcement_gaps, etc.
    risk_mitigation_score: float  # 0-1, based on governance controls


@dataclass
class PersonalRiskReduction:
    """Personal risk reduction through governance controls."""
    executive_name: str
    executive_role: ExecutiveRole
    current_annual_personal_risk: Decimal  # EV of personal liability without controls
    reduced_annual_personal_risk: Decimal  # EV with governance controls in place
    annual_risk_avoided: Decimal
    risk_reduction_percent: float  # Percentage reduction (0-100%)
    confidence_level: str  # low, medium, high
    evidence_chain: List[str]  # Controls that reduce personal risk
    insurance_protection_gap: Decimal  # Personal risk exceeding D&O coverage


class InsuranceIntegration:
    """Insurance integration layer for D&O coverage and premium optimization."""

    def __init__(self):
        """Initialize insurance integration."""
        self.policies: Dict[str, InsurancePolicy] = {}
        self.claims: Dict[str, InsuranceClaim] = {}
        self.premium_history: Dict[str, List[Dict[str, Any]]] = {}

    def register_policy(
        self,
        policy_id: str,
        insurer_name: str,
        policy_period_start: str,
        policy_period_end: str,
        base_premium: Decimal,
        coverage_limit: Decimal,
        deductible: Decimal,
        covered_risk_types: List[str],
    ) -> InsurancePolicy:
        """Register a D&O insurance policy."""
        risk_types = [RiskType(rt) for rt in covered_risk_types]
        policy = InsurancePolicy(
            policy_id=policy_id,
            insurer_name=insurer_name,
            policy_period_start=policy_period_start,
            policy_period_end=policy_period_end,
            base_premium=base_premium,
            coverage_limit=coverage_limit,
            deductible=deductible,
            covered_risk_types=risk_types,
        )
        self.policies[policy_id] = policy
        self.premium_history[policy_id] = []
        return policy

    def calculate_premium_discount(
        self,
        policy_id: str,
        sync_fidelity: float,
        enforcement_count: int,
        drift_detections: int,
        audit_completeness: float,
    ) -> PremiumDiscount:
        """Calculate premium discount based on governance metrics."""
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")

        # Tier-based sync discount: 0-20% sync = 0%, 80-90% = 5%, 90-95% = 10%, 95%+ = 15%
        if sync_fidelity >= 0.95:
            sync_discount = 15.0
        elif sync_fidelity >= 0.90:
            sync_discount = 10.0
        elif sync_fidelity >= 0.80:
            sync_discount = 5.0
        else:
            sync_discount = 0.0

        # Enforcement consistency bonus: 1% per 100 enforcements (capped at 3%)
        enforcement_multiplier = min(0.03, enforcement_count * 0.01 / 100)

        # Audit completeness bonus: 0-5% based on audit rate
        audit_multiplier = audit_completeness * 0.05

        # Drift detection bonus: 2% for proactive monitoring
        drift_detection_bonus = 0.02 if drift_detections > 0 else 0.0

        # Total discount capped at 25%
        total_discount = min(
            0.25,
            (sync_discount / 100.0) + enforcement_multiplier + audit_multiplier + drift_detection_bonus,
        )

        policy = self.policies[policy_id]
        estimated_savings = policy.base_premium * Decimal(str(total_discount))

        discount = PremiumDiscount(
            sync_fidelity=sync_fidelity,
            base_discount_percent=sync_discount,
            enforcement_multiplier=enforcement_multiplier * 100,
            audit_multiplier=audit_multiplier * 100,
            drift_detection_bonus=drift_detection_bonus * 100,
            total_discount_percent=total_discount * 100,
            estimated_annual_savings=estimated_savings,
        )

        # Record in history
        self.premium_history[policy_id].append({
            "calculated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "discount": discount,
        })

        # Update policy
        policy.current_premium = policy.base_premium * Decimal(str(1 - total_discount))
        policy.last_premium_calculated = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

        return discount

    def calculate_control_effectiveness(
        self,
        sync_fidelity: float,
        enforcement_rate: float,
        audit_trail_completeness: float,
        drift_detection_enabled: bool,
    ) -> ControlEffectivenessScore:
        """Calculate governance control effectiveness score."""
        sync_score = sync_fidelity * 100
        enforcement_score = enforcement_rate * 100
        audit_score = audit_trail_completeness * 100
        drift_score = 100.0 if drift_detection_enabled else 50.0

        overall_score = (sync_score + enforcement_score + audit_score + drift_score) / 4

        if overall_score >= 95:
            tier = "elite"
        elif overall_score >= 85:
            tier = "preferred"
        else:
            tier = "standard"

        return ControlEffectivenessScore(
            overall_score=overall_score,
            sync_score=sync_score,
            enforcement_score=enforcement_score,
            audit_score=audit_score,
            drift_detection_score=drift_score,
            recommended_premium_tier=tier,
        )

    def calculate_financial_impact(
        self,
        policy_id: str,
        annual_base_premium: Decimal,
        premium_discount_percent: float,
        audit_cost_avoidance: Decimal,
        compliance_cost_reduction: Decimal,
        breach_risk_reduction_percent: float,
    ) -> FinancialImpact:
        """Calculate total financial impact for CFO presentation."""
        premium_discount = annual_base_premium * Decimal(str(premium_discount_percent / 100.0))
        premium_after_discount = annual_base_premium - premium_discount

        # Breach risk reduction: estimated as premium savings × (risk reduction %)
        breach_risk_reduction = annual_base_premium * Decimal(str(breach_risk_reduction_percent / 100.0))

        first_year_value = (
            premium_discount + audit_cost_avoidance + compliance_cost_reduction + breach_risk_reduction
        )
        multiyear_value = first_year_value * 5 * Decimal("0.95")  # 5% annual degradation

        return FinancialImpact(
            annual_base_premium=annual_base_premium,
            annual_premium_discount=premium_discount,
            annual_premium_after_discount=premium_after_discount,
            estimated_audit_cost_avoidance=audit_cost_avoidance,
            estimated_compliance_cost_reduction=compliance_cost_reduction,
            estimated_breach_risk_reduction=breach_risk_reduction,
            total_first_year_value=first_year_value,
            multiyear_value_5years=multiyear_value,
        )

    def file_claim(
        self,
        claim_id: str,
        policy_id: str,
        risk_type: str,
        description: str,
        governance_evidence: Dict[str, Any],
        estimated_impact: Decimal,
    ) -> InsuranceClaim:
        """File an insurance claim with governance evidence."""
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")

        claim = InsuranceClaim(
            claim_id=claim_id,
            policy_id=policy_id,
            risk_type=RiskType(risk_type),
            description=description,
            governance_evidence=governance_evidence,
            estimated_impact=estimated_impact,
        )
        self.claims[claim_id] = claim
        return claim

    def get_insurer_audit_report(
        self,
        policy_id: str,
        dashboard_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive audit report for insurer."""
        if policy_id not in self.policies:
            return {"error": f"Policy {policy_id} not found"}

        policy = self.policies[policy_id]
        related_claims = [
            c for c in self.claims.values() if c.policy_id == policy_id
        ]

        return {
            "policy_id": policy_id,
            "insurer": policy.insurer_name,
            "policy_period": {
                "start": policy.policy_period_start,
                "end": policy.policy_period_end,
            },
            "coverage_limit": str(policy.coverage_limit),
            "base_premium": str(policy.base_premium),
            "current_premium": str(policy.current_premium) if policy.current_premium else None,
            "governance_metrics": {
                "total_procedures": dashboard_data.get("total_procedures", 0),
                "total_rules": dashboard_data.get("total_rules", 0),
                "synced_rules": dashboard_data.get("synced_rules", 0),
                "drifted_rules": dashboard_data.get("drifted_rules", 0),
                "sync_fidelity_percent": (
                    dashboard_data.get("synced_rules", 0)
                    / max(dashboard_data.get("total_rules", 1), 1)
                    * 100
                ),
                "enforcement_decisions": dashboard_data.get("enforcement_decisions_this_month", 0),
                "families_covered": dashboard_data.get("families_covered", 0),
            },
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "risk_type": c.risk_type.value,
                    "status": c.status.value,
                    "filed_at": c.filed_at,
                    "estimated_impact": str(c.estimated_impact),
                    "approved_amount": str(c.approved_amount) if c.approved_amount else None,
                }
                for c in related_claims
            ],
            "audit_trail_completeness": "complete" if dashboard_data.get("enforcement_timeline") else "partial",
            "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }

    def get_policy_details(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed policy information."""
        if policy_id not in self.policies:
            return None

        policy = self.policies[policy_id]
        return {
            "policy_id": policy.policy_id,
            "insurer_name": policy.insurer_name,
            "policy_period_start": policy.policy_period_start,
            "policy_period_end": policy.policy_period_end,
            "base_premium": str(policy.base_premium),
            "current_premium": str(policy.current_premium) if policy.current_premium else str(policy.base_premium),
            "coverage_limit": str(policy.coverage_limit),
            "deductible": str(policy.deductible),
            "covered_risk_types": [rt.value for rt in policy.covered_risk_types],
            "created_at": policy.created_at,
            "last_premium_calculated": policy.last_premium_calculated,
        }

    def get_claims_by_policy(self, policy_id: str) -> List[Dict[str, Any]]:
        """Get all claims for a policy."""
        related_claims = [
            c for c in self.claims.values() if c.policy_id == policy_id
        ]
        return [
            {
                "claim_id": c.claim_id,
                "risk_type": c.risk_type.value,
                "description": c.description,
                "status": c.status.value,
                "estimated_impact": str(c.estimated_impact),
                "filed_at": c.filed_at,
                "approved_amount": str(c.approved_amount) if c.approved_amount else None,
            }
            for c in related_claims
        ]

    def calculate_personal_risk_exposure(
        self,
        executive_name: str,
        executive_role: str,
        company_sector: str,
        personal_net_worth: Decimal,
        annual_salary: Decimal,
        D_and_O_coverage_limit: Decimal,
        governance_sync_fidelity: float,
        has_audit_trail: bool,
        enforcement_rate: float,
    ) -> PersonalRiskExposure:
        """Calculate personal liability exposure for an executive.

        Personal risk = Expected Value of personal liability given role, sector, net worth
        Adjusted by governance control quality.
        """
        role = ExecutiveRole(executive_role)

        # Base personal risk by role (annual EV of potential personal liability)
        role_base_risk = {
            ExecutiveRole.CEO: Decimal("2000000"),  # Highest personal exposure
            ExecutiveRole.CFO: Decimal("1500000"),
            ExecutiveRole.CTO: Decimal("1200000"),
            ExecutiveRole.COO: Decimal("1200000"),
            ExecutiveRole.CHIEF_COMPLIANCE_OFFICER: Decimal("1500000"),
            ExecutiveRole.CHIEF_RISK_OFFICER: Decimal("1500000"),
            ExecutiveRole.GENERAL_COUNSEL: Decimal("1400000"),
            ExecutiveRole.BOARD_CHAIR: Decimal("1800000"),
            ExecutiveRole.BOARD_MEMBER: Decimal("1000000"),
        }

        base_risk = role_base_risk.get(role, Decimal("1000000"))

        # Sector multiplier (AI/Healthcare/Finance = higher personal risk)
        sector_multiplier = {
            "ai": 1.5,
            "healthcare": 1.4,
            "finance": 1.3,
            "energy": 1.2,
            "technology": 1.1,
            "other": 1.0,
        }.get(company_sector.lower(), 1.0)

        # Net worth multiplier: higher net worth = higher personal exposure (more to lose)
        if personal_net_worth < Decimal("1000000"):
            net_worth_multiplier = 0.5
        elif personal_net_worth < Decimal("5000000"):
            net_worth_multiplier = 0.8
        elif personal_net_worth < Decimal("20000000"):
            net_worth_multiplier = 1.2
        else:
            net_worth_multiplier = 1.5

        # Compute base annual personal risk
        annual_personal_risk = (
            base_risk
            * Decimal(str(sector_multiplier))
            * Decimal(str(net_worth_multiplier))
        )

        # Risk factors based on governance gaps
        risk_factors = []
        if governance_sync_fidelity < 0.80:
            risk_factors.append("governance_gaps")
        if not has_audit_trail:
            risk_factors.append("audit_failures")
        if enforcement_rate < 0.70:
            risk_factors.append("enforcement_gaps")

        # Mitigation score: how well governance controls reduce personal risk
        mitigation_score = min(
            1.0,
            (governance_sync_fidelity * 0.5 + (0.5 if has_audit_trail else 0.0) + enforcement_rate * 0.5) / 2.0
        )

        return PersonalRiskExposure(
            executive_name=executive_name,
            executive_role=role,
            company_sector=company_sector,
            personal_net_worth=personal_net_worth,
            annual_salary=annual_salary,
            D_and_O_coverage_limit=D_and_O_coverage_limit,
            estimated_annual_personal_risk=annual_personal_risk,
            risk_factors=risk_factors,
            risk_mitigation_score=mitigation_score,
        )

    def calculate_personal_risk_reduction(
        self,
        executive_name: str,
        executive_role: str,
        current_personal_risk: Decimal,
        D_and_O_coverage_limit: Decimal,
        governance_control_effectiveness: float,
        has_enforcement_timeline: bool,
        has_regular_audits: bool,
    ) -> PersonalRiskReduction:
        """Calculate personal risk reduction from governance controls."""
        role = ExecutiveRole(executive_role)

        # Risk reduction from controls: controls eliminate/mitigate personal exposure
        # Effectiveness = (sync fidelity + audit trail + enforcement) = 0-1
        # Conservative estimate: controls reduce personal risk by effectiveness * 60-80%
        max_reduction_percent = 0.75 if has_enforcement_timeline else 0.50
        max_reduction_percent = min(0.85, max_reduction_percent + (0.05 if has_regular_audits else 0.0))

        risk_reduction_percent = governance_control_effectiveness * max_reduction_percent * 100

        reduced_risk = current_personal_risk * Decimal(str(1 - governance_control_effectiveness * max_reduction_percent))
        annual_risk_avoided = current_personal_risk - reduced_risk

        # Insurance protection gap: personal risk exceeding D&O coverage
        insurance_gap = max(
            Decimal("0"),
            reduced_risk - D_and_O_coverage_limit,
        )

        # Confidence level based on evidence
        if has_enforcement_timeline and has_regular_audits and governance_control_effectiveness >= 0.9:
            confidence = "high"
        elif has_enforcement_timeline or has_regular_audits:
            confidence = "medium"
        else:
            confidence = "low"

        evidence_chain = []
        if governance_control_effectiveness >= 0.9:
            evidence_chain.append("Strong procedure-rule synchronization (90%+)")
        if has_enforcement_timeline:
            evidence_chain.append("Complete enforcement timeline with audit trail")
        if has_regular_audits:
            evidence_chain.append("Regular governance audits and certifications")

        return PersonalRiskReduction(
            executive_name=executive_name,
            executive_role=role,
            current_annual_personal_risk=current_personal_risk,
            reduced_annual_personal_risk=reduced_risk,
            annual_risk_avoided=annual_risk_avoided,
            risk_reduction_percent=risk_reduction_percent,
            confidence_level=confidence,
            evidence_chain=evidence_chain,
            insurance_protection_gap=insurance_gap,
        )
