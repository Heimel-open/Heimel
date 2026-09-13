from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gate import GateDecision, GateEvent, RiskClass


_LARGE_CONTEXT_TOKENS = 32_000
_HIGH_TOKEN_ESTIMATE = 10_000
_LOW_VALUE_CONFIDENCE = 0.3
_HIGH_HUMAN_TIME_MINUTES = 30.0

AUTHORITY_ORDER = {
    "none": 0,
    "read": 1,
    "write": 2,
    "send": 3,
    "execute": 4,
    "delete": 5,
}

RISK_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


def classify_event(event: "GateEvent") -> "GateDecision":
    from .gate import GateDecision

    checks: list[str] = []

    checks.append("authority_scope")
    tool_auth = AUTHORITY_ORDER.get(event.tool_authority)
    task_auth = AUTHORITY_ORDER.get(event.task_authority)
    # Fail closed: an unknown authority level is treated as maximal risk and denied.
    if tool_auth is None or task_auth is None:
        return GateDecision(
            decision="deny",
            reason="unknown authority level (fail-closed)",
            risk_class=max_risk(event.domain_risk, "high"),
            checks_run=checks,
        )
    if tool_auth > task_auth:
        return GateDecision(
            decision="deny",
            reason="tool authority exceeds task authority",
            risk_class=max_risk(event.domain_risk, "high"),
            checks_run=checks,
        )

    checks.append("critical_domain")
    if event.domain_risk == "critical":
        return GateDecision(
            decision="require_human",
            reason="critical domain requires human review",
            risk_class="critical",
            checks_run=checks,
        )

    checks.append("irreversible_action")
    if event.reversibility == "irreversible":
        return GateDecision(
            decision="slow_path",
            reason="irreversible action cannot use fast path",
            risk_class=max_risk(event.domain_risk, "high"),
            checks_run=checks,
        )

    checks.append("external_effect_authority")
    if event.tool_authority in {"write", "send", "execute", "delete"}:
        return GateDecision(
            decision="slow_path",
            reason="external-effect tool authority requires slow path",
            risk_class=max_risk(event.domain_risk, "medium"),
            checks_run=checks,
        )

    checks.append("drift_threshold")
    if event.drift_score >= 0.70:
        return GateDecision(
            decision="halt",
            reason="semantic drift exceeds execution boundary",
            risk_class=max_risk(event.domain_risk, "high"),
            checks_run=checks,
        )
    if event.drift_score >= 0.40:
        return GateDecision(
            decision="slow_path",
            reason="semantic drift requires re-grounding",
            risk_class=max_risk(event.domain_risk, "medium"),
            checks_run=checks,
        )

    checks.append("uncertainty_threshold")
    if event.uncertainty >= 0.80:
        return GateDecision(
            decision="require_human",
            reason="uncertainty is too high for autonomous execution",
            risk_class=max_risk(event.domain_risk, "high"),
            checks_run=checks,
        )
    if event.uncertainty >= 0.50:
        return GateDecision(
            decision="slow_path",
            reason="uncertainty requires deeper verification",
            risk_class=max_risk(event.domain_risk, "medium"),
            checks_run=checks,
        )

    checks.append("observation_trust")
    if event.event_type == "observation" and event.observation_trust < 0.50:
        return GateDecision(
            decision="slow_path",
            reason="low-trust observation cannot become semantic ground",
            risk_class=max_risk(event.domain_risk, "medium"),
            checks_run=checks,
        )

    checks.append("claim_substantiation")
    if not event.claims_substantiated and event.domain_risk in {"medium", "high"}:
        return GateDecision(
            decision="slow_path",
            reason="claims require substantiation before consequential use",
            risk_class=max_risk(event.domain_risk, "medium"),
            checks_run=checks,
        )

    checks.append("cost_value_gate")
    if (event.human_time_minutes > _HIGH_HUMAN_TIME_MINUTES
            and event.expected_value == "low"):
        return GateDecision(
            decision="deny_cost",
            reason="high human-time burden with low expected value; action not worth executing",
            risk_class=event.domain_risk,
            checks_run=checks,
        )
    if event.expected_value == "low" and event.model_tier == "frontier":
        return GateDecision(
            decision="downshift_model",
            reason="low-value task does not justify frontier model; downshift to smaller tier",
            risk_class=event.domain_risk,
            checks_run=checks,
        )
    if event.expected_value == "low" and event.context_tokens > _LARGE_CONTEXT_TOKENS:
        return GateDecision(
            decision="reduce_context",
            reason="low-value task with oversized context; reduce before execution",
            risk_class=event.domain_risk,
            checks_run=checks,
        )
    if (event.estimated_tokens > _HIGH_TOKEN_ESTIMATE
            and event.value_confidence < _LOW_VALUE_CONFIDENCE):
        return GateDecision(
            decision="require_value_justification",
            reason="high token estimate with low value confidence; justify before spending",
            risk_class=event.domain_risk,
            checks_run=checks,
        )

    checks.append("fast_path_eligibility")
    if (
        event.tool_authority in {"none", "read"}
        and event.reversibility == "reversible"
        and event.domain_risk == "low"
        and event.uncertainty < 0.20
        and event.drift_score < 0.20
    ):
        return GateDecision(
            decision="allow_fast",
            reason="low-risk reversible step eligible for fast path",
            risk_class="low",
            checks_run=checks,
            receipt_required=False,
        )

    return GateDecision(
        decision="allow",
        reason="step is admissible under deterministic MVP rules",
        risk_class=event.domain_risk,
        checks_run=checks,
    )


def max_risk(a: "RiskClass", b: "RiskClass") -> "RiskClass":
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b
