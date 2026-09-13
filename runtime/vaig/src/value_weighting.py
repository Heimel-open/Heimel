"""
VΛLΦ Value Weighting v0.1

Cross-domain value normalization: "How do we compare value across domains?"
Converts different value types (revenue, time, risk, strategic) into comparable scores.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List
from decimal import Decimal
import hashlib
from datetime import datetime, timezone


def _utcnow() -> datetime:
    """Return naive UTC for compatibility with persisted legacy timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ValueDomain(str, Enum):
    """Value domain types."""
    FINANCIAL = "FINANCIAL"  # Revenue, cost, savings (USD)
    LABOR = "LABOR"  # Time saved (hours → USD)
    RISK = "RISK"  # Risk reduction or increase (probability × impact)
    STRATEGIC = "STRATEGIC"  # Long-term positioning, moat building
    COMPLIANCE = "COMPLIANCE"  # Regulatory adherence, audit trail
    REPUTATION = "REPUTATION"  # Brand, trust, market perception


class ValueAxis(str, Enum):
    """Value measurement axes."""
    EVIDENCE = "EVIDENCE"  # Evidence collected, certainty increased
    DURATION = "DURATION"  # Time period affected (hours→ months)
    ATTRIBUTION = "ATTRIBUTION"  # Who benefits (individual→ org→ market)
    STRATEGIC = "STRATEGIC"  # Strategic alignment with company goals


@dataclass
class DomainRate:
    """Exchange rate between domains."""
    from_domain: ValueDomain
    to_domain: ValueDomain  # Always normalize to USD
    rate_usd_per_unit: Decimal
    unit_name: str  # "hour", "risk point", "compliance check", etc
    confidence: str  # "measured", "estimated", "assumed"
    last_updated: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> Dict:
        return {
            "from_domain": self.from_domain.value,
            "to_domain": self.to_domain.value,
            "rate_usd_per_unit": float(self.rate_usd_per_unit),
            "unit_name": self.unit_name,
            "confidence": self.confidence,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class ValueComponent:
    """Single value component."""
    domain: ValueDomain
    quantity: Decimal
    unit: str  # "USD", "hours", "risk points", "compliance checks"
    axis: ValueAxis
    period_days: int = 30  # Time period for this value
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "domain": self.domain.value,
            "quantity": float(self.quantity),
            "unit": self.unit,
            "axis": self.axis.value,
            "period_days": self.period_days,
            "metadata": self.metadata,
        }


@dataclass
class NormalizedValue:
    """Normalized value in USD equivalent."""
    domain: ValueDomain
    quantity: Decimal  # Original quantity
    unit: str
    normalized_usd: Decimal  # USD equivalent
    exchange_rate: Decimal  # Rate used for conversion
    axis: ValueAxis
    period_multiplier: float  # Adjustment for time period (30d baseline)
    confidence: str  # How certain we are about this conversion
    hash: str = ""
    timestamp: datetime = field(default_factory=_utcnow)

    def compute_hash(self) -> str:
        """Compute SHA256 for audit trail."""
        data = f"{self.domain.value}{self.normalized_usd}{self.timestamp.isoformat()}".encode()
        return hashlib.sha256(data).hexdigest()

    def __post_init__(self):
        if not self.hash:
            self.hash = self.compute_hash()

    def to_dict(self) -> Dict:
        return {
            "domain": self.domain.value,
            "quantity": float(self.quantity),
            "unit": self.unit,
            "normalized_usd": float(self.normalized_usd),
            "exchange_rate": float(self.exchange_rate),
            "axis": self.axis.value,
            "period_multiplier": self.period_multiplier,
            "confidence": self.confidence,
            "hash": self.hash,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class WeightingPolicy:
    """Policy for value weighting and normalization."""
    # Labor rates by seniority
    labor_rates_usd_per_hour: Dict[str, Decimal] = field(default_factory=lambda: {
        "junior": Decimal("50"),
        "senior": Decimal("100"),
        "management": Decimal("150"),
        "executive": Decimal("250"),
    })

    # Risk conversion: probability × impact → USD value
    risk_impact_factors: Dict[str, Decimal] = field(default_factory=lambda: {
        "low": Decimal("1000"),      # $1k per low-impact event prevented
        "medium": Decimal("10000"),   # $10k per medium-impact event
        "high": Decimal("100000"),    # $100k per high-impact event
        "critical": Decimal("1000000"), # $1M per critical event
    })

    # Strategic value multiplier by alignment
    strategic_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "core_mission": 2.0,      # Double if core to mission
        "aligned": 1.5,           # 50% bonus if aligned
        "neutral": 1.0,           # No bonus if neutral
        "misaligned": 0.5,        # Discount if misaligned
    })

    # Period adjustments (30 days baseline)
    period_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "hourly": 0.1,
        "daily": 0.5,
        "weekly": 1.0,
        "monthly": 1.0,
        "quarterly": 1.5,
        "annual": 3.0,
    })


