from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional


class Status(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class VerificationResult:
    status: Status
    gates: tuple[GateResult, ...]
    rationale: str
    claim: Mapping[str, Any]
    authority: Mapping[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "gates": [asdict(g) for g in self.gates],
            "rationale": self.rationale,
            "claim": dict(self.claim),
            "authority": dict(self.authority),
        }


def _eq(a: Any, b: Any) -> bool:
    return a == b


def _gate(name: str, ok: bool, reason: str) -> GateResult:
    return GateResult(name, ok, reason)


def verify_claim(
    claim: Any,
    authority: Any,
    *,
    required_fields: Iterable[str],
    scope_fields: Iterable[str] = (),
    constraint_fields: Iterable[str] = (),
    freshness_field: Optional[str] = None,
    verification_time: Optional[Any] = None,
) -> VerificationResult:
    """Deterministically classify a structured claim against authoritative state.

    This is VAIG-side evidence classification only. It never grants authority,
    clearance, permits, or execution permission.
    """
    req = tuple(required_fields)
    scope = tuple(scope_fields)
    constraints = tuple(constraint_fields)
    gates: list[GateResult] = []

    claim_is_mapping = isinstance(claim, Mapping)
    authority_is_mapping = isinstance(authority, Mapping)
    claim_snapshot = dict(claim) if claim_is_mapping else {}
    authority_snapshot = dict(authority) if authority_is_mapping else {}

    structured = claim_is_mapping and bool(claim_snapshot)
    gates.append(_gate("G1_CLAIM_EXPLICIT", structured, "claim is structured" if structured else "claim missing/unstructured"))
    if not structured:
        return VerificationResult(Status.UNKNOWN, tuple(gates), "Claim is not explicit structured data.", claim_snapshot, authority_snapshot)

    missing_claim = [field for field in req if field not in claim_snapshot]
    gates.append(_gate("G2_SCHEMA_FIT", not missing_claim, "all required claim fields present" if not missing_claim else f"missing claim fields: {missing_claim}"))
    if missing_claim:
        return VerificationResult(Status.UNKNOWN, tuple(gates), "Claim schema cannot represent all required predicates.", claim_snapshot, authority_snapshot)

    source_exists = authority_is_mapping and bool(authority_snapshot)
    gates.append(_gate("G3_SOURCE_EXISTS", source_exists, "authority source present" if source_exists else "authority source missing"))
    if not source_exists:
        return VerificationResult(Status.UNKNOWN, tuple(gates), "No authoritative source state available.", claim_snapshot, authority_snapshot)

    missing_auth = [field for field in req if field not in authority_snapshot]
    gates.append(_gate("G4_SOURCE_AUTHORITY", not missing_auth, "authoritative predicates available" if not missing_auth else f"authority missing fields: {missing_auth}"))
    if missing_auth:
        return VerificationResult(Status.UNKNOWN, tuple(gates), "Authoritative source lacks required predicates.", claim_snapshot, authority_snapshot)

    scope_missing = [field for field in scope if field not in claim_snapshot or field not in authority_snapshot]
    if scope_missing:
        gates.append(_gate("G5_SCOPE", False, f"scope fields missing: {scope_missing}"))
        return VerificationResult(Status.UNKNOWN, tuple(gates), "Scope cannot be established.", claim_snapshot, authority_snapshot)

    scope_mismatch = [field for field in scope if not _eq(claim_snapshot[field], authority_snapshot[field])]
    gates.append(_gate("G5_SCOPE", not scope_mismatch, "scope matches" if not scope_mismatch else f"scope mismatch: {scope_mismatch}"))
    if scope_mismatch:
        return VerificationResult(Status.CONTRADICTED, tuple(gates), "Claim is outside authoritative scope.", claim_snapshot, authority_snapshot)

    if freshness_field:
        if freshness_field not in authority_snapshot or verification_time is None:
            gates.append(_gate("G6_FRESHNESS", False, "freshness cannot be established"))
            return VerificationResult(Status.UNKNOWN, tuple(gates), "Freshness cannot be established.", claim_snapshot, authority_snapshot)
        fresh = verification_time <= authority_snapshot[freshness_field]
        gates.append(_gate("G6_FRESHNESS", fresh, "authority state fresh" if fresh else "authority state expired/stale"))
        if not fresh:
            return VerificationResult(Status.CONTRADICTED, tuple(gates), "Authoritative state is stale or expired.", claim_snapshot, authority_snapshot)
    else:
        gates.append(_gate("G6_FRESHNESS", True, "freshness not required by this verification profile"))

    missing_constraints = [field for field in constraints if field not in claim_snapshot or field not in authority_snapshot]
    gates.append(_gate("G7_CONSTRAINT_COMPLETENESS", not missing_constraints, "constraints represented" if not missing_constraints else f"missing constraints: {missing_constraints}"))
    if missing_constraints:
        return VerificationResult(Status.UNKNOWN, tuple(gates), "Constraint completeness cannot be established.", claim_snapshot, authority_snapshot)

    constraint_mismatch = [field for field in constraints if not _eq(claim_snapshot[field], authority_snapshot[field])]
    if constraint_mismatch:
        return VerificationResult(Status.CONTRADICTED, tuple(gates), f"Constraint mismatch: {constraint_mismatch}", claim_snapshot, authority_snapshot)

    mismatches = [field for field in req if not _eq(claim_snapshot[field], authority_snapshot[field])]
    gates.append(_gate("G8_DETERMINISTIC_COMPARABILITY", True, "exact structural comparison used"))
    gates.append(_gate("G9_NO_UNRESOLVED_CONTRADICTION", not mismatches, "no contradiction" if not mismatches else f"mismatch: {mismatches}"))
    if mismatches:
        return VerificationResult(Status.CONTRADICTED, tuple(gates), f"Authoritative contradiction on: {mismatches}", claim_snapshot, authority_snapshot)

    return VerificationResult(Status.SUPPORTED, tuple(gates), "All required binary gates passed and claim matches authoritative state.", claim_snapshot, authority_snapshot)


__all__ = ["GateResult", "Status", "VerificationResult", "verify_claim"]
