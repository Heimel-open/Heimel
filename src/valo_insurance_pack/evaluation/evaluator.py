from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ..contracts.assurance_profile import AssuranceProfileV1, FailureOutcome
from ..contracts.assurance_strength import (
    AssuranceCapability,
    resolve_capabilities,
    resolve_evidence_capabilities,
)
from ..contracts.evaluation import AssuranceResult, CommitAssuranceEvaluationV1
from ..contracts.source_evidence import (
    ChangedSinceStatus,
    RevocationVisibilityStatus,
    SourceAssuranceEvidenceV1,
)
from ..utils.crypto import sha256_digest, utcnow


def evaluate_commit_assurance(
    *,
    profile: AssuranceProfileV1,
    action: Any,
    source_evidences: Sequence[SourceAssuranceEvidenceV1]
    | Mapping[str, SourceAssuranceEvidenceV1],
    reht_clearance_ref: str | None = None,
    racs_decision_ref: str | None = None,
    now: datetime | None = None,
    evaluation_id: str | None = None,
) -> CommitAssuranceEvaluationV1:
    """Evaluate whether source evidence satisfies the carrier AssuranceProfile at commit-time.

    CRITICAL INVARIANT: The insurance layer can NEVER override REHT or RACS.
    Execution authority is exclusively governed by REHT/RACS.
    """
    now = now or utcnow()

    # Normalize action reference
    if isinstance(action, dict):
        action_type = action.get("action_type")
        action_ref = sha256_digest(action)
    elif hasattr(action, "model_dump"):
        action_type = getattr(action, "action_type", None)
        action_ref = sha256_digest(action.model_dump(mode="json"))
    elif hasattr(action, "digest"):
        action_type = getattr(action, "action_type", None)
        action_ref = action.digest
    elif isinstance(action, str):
        action_ref = action
        action_type = None
    else:
        action_ref = sha256_digest(str(action))
        action_type = None

    # Normalize source evidence mapping
    if isinstance(source_evidences, Mapping):
        evidence_map = dict(source_evidences)
    else:
        evidence_map = {}
        for ev in source_evidences:
            if isinstance(ev, dict):
                ev = SourceAssuranceEvidenceV1.model_validate(ev)
            if ev.source_id in evidence_map:
                raise ValueError(
                    f"duplicate source evidence for '{ev.source_id}': a source may "
                    "provide only one evidence record per evaluation"
                )
            evidence_map[ev.source_id] = ev

    unmet_requirements: list[str] = []

    # 1. Profile Effective Period
    if not profile.is_effective(now):
        unmet_requirements.append(
            f"profile_inactive: AssuranceProfile '{profile.profile_id}' (version {profile.profile_version}) "
            f"is not active at evaluation time"
        )

    # 2. Action Type Match (if discernible)
    if action_type is not None and action_type != profile.action_type:
        unmet_requirements.append(
            f"action_type_mismatch: profile requires action_type '{profile.action_type}', "
            f"received '{action_type}'"
        )

    # 3. Required Authoritative Sources (Fail-closed)
    for req_source in profile.required_authoritative_sources:
        evidence = evidence_map.get(req_source)
        if evidence is None:
            unmet_requirements.append(
                f"missing_required_source: required authoritative source '{req_source}' is absent"
            )
            continue

        # Check revocation status (Must be ACTIVE, UNKNOWN fails closed)
        if evidence.revocation_visibility != RevocationVisibilityStatus.ACTIVE:
            unmet_requirements.append(
                f"revoked_or_unverified_evidence: source '{req_source}' status is {evidence.revocation_visibility.value}"
            )

        # Check validity window
        if evidence.valid_until is not None and now >= evidence.valid_until:
            unmet_requirements.append(
                f"expired_evidence: source '{req_source}' validity expired at {evidence.valid_until.isoformat()}"
            )

        # Check freshness requirement
        max_age = profile.freshness_requirements.get(req_source)
        if max_age is not None and not evidence.is_fresh(now, max_age):
            age = (now - evidence.observed_at).total_seconds()
            unmet_requirements.append(
                f"stale_evidence: source '{req_source}' observed age ({age:.1f}s) "
                f"exceeds maximum allowed freshness of {max_age}s"
            )

        # Check changed_since status (Must be UNCHANGED, UNKNOWN/CHANGED fails closed)
        if evidence.changed_since_status != ChangedSinceStatus.UNCHANGED:
            unmet_requirements.append(
                f"evidence_drift_or_unconfirmed: source '{req_source}' continuity is {evidence.changed_since_status.value}"
            )

        # Check revocation visibility mode if required
        req_rev_mode = profile.revocation_visibility_requirements.get(req_source)
        if (
            req_rev_mode == "REALTIME_ACTIVE"
            and evidence.revocation_visibility != RevocationVisibilityStatus.ACTIVE
        ):
            unmet_requirements.append(
                f"unverified_revocation: source '{req_source}' lacks required real-time active revocation visibility"
            )

        # Check minimum assurance requirement (capability subsumption, never
        # a linear strength ranking; different mechanisms prove different
        # properties and may be combined).
        required_caps: frozenset[AssuranceCapability] | None = None
        explicit_caps = profile.required_capabilities_per_source.get(req_source)
        min_mechanism = profile.minimum_assurance_per_source.get(req_source)
        if explicit_caps:
            required_caps = frozenset(
                c if isinstance(c, AssuranceCapability) else AssuranceCapability(str(c))
                for c in explicit_caps
            )
        elif min_mechanism:
            resolved = resolve_capabilities(min_mechanism)
            if resolved:
                required_caps = resolved
            else:
                unmet_requirements.append(
                    f"unknown_assurance_requirement: source '{req_source}' declares "
                    f"minimum mechanism '{min_mechanism}' with no resolvable capabilities"
                )
        if required_caps:
            actual_caps = resolve_evidence_capabilities(evidence)
            if not required_caps <= actual_caps:
                unmet_requirements.append(
                    f"insufficient_assurance_capabilities: source '{req_source}' provides "
                    f"{sorted(c.value for c in actual_caps)}, required "
                    f"{sorted(c.value for c in required_caps)}"
                )

    # Compute result based on failure outcome
    if not unmet_requirements:
        assurance_result = AssuranceResult.SATISFIED
    else:
        match profile.failure_outcome:
            case FailureOutcome.STEP_UP:
                assurance_result = AssuranceResult.STEP_UP_REQUIRED
            case FailureOutcome.DEFER:
                assurance_result = AssuranceResult.DEFERRED
            case FailureOutcome.HALT:
                assurance_result = AssuranceResult.HALTED
            case FailureOutcome.DENY | _:
                assurance_result = AssuranceResult.UNMET

    evidence_refs = [
        ev.evidence_digest or ev.compute_digest() for ev in evidence_map.values()
    ]
    evidence_digests = {
        src_id: ev.evidence_digest or ev.compute_digest()
        for src_id, ev in evidence_map.items()
    }

    eval_kwargs: dict[str, Any] = {
        "action_ref": action_ref,
        "profile_ref": f"{profile.profile_id}:{profile.profile_version}:{profile.digest}",
        "evidence_refs": evidence_refs,
        "evidence_digests": evidence_digests,
        "assurance_result": assurance_result,
        "unmet_requirements": unmet_requirements,
        "evaluated_at": now,
        "reht_clearance_ref": reht_clearance_ref,
        "racs_decision_ref": racs_decision_ref,
        "consequence_class": profile.consequence_class.value,
    }
    if evaluation_id:
        eval_kwargs["evaluation_id"] = evaluation_id

    return CommitAssuranceEvaluationV1(**eval_kwargs)
