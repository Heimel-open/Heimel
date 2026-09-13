"""Deterministic binding for behavior-changing skill state.

A downstream Authority State may bind the returned execution_assumption_id.
A missing or mismatched binding means the prior execution assumption is stale
and must be re-evaluated before a consequence-bearing action.

A matching binding is necessary only. It never grants authority, proves policy
freshness, or replaces fresh state + reht evaluation.
"""

from __future__ import annotations

from .manifest import SkillManifestV1, content_hash


def execution_assumption_id(manifest: SkillManifestV1) -> str:
    """Fingerprint fields that can change available behavior or reach."""
    risk_class = getattr(manifest.risk_class, "value", str(manifest.risk_class))
    payload = {
        "skill_id": manifest.skill_id,
        "version": manifest.version,
        "content_hash": manifest.content_hash,
        "model_id": manifest.model_id,
        "training_or_derivation_context": manifest.training_or_derivation_context,
        "tool_requirements": sorted(str(v) for v in manifest.tool_requirements),
        "input_schema": manifest.input_schema,
        "output_schema": manifest.output_schema,
        "declared_scope": sorted(str(v) for v in manifest.declared_scope),
        "known_exclusions": sorted(str(v) for v in manifest.known_exclusions),
        "risk_class": risk_class,
    }
    return content_hash(payload)


def requires_authority_reevaluation(
    manifest: SkillManifestV1,
    bound_execution_assumption_id: str | None,
) -> bool:
    """Fail stale when capability state is unbound or has changed.

    False means only that this capability-state binding still matches. It does
    not imply ALLOW and does not waive any other freshness or authorization
    requirement.
    """
    if not bound_execution_assumption_id:
        return True
    return bound_execution_assumption_id != execution_assumption_id(manifest)


__all__ = ["execution_assumption_id", "requires_authority_reevaluation"]
