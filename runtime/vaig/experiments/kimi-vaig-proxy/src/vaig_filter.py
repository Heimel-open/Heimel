from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GovernanceResult:
    decision: str
    mode: str
    llm_allowed: bool
    output_scope: str
    reason: str
    primary_failure: str
    secondary_failures: list[str]
    autonomous_recommendation_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_case(case: dict[str, Any]) -> GovernanceResult:
    """Small redacted VAIG-style pre-generation rule set.

    This is only an experiment harness, not the full VALO/VAIG runtime.
    """

    severity = case.get("consequence_severity", "unknown")
    evidence = case.get("evidence_condition", "unknown")
    reversibility = case.get("reversibility", "unknown")
    time_pressure = case.get("time_pressure", "unknown")
    human_required = bool(case.get("human_authority_required", False))
    domain = case.get("domain", "unknown")

    if severity == "critical" and evidence != "validated":
        return GovernanceResult(
            decision="STEP_UP",
            mode="SAFE_MODE",
            llm_allowed=True,
            output_scope=(
                "uncertainty inventory; blocked options; limited reversible measures; "
                "escalation only; no autonomous action selection"
            ),
            reason="Critical case with non-validated evidence. Autonomous action selection is blocked.",
            primary_failure=_primary_failure_for(domain, evidence),
            secondary_failures=[
                f"evidence_condition={evidence}",
                f"reversibility={reversibility}",
                f"time_pressure={time_pressure}",
                "consequence_severity=critical",
            ],
            autonomous_recommendation_allowed=False,
        )

    if human_required:
        return GovernanceResult(
            decision="STEP_UP",
            mode="SAFE_MODE",
            llm_allowed=True,
            output_scope="escalation summary only; no autonomous action selection",
            reason="Human authority is required by case metadata.",
            primary_failure="authority requirement",
            secondary_failures=["human_authority_required=true"],
            autonomous_recommendation_allowed=False,
        )

    return GovernanceResult(
        decision="ALLOW",
        mode="NORMAL",
        llm_allowed=True,
        output_scope="normal response allowed",
        reason="Evidence and consequence conditions allow normal generation.",
        primary_failure="none",
        secondary_failures=[],
        autonomous_recommendation_allowed=True,
    )


def _primary_failure_for(domain: str, evidence: str) -> str:
    if domain == "emergency_management":
        return "predictive incoherence"
    if domain == "chemical_plant_safety":
        return "causal incoherence"
    if evidence == "insufficient":
        return "insufficient evidence"
    if evidence == "contested":
        return "contested evidence"
    return "admissibility failure"
