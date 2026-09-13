"""Customer-controlled BARO weight profiles + three-layer control (valo-platform #457).

This is the *advisory* control plane: customers define what BARO should weigh,
within permitted governance boundaries. It is NOT an authority. The customer can
never silently disable platform invariants or regulatory minimums.

Layer precedence (deterministic, explicit):
    Platform invariants
    > regulatory minimums
    > contractual minimums
    > organisation profile
    > domain profile
    > action-class override
    > temporary approved exception

Conflicts are reported explicitly and receipted — they are never swallowed.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.valo_platform.models.core_receipt import ExecutionDecision
from src.valo_platform.statistical_provenance import (
    DecomposedStatisticalSignals,
    StatisticalProvenanceRecord,
)

# Protected weight kinds carry a regulatory floor (env-overridable, never 0 hard-coded).
_REG_FLOOR_ENV = os.environ.get("VALO_SP_REG_FLOOR", "0.1")
REGULATORY_FLOOR = float(_REG_FLOOR_ENV)


class ProfileScope(str, Enum):
    ORGANISATION = "organisation"
    DOMAIN = "domain"
    JURISDICTION = "jurisdiction"
    ACTION_CLASS = "action_class"
    RISK_TIER = "risk_tier"


class WeightKind(str, Enum):
    EVIDENCE_QUALITY = "evidence_quality"
    INFLUENCE_RISK = "influence_risk"
    CONSEQUENCE = "consequence"
    CONTEXT = "context"


class HardRule(str, Enum):
    """Platform invariants — present in EVERY profile, never removable by config."""

    PROVENANCE_RECORDED = "provenance_recorded"
    WEIGHTS_VISIBLE = "weights_visible"
    NO_HIDDEN_OVERRIDE = "no_hidden_override"
    BARO_CANNOT_DECIDE = "baro_cannot_decide"
    REHT_DECISION_AUTHORITY = "reht_decision_authority"
    UNCERTAIN_AI_NOT_FACT = "uncertain_ai_not_presented_as_fact"


# The non-disablable set. A profile missing any of these is invalid.
PLATFORM_INVARIANTS: frozenset = frozenset(HardRule)

# Which weight kinds are "protected" (cannot be zeroed below the regulatory floor).
PROTECTED_WEIGHTS = frozenset(
    {WeightKind.INFLUENCE_RISK, WeightKind.EVIDENCE_QUALITY}
)


class BaroWeightProfile(BaseModel):
    """Versioned, customer-controlled BARO weighting profile (advisory only)."""

    profile_id: str
    version: str = Field(..., description="semver-style, e.g. 1.0.0")
    owner: str
    approvers: List[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    expiry_or_review_date: Optional[str] = None
    scope: Dict[ProfileScope, str] = Field(default_factory=dict)
    weights: Dict[WeightKind, float] = Field(default_factory=dict)
    hard_rules: List[HardRule] = Field(
        default_factory=lambda: list(PLATFORM_INVARIANTS)
    )
    regulatory_minimums: Dict[str, float] = Field(default_factory=dict)
    rollback_target: Optional[str] = None
    change_reason: str = ""
    is_active: bool = False

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if not self.expiry_or_review_date:
            return False
        now = now or datetime.now(timezone.utc)
        try:
            exp = datetime.fromisoformat(self.expiry_or_review_date)
        except ValueError:
            return False
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp <= now


class ThreeLayerControl:
    """Validates a profile against the three-layer model.

    Layer A (platform invariants) and Layer B (regulatory minimums) constrain
    what Layer C (customer weights) may do. A profile that weakens a mandatory
    control is rejected.
    """

    def validate(
        self, profile: BaroWeightProfile
    ) -> Tuple[bool, List[str], List[str]]:
        """Return (ok, invariant_violations, regulatory_conflicts)."""
        violations: List[str] = []
        conflicts: List[str] = []

        # Layer A — platform invariants cannot be removed.
        present = set(profile.hard_rules)
        missing = PLATFORM_INVARIANTS - present
        for m in missing:
            violations.append(f"profile removes platform invariant: {m.value}")

        # Layer B — protected weights cannot be zeroed below the regulatory floor.
        for kind in PROTECTED_WEIGHTS:
            w = profile.weights.get(kind, 0.0)
            floor = profile.regulatory_minimums.get(kind.value, REGULATORY_FLOOR)
            if w < floor:
                conflicts.append(
                    f"{kind.value} weight {w} below regulatory floor {floor}"
                )

        ok = not violations and not conflicts
        return ok, violations, conflicts


class PolicyPrecedenceResolver:
    """Resolves effective weights under deterministic precedence.

    Precedence (high -> low): platform invariants > regulatory minimums >
    contractual minimums > organisation > domain > action-class > temporary exception.
    Conflicts between layers are reported explicitly, never silently absorbed.
    """

    PRECEDENCE = [
        "platform_invariants",
        "regulatory_minimums",
        "contractual_minimums",
        "organisation",
        "domain",
        "action_class",
        "temporary_exception",
    ]

    def resolve(
        self,
        profile: BaroWeightProfile,
        jurisdiction: Optional[str] = None,
        contractual_minimums: Optional[Dict[str, float]] = None,
        action_class: Optional[str] = None,
    ) -> Tuple[Dict[str, float], List[str]]:
        """Return (resolved_weights, reported_conflicts)."""
        conflicts: List[str] = []
        resolved: Dict[str, float] = dict(profile.weights)

        # Layer B — regulatory floor (jurisdiction-scoped if provided).
        for kind in PROTECTED_WEIGHTS:
            key = kind.value
            floor = profile.regulatory_minimums.get(
                key, REGULATORY_FLOOR
            )
            if resolved.get(key, 0.0) < floor:
                conflicts.append(
                    f"regulatory floor raised {key} {resolved.get(key, 0.0)} -> {floor}"
                )
                resolved[key] = floor

        # Layer B2 — contractual minimums (cannot lower a regulatory floor).
        if contractual_minimums:
            for key, val in contractual_minimums.items():
                if resolved.get(key, 0.0) < val:
                    conflicts.append(
                        f"contractual minimum raised {key} -> {val}"
                    )
                    resolved[key] = val

        # Scope reporting (selection, not override) — surfaced for audit.
        if jurisdiction:
            conflicts.append(f"scope jurisdiction={jurisdiction}")
        if action_class:
            conflicts.append(f"scope action_class={action_class}")
        return resolved, conflicts


class SimulationReport(BaseModel):
    changed_decisions: List[str] = Field(default_factory=list)
    changed_risk_scores: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    new_step_ups: List[str] = Field(default_factory=list)
    new_denials: List[str] = Field(default_factory=list)
    reduced_controls: List[str] = Field(default_factory=list)
    invariant_conflicts: List[str] = Field(default_factory=list)
    regulatory_conflicts: List[str] = Field(default_factory=list)
    rejected: bool = False
    reject_reason: Optional[str] = None


def simulate(
    profile: BaroWeightProfile,
    cases: List[str],
    baseline_decide: Callable[[str], ExecutionDecision],
    profile_decide: Callable[[str, BaroWeightProfile], ExecutionDecision],
) -> SimulationReport:
    """Dry-run a candidate profile against historical/synthetic cases.

    Returns *what would change* — it never performs a real decision. A profile
    that weakens a mandatory control is rejected before any case is scored.
    """
    report = SimulationReport()

    if profile.is_expired():
        report.rejected = True
        report.reject_reason = "profile expired"
        return report

    ok, violations, conflicts = ThreeLayerControl().validate(profile)
    report.invariant_conflicts = violations
    report.regulatory_conflicts = conflicts
    if not ok:
        report.rejected = True
        report.reject_reason = "; ".join(violations + conflicts)
        return report

    for case in cases:
        base = baseline_decide(case)
        prof = profile_decide(case, profile)
        if base != prof:
            report.changed_decisions.append(case)
            if prof == ExecutionDecision.DENY and base != ExecutionDecision.DENY:
                report.new_denials.append(case)
            if prof == ExecutionDecision.STEP_UP and base != ExecutionDecision.STEP_UP:
                report.new_step_ups.append(case)
            # More permissive than baseline == reduced control.
            _permissive = {
                ExecutionDecision.ALLOW,
                ExecutionDecision.MODIFY,
            }
            if prof in _permissive and base not in _permissive:
                report.reduced_controls.append(case)
    return report
