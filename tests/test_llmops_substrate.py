# ruff: noqa: I001
from __future__ import annotations

import pydantic
import pytest

import valo_kernel.llmops_substrate as ls


D64 = "a" * 64
E64 = "b" * 64
F64 = "c" * 64


def artifact(
    kind: ls.LLMOpsArtifactKind,
    ref: str,
    digest: str,
) -> ls.VersionedArtifactBinding:
    return ls.VersionedArtifactBinding(
        kind=kind,
        artifact_ref=ref,
        version="v1",
        digest=digest,
        owner="platform",
        approved_eval_ref="eval:golden-v1",
    )


def ready_profile() -> ls.LLMOpsSubstrateProfile:
    return ls.LLMOpsSubstrateProfile(
        profile_id="llmops:workspace-default",
        tenant_id="tenant-a",
        artifacts=(
            artifact(ls.LLMOpsArtifactKind.PROMPT, "prompt:triage", D64),
            artifact(ls.LLMOpsArtifactKind.MODEL, "model:worker", E64),
            artifact(ls.LLMOpsArtifactKind.EVAL_DATASET, "dataset:golden", F64),
        ),
        serving_test=ls.ServingTestControls(
            bounded_concurrency=True,
            load_test_multiplier=10,
            shadow_testing=True,
            canary_rollout=True,
            canary_stages_percent=(1, 5, 25, 100),
            ab_testing=True,
            per_tenant_rate_limits=True,
            separate_interactive_batch_queues=True,
        ),
        evaluation_drift=ls.EvaluationDriftControls(
            offline_regression_suite_ref="eval:regression-v1",
            offline_regression_suite_digest=D64,
            online_evaluation=True,
            production_sampling_fraction=0.1,
            user_signal_capture=True,
            drift_detection=True,
            golden_evaluation_schedule_ref="schedule:golden-daily",
            production_failures_feed_offline_suite=True,
        ),
        resources=ls.ResourceControls(
            cost_attribution=True,
            hard_budget_caps=True,
            spend_velocity_alerting=True,
            context_token_monitoring=True,
            max_context_tokens=8000,
            context_pruning_or_compression=True,
        ),
        tracing=ls.TraceControls(
            end_to_end_trace=True,
            request_trace_id=True,
            record_prompt_version=True,
            record_model_version=True,
            record_retrieval_refs=True,
            record_tool_calls=True,
            record_token_counts=True,
            deterministic_boundary_correlation=True,
        ),
    )


def test_complete_profile_is_ready_without_creating_authority() -> None:
    profile = ls.seal_llmops_substrate_profile(ready_profile())
    assessment = ls.assess_llmops_substrate(profile)

    assert assessment.readiness == ls.LLMOpsReadiness.READY
    assert assessment.gaps == ()
    assert profile.authority_effect == "NO_AUTHORITY_CREATION"
    assert profile.can_issue_clearance is False
    assert profile.can_execute_external_effects is False
    assert assessment.can_issue_clearance is False


def test_missing_operational_controls_defer_instead_of_authorizing() -> None:
    profile = ready_profile().model_copy(
        update={
            "serving_test": ls.ServingTestControls(),
            "resources": ls.ResourceControls(),
        }
    )
    assessment = ls.assess_llmops_substrate(profile)

    assert assessment.readiness == ls.LLMOpsReadiness.DEFER
    assert "serving:shadow_testing" in assessment.gaps
    assert "resources:hard_budget_caps" in assessment.gaps


def test_missing_required_versioned_artifact_defers() -> None:
    profile = ready_profile().model_copy(
        update={"artifacts": ready_profile().artifacts[:2]}
    )
    assessment = ls.assess_llmops_substrate(profile)

    assert assessment.readiness == ls.LLMOpsReadiness.DEFER
    assert "missing_versioned_artifact:EVAL_DATASET" in assessment.gaps


def test_behavioral_binding_change_changes_profile_digest() -> None:
    first = ready_profile()
    changed_model = artifact(ls.LLMOpsArtifactKind.MODEL, "model:worker", "d" * 64)
    second = first.model_copy(
        update={"artifacts": (first.artifacts[0], changed_model, first.artifacts[2])}
    )

    assert first.computed_digest != second.computed_digest


def test_workspace_binding_rejects_stale_substrate_profile() -> None:
    profile = ready_profile()
    binding = ls.bind_llmops_substrate_to_workspace("workspace-1", D64, profile)
    changed_model = artifact(ls.LLMOpsArtifactKind.MODEL, "model:worker", "d" * 64)
    changed = profile.model_copy(
        update={"artifacts": (profile.artifacts[0], changed_model, profile.artifacts[2])}
    )

    with pytest.raises(ValueError, match="profile digest mismatch"):
        ls.verify_llmops_substrate_binding(binding, "workspace-1", D64, changed)


def test_workspace_binding_accepts_exact_current_profile() -> None:
    profile = ready_profile()
    binding = ls.bind_llmops_substrate_to_workspace("workspace-1", D64, profile)

    ls.verify_llmops_substrate_binding(binding, "workspace-1", D64, profile)
    assert binding.can_issue_clearance is False


def test_sealed_profile_rejects_digest_mismatch() -> None:
    sealed = ls.seal_llmops_substrate_profile(ready_profile())
    payload = sealed.model_dump()
    payload["profile_id"] = "llmops:changed"

    with pytest.raises(pydantic.ValidationError, match="profile digest mismatch"):
        ls.LLMOpsSubstrateProfile.model_validate(payload)


def test_duplicate_artifact_binding_fails_closed() -> None:
    profile = ready_profile()
    duplicate = profile.artifacts[0]

    with pytest.raises(pydantic.ValidationError, match="artifact bindings must be unique"):
        ls.LLMOpsSubstrateProfile(
            profile_id=profile.profile_id,
            tenant_id=profile.tenant_id,
            artifacts=profile.artifacts + (duplicate,),
            serving_test=profile.serving_test,
            evaluation_drift=profile.evaluation_drift,
            resources=profile.resources,
            tracing=profile.tracing,
        )


def test_canary_stages_must_be_increasing_and_end_at_full_rollout() -> None:
    with pytest.raises(pydantic.ValidationError, match="canary stages"):
        ls.ServingTestControls(
            canary_rollout=True,
            canary_stages_percent=(25, 5),
        )


def test_online_evaluation_requires_positive_sampling() -> None:
    with pytest.raises(pydantic.ValidationError, match="positive sampling fraction"):
        ls.EvaluationDriftControls(online_evaluation=True)
