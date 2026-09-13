from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .contracts import canonical_digest


class LLMOpsArtifactKind(str, Enum):
    PROMPT = "PROMPT"
    MODEL = "MODEL"
    EVAL_DATASET = "EVAL_DATASET"
    SERVING_CONFIG = "SERVING_CONFIG"
    RETRIEVAL_CONFIG = "RETRIEVAL_CONFIG"


class LLMOpsReadiness(str, Enum):
    READY = "READY"
    DEFER = "DEFER"


class VersionedArtifactBinding(BaseModel):
    kind: LLMOpsArtifactKind
    artifact_ref: str
    version: str
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner: str
    approved_eval_ref: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_binding(self) -> VersionedArtifactBinding:
        if not self.artifact_ref or not self.version or not self.owner:
            raise ValueError("versioned artifact binding requires ref, version and owner")
        return self


class ServingTestControls(BaseModel):
    bounded_concurrency: bool = False
    load_test_multiplier: int = Field(default=1, ge=1)
    shadow_testing: bool = False
    canary_rollout: bool = False
    canary_stages_percent: tuple[int, ...] = ()
    ab_testing: bool = False
    per_tenant_rate_limits: bool = False
    separate_interactive_batch_queues: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("canary_stages_percent")
    @classmethod
    def validate_canary_stages(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(stage < 1 or stage > 100 for stage in value):
            raise ValueError("canary stages must be percentages from 1 to 100")
        if value and (tuple(sorted(set(value))) != value or value[-1] != 100):
            raise ValueError("canary stages must be unique, increasing and end at 100")
        return value


class EvaluationDriftControls(BaseModel):
    offline_regression_suite_ref: str | None = None
    offline_regression_suite_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    online_evaluation: bool = False
    production_sampling_fraction: float = Field(default=0.0, ge=0.0, le=1.0)
    user_signal_capture: bool = False
    drift_detection: bool = False
    golden_evaluation_schedule_ref: str | None = None
    production_failures_feed_offline_suite: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_eval_binding(self) -> EvaluationDriftControls:
        if bool(self.offline_regression_suite_ref) != bool(
            self.offline_regression_suite_digest
        ):
            raise ValueError("offline regression suite ref and digest must be bound")
        if self.online_evaluation and self.production_sampling_fraction <= 0:
            raise ValueError("online evaluation requires a positive sampling fraction")
        return self


class ResourceControls(BaseModel):
    cost_attribution: bool = False
    hard_budget_caps: bool = False
    spend_velocity_alerting: bool = False
    context_token_monitoring: bool = False
    max_context_tokens: int | None = Field(default=None, ge=1)
    context_pruning_or_compression: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class TraceControls(BaseModel):
    end_to_end_trace: bool = False
    request_trace_id: bool = False
    record_prompt_version: bool = False
    record_model_version: bool = False
    record_retrieval_refs: bool = False
    record_tool_calls: bool = False
    record_token_counts: bool = False
    deterministic_boundary_correlation: bool = False
    token_by_token_replay_claimed: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class LLMOpsSubstrateProfile(BaseModel):
    schema_version: Literal["llmops_substrate.v1"] = "llmops_substrate.v1"
    profile_id: str
    tenant_id: str
    artifacts: tuple[VersionedArtifactBinding, ...]
    serving_test: ServingTestControls
    evaluation_drift: EvaluationDriftControls
    resources: ResourceControls
    tracing: TraceControls
    profile_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"profile_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_profile(self) -> LLMOpsSubstrateProfile:
        if not self.profile_id or not self.tenant_id:
            raise ValueError("LLMOps substrate profile requires profile and tenant identity")
        identities = [(item.kind, item.artifact_ref) for item in self.artifacts]
        if len(set(identities)) != len(identities):
            raise ValueError("LLMOps artifact bindings must be unique")
        if self.profile_digest and self.profile_digest != self.computed_digest:
            raise ValueError("LLMOps substrate profile digest mismatch")
        return self


class GovernedWorkspaceLLMOpsBinding(BaseModel):
    schema_version: Literal["governed_workspace_llmops_binding.v1"] = (
        "governed_workspace_llmops_binding.v1"
    )
    workspace_id: str
    workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_id: str
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    binding_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"binding_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_binding(self) -> GovernedWorkspaceLLMOpsBinding:
        if not self.workspace_id or not self.profile_id:
            raise ValueError("workspace LLMOps binding requires workspace and profile ids")
        if self.binding_digest and self.binding_digest != self.computed_digest:
            raise ValueError("workspace LLMOps binding digest mismatch")
        return self


class LLMOpsSubstrateAssessment(BaseModel):
    profile_id: str
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    readiness: LLMOpsReadiness
    gaps: tuple[str, ...] = ()
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


def seal_llmops_substrate_profile(
    profile: LLMOpsSubstrateProfile,
) -> LLMOpsSubstrateProfile:
    return profile.model_copy(update={"profile_digest": profile.computed_digest})


def bind_llmops_substrate_to_workspace(
    workspace_id: str,
    workspace_digest: str,
    profile: LLMOpsSubstrateProfile,
) -> GovernedWorkspaceLLMOpsBinding:
    binding = GovernedWorkspaceLLMOpsBinding(
        workspace_id=workspace_id,
        workspace_digest=workspace_digest,
        profile_id=profile.profile_id,
        profile_digest=profile.computed_digest,
    )
    return binding.model_copy(update={"binding_digest": binding.computed_digest})


def verify_llmops_substrate_binding(
    binding: GovernedWorkspaceLLMOpsBinding,
    workspace_id: str,
    workspace_digest: str,
    profile: LLMOpsSubstrateProfile,
) -> None:
    if binding.workspace_id != workspace_id:
        raise ValueError("workspace LLMOps binding workspace id mismatch")
    if binding.workspace_digest != workspace_digest:
        raise ValueError("workspace LLMOps binding workspace digest mismatch")
    if binding.profile_id != profile.profile_id:
        raise ValueError("workspace LLMOps binding profile id mismatch")
    if binding.profile_digest != profile.computed_digest:
        raise ValueError("workspace LLMOps binding profile digest mismatch")
    if binding.binding_digest != binding.computed_digest:
        raise ValueError("workspace LLMOps binding digest mismatch")


def assess_llmops_substrate(
    profile: LLMOpsSubstrateProfile,
) -> LLMOpsSubstrateAssessment:
    gaps: list[str] = []
    artifact_kinds = {item.kind for item in profile.artifacts}
    required_artifacts = {
        LLMOpsArtifactKind.PROMPT,
        LLMOpsArtifactKind.MODEL,
        LLMOpsArtifactKind.EVAL_DATASET,
    }
    for kind in sorted(required_artifacts - artifact_kinds, key=lambda item: item.value):
        gaps.append(f"missing_versioned_artifact:{kind.value}")

    serving = profile.serving_test
    if not serving.bounded_concurrency:
        gaps.append("serving:bounded_concurrency")
    if serving.load_test_multiplier < 10:
        gaps.append("serving:load_test_below_10x")
    if not serving.shadow_testing:
        gaps.append("serving:shadow_testing")
    if not serving.canary_rollout or not serving.canary_stages_percent:
        gaps.append("serving:canary_rollout")
    if not serving.ab_testing:
        gaps.append("serving:ab_testing")
    if not serving.per_tenant_rate_limits:
        gaps.append("serving:per_tenant_rate_limits")
    if not serving.separate_interactive_batch_queues:
        gaps.append("serving:queue_isolation")

    evaluation = profile.evaluation_drift
    if not evaluation.offline_regression_suite_ref:
        gaps.append("evaluation:offline_regression_suite")
    if not evaluation.online_evaluation:
        gaps.append("evaluation:online_evaluation")
    if not evaluation.user_signal_capture:
        gaps.append("evaluation:user_signal_capture")
    if not evaluation.drift_detection:
        gaps.append("evaluation:drift_detection")
    if not evaluation.golden_evaluation_schedule_ref:
        gaps.append("evaluation:golden_schedule")
    if not evaluation.production_failures_feed_offline_suite:
        gaps.append("evaluation:production_failure_feedback")

    resources = profile.resources
    if not resources.cost_attribution:
        gaps.append("resources:cost_attribution")
    if not resources.hard_budget_caps:
        gaps.append("resources:hard_budget_caps")
    if not resources.spend_velocity_alerting:
        gaps.append("resources:spend_velocity_alerting")
    if not resources.context_token_monitoring:
        gaps.append("resources:context_token_monitoring")
    if resources.max_context_tokens is None:
        gaps.append("resources:max_context_tokens")
    if not resources.context_pruning_or_compression:
        gaps.append("resources:context_pruning_or_compression")

    tracing = profile.tracing
    trace_requirements = {
        "end_to_end_trace": tracing.end_to_end_trace,
        "request_trace_id": tracing.request_trace_id,
        "record_prompt_version": tracing.record_prompt_version,
        "record_model_version": tracing.record_model_version,
        "record_retrieval_refs": tracing.record_retrieval_refs,
        "record_tool_calls": tracing.record_tool_calls,
        "record_token_counts": tracing.record_token_counts,
        "deterministic_boundary_correlation": tracing.deterministic_boundary_correlation,
    }
    for requirement, present in trace_requirements.items():
        if not present:
            gaps.append(f"tracing:{requirement}")

    ordered_gaps = tuple(sorted(gaps))
    return LLMOpsSubstrateAssessment(
        profile_id=profile.profile_id,
        profile_digest=profile.computed_digest,
        readiness=LLMOpsReadiness.READY if not ordered_gaps else LLMOpsReadiness.DEFER,
        gaps=ordered_gaps,
    )