class ValueWeighting:
    """VΛLΦ Value Weighting: Cross-domain normalization."""

    def __init__(self, policy: WeightingPolicy = None):
        self.policy = policy or WeightingPolicy()
        self.exchange_rates: Dict[str, DomainRate] = {}
        self.normalizations: List[NormalizedValue] = []
        self._initialize_default_rates()

    def _initialize_default_rates(self):
        """Initialize default exchange rates for common value domains."""
        # Financial to USD: 1:1
        self.register_exchange_rate(DomainRate(
            from_domain=ValueDomain.FINANCIAL,
            to_domain=ValueDomain.FINANCIAL,
            rate_usd_per_unit=Decimal("1.0"),
            unit_name="USD",
            confidence="measured"
        ))
        # Labor to USD: Use policy rates
        self.register_exchange_rate(DomainRate(
            from_domain=ValueDomain.LABOR,
            to_domain=ValueDomain.FINANCIAL,
            rate_usd_per_unit=self.policy.labor_rates_usd_per_hour.get("junior", Decimal("50")),
            unit_name="hour",
            confidence="estimated"
        ))
        # Risk to USD: Use policy factors
        self.register_exchange_rate(DomainRate(
            from_domain=ValueDomain.RISK,
            to_domain=ValueDomain.FINANCIAL,
            rate_usd_per_unit=self.policy.risk_impact_factors.get("low", Decimal("1000")),
            unit_name="risk_point",
            confidence="estimated"
        ))

    def normalize(self, component: ValueComponent) -> NormalizedValue:
        """
        Normalize a value component to USD equivalent.

        Returns:
            NormalizedValue with USD conversion and confidence
        """
        # Get exchange rate
        rate_key = f"{component.domain.value}_to_USD"
        if rate_key not in self.exchange_rates:
            rate_key = "default"  # Use default if domain-specific not found

        # Financial domain is already in USD
        if component.domain == ValueDomain.FINANCIAL:
            normalized = NormalizedValue(
                domain=component.domain,
                quantity=component.quantity,
                unit=component.unit,
                normalized_usd=component.quantity,
                exchange_rate=Decimal("1.0"),
                axis=component.axis,
                period_multiplier=self._get_period_multiplier(component.period_days),
                confidence="measured",
            )
        elif component.domain == ValueDomain.LABOR:
            # Extract seniority if in metadata
            seniority = component.metadata.get("seniority", "senior")
            rate = self.policy.labor_rates_usd_per_hour.get(seniority, Decimal("100"))
            period_mult = self._get_period_multiplier(component.period_days)
            normalized_base = component.quantity * rate
            normalized = NormalizedValue(
                domain=component.domain,
                quantity=component.quantity,
                unit=component.unit,
                normalized_usd=normalized_base * Decimal(str(period_mult)),
                exchange_rate=rate,
                axis=component.axis,
                period_multiplier=period_mult,
                confidence="estimated",
            )
        elif component.domain == ValueDomain.RISK:
            # Risk: probability × impact factor
            probability = Decimal(str(component.metadata.get("probability", 0.5)))
            severity = component.metadata.get("severity", "medium")
            impact_factor = self.policy.risk_impact_factors.get(severity, Decimal("10000"))
            period_mult = self._get_period_multiplier(component.period_days)
            risk_value = component.quantity * probability * impact_factor
            normalized = NormalizedValue(
                domain=component.domain,
                quantity=component.quantity,
                unit=component.unit,
                normalized_usd=risk_value * Decimal(str(period_mult)),
                exchange_rate=impact_factor,
                axis=component.axis,
                period_multiplier=period_mult,
                confidence="estimated",
            )
        elif component.domain == ValueDomain.STRATEGIC:
            # Strategic: base value × alignment multiplier
            alignment = component.metadata.get("alignment", "neutral")
            mult = self.policy.strategic_multipliers.get(alignment, 1.0)
            period_mult = self._get_period_multiplier(component.period_days)
            normalized_base = component.quantity * Decimal(str(mult))
            normalized = NormalizedValue(
                domain=component.domain,
                quantity=component.quantity,
                unit=component.unit,
                normalized_usd=normalized_base * Decimal(str(period_mult)),
                exchange_rate=Decimal(str(mult)),
                axis=component.axis,
                period_multiplier=period_mult,
                confidence="estimated",
            )
        elif component.domain == ValueDomain.COMPLIANCE:
            # Compliance: value per compliance check (assume $5k per major compliance check)
            period_mult = self._get_period_multiplier(component.period_days)
            normalized_base = component.quantity * Decimal("5000")
            normalized = NormalizedValue(
                domain=component.domain,
                quantity=component.quantity,
                unit=component.unit,
                normalized_usd=normalized_base * Decimal(str(period_mult)),
                exchange_rate=Decimal("5000"),
                axis=component.axis,
                period_multiplier=period_mult,
                confidence="estimated",
            )
        elif component.domain == ValueDomain.REPUTATION:
            # Reputation: market perception value (hard to measure, high uncertainty)
            # Assume $1 per reputation point as conservative baseline
            period_mult = self._get_period_multiplier(component.period_days)
            normalized = NormalizedValue(
                domain=component.domain,
                quantity=component.quantity,
                unit=component.unit,
                normalized_usd=component.quantity * Decimal(str(period_mult)),
                exchange_rate=Decimal("1.0"),
                axis=component.axis,
                period_multiplier=period_mult,
                confidence="claimed",  # Highly uncertain
            )
        else:
            raise ValueError(f"Unknown domain: {component.domain}")

        self.normalizations.append(normalized)
        return normalized

    def normalize_multiple(self, components: List[ValueComponent]) -> Dict[str, Decimal]:
        """
        Normalize multiple components and return aggregate.

        Returns:
            Dict with total_usd, by_domain breakdown, and confidence
        """
        normalizations = [self.normalize(c) for c in components]

        total = Decimal("0")
        by_domain = {}
        confidence_scores = []

        for norm in normalizations:
            total += norm.normalized_usd
            domain_name = norm.domain.value
            if domain_name not in by_domain:
                by_domain[domain_name] = Decimal("0")
            by_domain[domain_name] += norm.normalized_usd
            confidence_scores.append(self._confidence_score(norm.confidence))

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        return {
            "total_usd": float(total),
            "by_domain": {k: float(v) for k, v in by_domain.items()},
            "avg_confidence": avg_confidence,
            "sample_size": len(normalizations),
            "normalizations": [n.to_dict() for n in normalizations],
        }

    def register_exchange_rate(self, rate: DomainRate):
        """Register new exchange rate for custom domains."""
        key = f"{rate.from_domain.value}_to_{rate.to_domain.value}"
        self.exchange_rates[key] = rate

    def _get_period_multiplier(self, period_days: int) -> float:
        """Get value multiplier based on time period."""
        if period_days <= 1:
            return self.policy.period_multipliers.get("hourly", 0.1)
        elif period_days <= 7:
            return self.policy.period_multipliers.get("weekly", 1.0)
        elif period_days <= 30:
            return self.policy.period_multipliers.get("monthly", 1.0)
        elif period_days <= 90:
            return self.policy.period_multipliers.get("quarterly", 1.5)
        else:
            return self.policy.period_multipliers.get("annual", 3.0)

    def _confidence_score(self, confidence: str) -> float:
        """Convert confidence label to numeric score."""
        scores = {
            "measured": 1.0,
            "estimated": 0.7,
            "claimed": 0.3,
        }
        return scores.get(confidence, 0.5)

    def get_normalization_log(self) -> List[Dict]:
        """Return all normalizations as dicts."""
        return [n.to_dict() for n in self.normalizations]
