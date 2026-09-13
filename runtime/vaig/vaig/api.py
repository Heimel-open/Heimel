"""VAIG evaluation and integrity API.

VAIG evaluates evidence, risk and model/runtime signals. It does not grant
execution authority. The historical ``/api/v1/authorize`` route is retained as
a deprecated compatibility surface, but its AARM result is an evaluation only.
Every response states that REHT clearance is required before any consequential
execution.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

from fastapi import FastAPI, status, Body
from fastapi.middleware.cors import CORSMiddleware

from vaig.aarm import aarm_explain, verdict_from_evidence
from vaig.digest import canonical_digest
from vaig.rrp.evidence import (
    ConfidenceLevel,
    EvidenceCondition,
    EvidenceSource,
    ValidationMethod,
    ValidationStatus,
)
from vaig.worm import WORMLog


def _utcnow() -> datetime:
    """Return naive UTC for compatibility with the existing API schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


logger = logging.getLogger(__name__)


def _load_worm() -> WORMLog:
    """Build a WORMLog from VAIG_WORM_LOG/VAIG_WORM_KEY, or the default log."""
    key = os.environ.get("VAIG_WORM_KEY")
    return WORMLog(
        os.environ.get("VAIG_WORM_LOG", "vaig_audit.jsonl"),
        encryption_key=key.encode("utf-8") if key else None,
    )


app = FastAPI(
    title="VAIG Evaluation & Integrity API",
    description=(
        "Evidence validation, risk evaluation and audit signals. "
        "VAIG never grants execution authority; REHT clearance is required."
    ),
    version="1.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "VAIG_CORS_ORIGINS", "http://127.0.0.1,http://localhost"
    ).split(",")
    if origin.strip()
]
_cors_allow_origins = _CORS_ORIGINS or ["http://127.0.0.1"]
_cors_allow_credentials = "*" not in _cors_allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


tags_metadata = [
    {
        "name": "Evaluation",
        "description": (
            "AARM compatibility recommendations. ALLOW is not execution authority; "
            "REHT clearance remains mandatory."
        ),
    },
    {
        "name": "Evidence",
        "description": "Evidence condition validation and gating",
    },
    {
        "name": "Risk Scoring",
        "description": "WHY Gate 4-dimension risk assessment",
    },
    {
        "name": "Audit",
        "description": "WORM audit logs and accountability",
    },
    {
        "name": "System",
        "description": "Health checks and system information",
    },
]

app.openapi_tags = tags_metadata


# ============================================================================
# Evaluation compatibility endpoints
# ============================================================================


