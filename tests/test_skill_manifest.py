"""Tests for governed skill manifest V1 and invariants (#637)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from skills_registry import (
    SkillAdmissibilityEvaluator,
    SkillManifestError,
    SkillManifestV1,
    ValidationStatus,
)


def _now():
    return datetime.now(timezone.utc)


def _manifest(**overrides):
    kwargs = {
        "skill_id": "data-cleaning",
        "version": "1.0.0",
        "origin": "research-factory",
        "author_or_generator": "sage-eval",
        "model_id": "model-1",
        "declared_scope": ["csv-clean"],
        "evidence_refs": ["ev-1", "ev-2"],
        "validation_status": ValidationStatus.VALIDATED,
        "validated_at": _now(),
        "reviewer": "reviewer-1",
    }
    kwargs.update(overrides)
    return SkillManifestV1(**kwargs)


def test_manifest_requires_id_and_version():
    with pytest.raises(SkillManifestError):
        SkillManifestV1(skill_id="", version="1.0.0")


def test_invariant_skill_acquired_not_authority():
    """A skill being present never grants authority."""
    m = _manifest()
    assert m.is_acquired() is True
    assert m.admission_gate()[1] != "authority_granted"


def test_invariant_revoked_denied():
    m = _manifest(revocation_state="revoked")
    assert m.is_permitted() is False
    allowed, reason = m.admission_gate()
    assert allowed is False
    assert "revoked" in reason


def test_invariant_unknown_provenance_never_allow():
    m = _manifest(origin="", author_or_generator="")
    allowed, reason = m.admission_gate()
    assert allowed is False
    assert "provenance" in reason


def test_invariant_missing_evidence_never_allow():
    m = _manifest(evidence_refs=())
    allowed, reason = m.admission_gate()
    assert allowed is False
    assert "evidence" in reason


def test_invariant_past_success_not_current_admissibility():
    """Validated at t1 does not guarantee admissibility at t2 (REHT decides)."""
    m = _manifest(validation_status=ValidationStatus.VALIDATED, validated_at=_now())
    assert m.is_currently_validated() is True
    # The manifest explicitly does not assert t2-admissibility.
    assert m.admission_gate()[1] in ("advisory admit",)


def test_invariant_skill_update_requires_reevaluation():
    """A new version is a new manifest (no silent reuse of old validation)."""
    v1 = _manifest(version="1.0.0")
    v2 = _manifest(version="2.0.0")
    assert v1.content_hash != v2.content_hash


def test_advisory_evaluator_never_grants_authority():
    m = _manifest()
    result = SkillAdmissibilityEvaluator().evaluate(m)
    assert result["authority_granted"] is False
    assert result["capability_evolved"] is True


def test_content_hash_deterministic():
    a = _manifest()
    b = _manifest()
    assert a.content_hash == b.content_hash
    assert len(a.content_hash) == 64
