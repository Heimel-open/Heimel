from datetime import datetime, timezone

from skills_registry import (
    SkillManifestV1,
    ValidationStatus,
    execution_assumption_id,
    requires_authority_reevaluation,
)


def _manifest(**overrides):
    values = {
        "skill_id": "procurement",
        "version": "1.0.0",
        "origin": "skills-hub",
        "author_or_generator": "builder",
        "model_id": "model-a",
        "tool_requirements": ("catalog.read",),
        "declared_scope": ("quote",),
        "known_exclusions": ("purchase",),
        "risk_class": "medium",
        "evidence_refs": ("ev-1",),
        "validation_status": ValidationStatus.VALIDATED,
        "validated_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return SkillManifestV1(**values)


def test_matching_binding_does_not_require_capability_reevaluation():
    manifest = _manifest()
    bound = execution_assumption_id(manifest)
    assert requires_authority_reevaluation(manifest, bound) is False


def test_missing_binding_is_stale():
    assert requires_authority_reevaluation(_manifest(), None) is True


def test_tool_mutation_invalidates_old_binding():
    before = _manifest(tool_requirements=("catalog.read",))
    after = _manifest(tool_requirements=("catalog.read", "purchase.write"))
    bound = execution_assumption_id(before)
    assert execution_assumption_id(after) != bound
    assert requires_authority_reevaluation(after, bound) is True


def test_model_or_scope_mutation_invalidates_old_binding():
    before = _manifest(model_id="model-a", declared_scope=("quote",))
    bound = execution_assumption_id(before)

    model_changed = _manifest(model_id="model-b", declared_scope=("quote",))
    scope_changed = _manifest(model_id="model-a", declared_scope=("quote", "purchase"))

    assert requires_authority_reevaluation(model_changed, bound) is True
    assert requires_authority_reevaluation(scope_changed, bound) is True


def test_content_mutation_invalidates_old_binding():
    before = _manifest(content_hash="a" * 64)
    after = _manifest(content_hash="b" * 64)
    bound = execution_assumption_id(before)
    assert requires_authority_reevaluation(after, bound) is True