@app.post(
    "/api/v1/authorize",
    tags=["Evaluation"],
    status_code=status.HTTP_200_OK,
    deprecated=True,
)
async def authorize(
    intent: str = Body(..., example="user:maria:write:secrets"),
    evidence: Dict[str, Any] = Body(..., example={"mfa_verified": True, "ip_whitelisted": True}),
    override_authority: Optional[str] = None,
):
    """Evaluate a proposed action using the legacy AARM vocabulary.

    This route is retained for compatibility only. ``decision`` is an alias for
    the AARM evaluation verdict. Even when it is ``ALLOW`` the response has no
    execution authority, no clearance and no permit. Consequential execution
    must cross REHT separately.
    """
    verdict, signal = verdict_from_evidence(evidence)
    evaluation = verdict.value
    reason = aarm_explain(verdict, signal)

    digest_source = {
        "intent": intent,
        "evaluation": evaluation,
        "reason": reason,
        "evidence": evidence,
        "execution_authority": False,
        "requires_reht_clearance": True,
    }
    worm_hash = hashlib.sha256(
        json.dumps(digest_source, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    evaluation_id = f"eval-{_utcnow().timestamp()}"

    return {
        "intent": intent,
        "evaluation": evaluation,
        # Compatibility alias. This is explicitly not an execution decision.
        "decision": evaluation,
        "reason": reason,
        "execution_authority": False,
        "requires_reht_clearance": True,
        "reht_clearance": None,
        "permit": None,
        "override_authority_accepted": False,
        "evidence_summary": {
            "conditions_validated": len(evidence),
            "conditions_failed": 0 if evaluation in ["ALLOW", "MODIFY"] else 1,
            "confidence": round(signal.observation_trust, 2),
        },
        "receipt": {
            "evaluation_id": evaluation_id,
            "decision_id": evaluation_id,
            "timestamp": _utcnow().isoformat(),
            "worm_hash": f"sha256:{worm_hash}",
            "previous_hash": "sha256:0000000000000000",
            "audit_chain_valid": True,
            "execution_authority": False,
        },
    }


@app.get(
    "/api/v1/authorization/{decision_id}",
    tags=["Evaluation"],
    status_code=status.HTTP_200_OK,
    deprecated=True,
)
async def get_authorization(decision_id: str):
    """Compatibility lookup response.

    The legacy implementation fabricated an ALLOW record. VAIG does not persist
    authoritative execution decisions, so this endpoint now reports that no
    execution authorization is stored here.
    """
    return {
        "decision_id": decision_id,
        "status": "NOT_STORED_BY_VAIG",
        "execution_authority": False,
        "requires_reht_clearance": True,
        "reht_clearance": None,
        "permit": None,
        "reason": (
            "VAIG stores evaluation/audit evidence only; execution authorization "
            "must be retrieved from the REHT authority boundary."
        ),
    }


# ============================================================================
# Evidence Validation Endpoints
# ============================================================================


@app.post(
    "/api/v1/evidence/validate",
    tags=["Evidence"],
    status_code=status.HTTP_200_OK,
)
async def validate_evidence(
    condition_type: str = Body(..., example="mfa_verified"),
    condition_value: Any = Body(None, example=True),
    freshness_boundary_seconds: Optional[int] = Body(
        None, example=60, ge=0
    ),
):
    """Validate a single evidence condition.

    The returned object is evidence only. It carries no execution authority.
    """
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    source = EvidenceSource(
        source_id=f"evidence:{condition_type}",
        source_type="direct_observation",
        provenance=f"condition:{condition_type}",
        raw_payload_digest=canonical_digest(
            {"type": condition_type, "value": condition_value}
        ),
        timestamp_acquired=now_utc,
        timestamp_submitted=now_utc,
    )

    if condition_value is None:
        state = ValidationStatus.INSUFFICIENT
        confidence = ConfidenceLevel.UNKNOWN
        reasoning = "No evidence value supplied for the condition."
    elif freshness_boundary_seconds is not None:
        state = ValidationStatus.STALE
        confidence = ConfidenceLevel.LOW
        reasoning = "Evidence value present but freshness not yet verified at validation time."
    else:
        state = ValidationStatus.VALIDATED
        confidence = ConfidenceLevel.HIGH
        reasoning = "Condition value bound to an admissible evidence source."

    condition = EvidenceCondition(
        evidence_id=f"evc-{condition_type}",
        created_at=now_utc,
        source_chain=[source],
        freshness_boundary_seconds=freshness_boundary_seconds,
        timestamp_validated=now_utc,
        timestamp_expires=None,
        validation_status=state.value,
        validator="rrp-evidence-v1",
        validation_method=ValidationMethod.DIRECT_VERIFICATION.value,
        validation_reasoning=reasoning,
        confidence_level=confidence.name,
        confidence_reasoning=reasoning,
        contested_by=None,
        contest_reasoning=None,
        bound_intents=[],
    )

    return {
        "condition_type": condition_type,
        "condition_value": condition_value,
        "validation_state": state.value.upper(),
        "confidence": confidence.value,
        "admissible": condition.is_admissible(),
        "fresh": condition.check_freshness(),
        "freshness_seconds": freshness_boundary_seconds,
        "validator": condition.validator,
        "payload_digest": source.raw_payload_digest,
        "timestamp": now_utc,
        "execution_authority": False,
    }


@app.get(
    "/api/v1/evidence/conditions",
    tags=["Evidence"],
    status_code=status.HTTP_200_OK,
)
async def list_evidence_conditions():
    """List all available evidence conditions for policy validation."""
    return {
        "conditions": [
            {
                "name": "mfa_verified",
                "type": "boolean",
                "freshness_ttl_seconds": 3600,
                "description": "Multi-factor authentication verified",
            },
            {
                "name": "ip_whitelisted",
                "type": "boolean",
                "freshness_ttl_seconds": 86400,
                "description": "Request from whitelisted IP",
            },
            {
                "name": "risk_score",
                "type": "float",
                "freshness_ttl_seconds": 300,
                "description": "Computed risk score 0.0-1.0",
            },
            {
                "name": "rate_limit_ok",
                "type": "boolean",
                "freshness_ttl_seconds": 60,
                "description": "Request within rate limits",
            },
            {
                "name": "audit_trail_complete",
                "type": "boolean",
                "freshness_ttl_seconds": 1,
                "description": "All prior decisions logged",
            },
        ],
        "total": 5,
        "execution_authority": False,
    }


# ============================================================================
# Risk Scoring (WHY Gate v2)
# ============================================================================


@app.post(
    "/api/v1/risk/score",
    tags=["Risk Scoring"],
    status_code=status.HTTP_200_OK,
)
async def score_risk(
    authority: float = Body(..., ge=0, le=1, example=0.95),
    policy: float = Body(..., ge=0, le=1, example=0.98),
    reality: float = Body(..., ge=0, le=1, example=0.92),
    consequence: float = Body(..., ge=0, le=1, example=0.89),
):
    """Score four evaluation dimensions; this does not authorize execution."""
    combined_score = min(authority, policy, reality, consequence)

    if combined_score >= 0.95:
        distrust_level = "L0_TRUSTED"
        max_spread = 5.0
    elif combined_score >= 0.80:
        distrust_level = "L1_MONITOR"
        max_spread = 4.0
    elif combined_score >= 0.60:
        distrust_level = "L2_CAUTION"
        max_spread = 3.0
    elif combined_score >= 0.40:
        distrust_level = "L3_SUSPICIOUS"
        max_spread = 2.0
    else:
        distrust_level = "L4_UNTRUSTED"
        max_spread = -1.0

    return {
        "dimensions": {
            "authority": authority,
            "policy": policy,
            "reality": reality,
            "consequence": consequence,
        },
        "combined_score": combined_score,
        "distrust_level": distrust_level,
        "max_spread": max_spread,
        "confidence_floor": 0.05 if combined_score >= 0.95 else 1.01,
        "timestamp": _utcnow().isoformat(),
        "execution_authority": False,
    }


# ============================================================================
# Audit & Accountability
# ============================================================================


@app.get(
    "/api/v1/audit/log",
    tags=["Audit"],
    status_code=status.HTTP_200_OK,
)
async def get_audit_log(
    limit: int = 50,
    subject_id: Optional[str] = None,
):
    """Get the real WORM audit log, never fabricated entries."""
    worm = _load_worm()
    if not worm.path.exists():
        return {
            "entries": [],
            "count": 0,
            "chain_integrity": "no_entries",
            "verified_through_entry": None,
            "timestamp": _utcnow().isoformat(),
        }

    entries = [
        {
            "sequence": i,
            "entry_id": entry.get("id"),
            "timestamp": entry.get("ts"),
            "hash": entry.get("hash"),
            "previous_hash": entry.get("prev"),
        }
        for i, entry in enumerate(worm.read_all())
        if subject_id is None or entry.get("id") == subject_id
    ][-limit:]

    return {
        "entries": entries,
        "count": len(entries),
        "chain_integrity": "verified" if worm.verify() else "violation",
        "verified_through_entry": len(entries) or None,
        "timestamp": _utcnow().isoformat(),
    }


@app.get(
    "/api/v1/audit/verify-chain",
    tags=["Audit"],
    status_code=status.HTTP_200_OK,
)
async def verify_audit_chain():
    """Verify the integrity of the entire WORM audit chain."""
    worm = _load_worm()
    if not worm.path.exists():
        return {
            "chain_status": "no_entries",
            "total_entries": 0,
            "integrity_violations": 0,
            "verified_through_entry": None,
            "verification_timestamp": _utcnow().isoformat(),
        }

    total = len(worm.read_all())
    valid = worm.verify()
    return {
        "chain_status": "verified" if valid else "violation",
        "total_entries": total,
        "integrity_violations": 0 if valid else 1,
        "verified_through_entry": total,
        "verification_timestamp": _utcnow().isoformat(),
    }
