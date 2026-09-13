import uuid
import datetime
from typing import Any


HALT_RULES = [
    {
        "id": "H01",
        "label": "Mass send to competitor or unverified list",
        "check": lambda r: r.get("recipient_count", 1) > 20 and r.get("recipient_type") in ("competitor", "unknown"),
    },
    {
        "id": "H02",
        "label": "Potential legal violation — GDPR or confidentiality",
        "check": lambda r: r.get("legal_risk") == "high",
    },
    {
        "id": "H03",
        "label": "Explicit halt flag",
        "check": lambda r: r.get("halt") is True,
    },
]

DENY_RULES = [
    {
        "id": "D01",
        "label": "Contains sensitive internal data",
        "check": lambda r: r.get("contains_sensitive_data") is True,
    },
    {
        "id": "D02",
        "label": "Recipient is wrong or unintended",
        "check": lambda r: r.get("wrong_recipient") is True,
    },
    {
        "id": "D03",
        "label": "Contains personal data without basis",
        "check": lambda r: r.get("contains_personal_data") is True and not r.get("gdpr_basis"),
    },
    {
        "id": "D04",
        "label": "Explicit policy violation",
        "check": lambda r: r.get("policy_violation") is True,
    },
]

STEP_UP_RULES = [
    {
        "id": "R01",
        "label": "Recipient domain unverified",
        "check": lambda r: r.get("recipient_domain_verified") is False,
    },
    {
        "id": "R02",
        "label": "Attachment content unreviewed",
        "check": lambda r: r.get("attachment_reviewed") is False,
    },
    {
        "id": "R03",
        "label": "Insufficient authority",
        "check": lambda r: r.get("authority_level") == "insufficient",
    },
    {
        "id": "R04",
        "label": "Uncertainty exceeds policy",
        "check": lambda r: r.get("uncertainty") == "exceeds_policy",
    },
    {
        "id": "R05",
        "label": "High consequence action",
        "check": lambda r: r.get("amount_risk") == "high",
    },
]

STEP_UP_THRESHOLD = 2


def _receipt_id() -> str:
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    short = str(uuid.uuid4())[:8]
    return f"valo_exec_{ts}_{short}"


def evaluate(request: dict[str, Any]) -> dict[str, Any]:
    halt_triggered = [r for r in HALT_RULES if r["check"](request)]
    if halt_triggered:
        reason = " + ".join(r["label"] for r in halt_triggered)
        return {
            "decision": "HALT",
            "reason": reason,
            "rules_triggered": [r["id"] for r in halt_triggered],
            "next_action": "escalate_immediately",
            "receipt_id": _receipt_id(),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }

    deny_triggered = [r for r in DENY_RULES if r["check"](request)]
    if deny_triggered:
        reason = " + ".join(r["label"] for r in deny_triggered)
        return {
            "decision": "DENY",
            "reason": reason,
            "rules_triggered": [r["id"] for r in deny_triggered],
            "next_action": "action_blocked",
            "receipt_id": _receipt_id(),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }

    step_up_triggered = [r for r in STEP_UP_RULES if r["check"](request)]
    if len(step_up_triggered) >= STEP_UP_THRESHOLD:
        reason = " + ".join(r["label"] for r in step_up_triggered)
        return {
            "decision": "STEP_UP",
            "reason": reason,
            "rules_triggered": [r["id"] for r in step_up_triggered],
            "next_action": "human_review_required",
            "receipt_id": _receipt_id(),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }

    return {
        "decision": "ALLOW",
        "reason": "Admissible — all checks passed",
        "rules_triggered": [],
        "next_action": "proceed",
        "receipt_id": _receipt_id(),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
