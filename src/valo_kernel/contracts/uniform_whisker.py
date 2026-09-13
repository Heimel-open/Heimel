from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from time import perf_counter_ns
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import canonical_digest, utcnow


class TransitionSurface(str, Enum):
    INPUT = "INPUT"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    STATE_READ = "STATE_READ"
    STATE_WRITE = "STATE_WRITE"
    MEMORY_WRITE = "MEMORY_WRITE"
    DELEGATION = "DELEGATION"
    ROUTING = "ROUTING"
    TOOL_REQUEST = "TOOL_REQUEST"
    EFFECT_COMMIT = "EFFECT_COMMIT"
    EFFECT_RESULT = "EFFECT_RESULT"
    EVIDENCE_ADMISSION = "EVIDENCE_ADMISSION"


class WhiskerMode(str, Enum):
    SHADOW = "SHADOW"
    ENFORCE = "ENFORCE"


class WhiskerDisposition(str, Enum):
    PASS = "PASS"
    OBSERVE = "OBSERVE"
    STEP_UP = "STEP_UP"
    BLOCK = "BLOCK"


class WhiskerCostClass(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    LOCAL_SEMANTIC = "LOCAL_SEMANTIC"
    CLASSIFIER = "CLASSIFIER"
    MODEL_JUDGE = "MODEL_JUDGE"

    @property
    def rank(self) -> int:
        return {
            WhiskerCostClass.DETERMINISTIC: 0,
            WhiskerCostClass.LOCAL_SEMANTIC: 1,
            WhiskerCostClass.CLASSIFIER: 2,
            WhiskerCostClass.MODEL_JUDGE: 3,
        }[self]


class GovernedUniform(BaseModel):
    """Portable governed context bound to one exact consequence proposal.

    The uniform carries and constrains context. It never creates authority and
    cannot issue execution clearance.
    """

    schema_version: Literal["governed_uniform.v1"] = "governed_uniform.v1"
    uniform_id: str
    tenant_id: str
    actor_id: str
    identity_ref: str
    capability: str
    target: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    state_ref: str
    authority_refs: tuple[str, ...]
    delegation_refs: tuple[str, ...] = ()
    purpose_ref: str | None = None
    constraint_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    permitted_effect_classes: tuple[str, ...] = ()
    consequence_ref: str | None = None
    issued_at: datetime
    valid_until: datetime
    revocation_epoch: int = Field(ge=0)
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_uniform(self) -> GovernedUniform:
        required = (
            self.uniform_id,
            self.tenant_id,
            self.actor_id,
            self.identity_ref,
            self.capability,
            self.target,
            self.state_ref,
        )
        if any(not item for item in required):
            raise ValueError("uniform identity and exact action context are required")
        if not self.authority_refs:
            raise ValueError("governed uniform requires at least one authority ref")
        if self.issued_at.utcoffset() is None or self.valid_until.utcoffset() is None:
            raise ValueError("uniform timestamps must be timezone-aware")
        if self.valid_until <= self.issued_at:
            raise ValueError("uniform valid_until must be after issued_at")
        return self

    @property
    def uniform_digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))

    def is_fresh(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        return self.issued_at <= moment < self.valid_until

    @property
    def can_authorize_execution(self) -> bool:
        return False


class TransitionObservation(BaseModel):
    schema_version: Literal["transition_observation.v1"] = (
        "transition_observation.v1"
    )
    transition_id: str
    surface: TransitionSurface
    actor_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    state_ref: str
    consequence_ref: str | None = None
    observed_at: datetime
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_observation(self) -> TransitionObservation:
        if not self.transition_id or not self.actor_id or not self.state_ref:
            raise ValueError("transition identity and state binding are required")
        if self.observed_at.utcoffset() is None:
            raise ValueError("transition observed_at must be timezone-aware")
        return self

    @property
    def transition_digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class WhiskerAssessment(BaseModel):
    disposition: WhiskerDisposition
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def require_reason(self) -> WhiskerAssessment:
        if not self.reason_codes:
            raise ValueError("whisker assessment requires at least one reason code")
        return self


class WhiskerResult(BaseModel):
    schema_version: Literal["whisker_result.v1"] = "whisker_result.v1"
    whisker_id: str
    surface: TransitionSurface
    mode: WhiskerMode
    cost_class: WhiskerCostClass
    disposition: WhiskerDisposition
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    uniform_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    transition_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluated_at: datetime
    duration_ns: int = Field(ge=0)
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def is_binding_terminal(self) -> bool:
        return self.mode == WhiskerMode.ENFORCE and self.disposition in {
            WhiskerDisposition.BLOCK,
            WhiskerDisposition.STEP_UP,
        }

    @property
    def can_authorize_execution(self) -> bool:
        return False


class WhiskerProbe(Protocol):
    whisker_id: str
    surfaces: frozenset[TransitionSurface]
    mode: WhiskerMode
    cost_class: WhiskerCostClass
    priority: int

    def evaluate(
        self,
        uniform: GovernedUniform,
        observation: TransitionObservation,
        *,
        moment: datetime,
    ) -> WhiskerResult: ...


WhiskerEvaluator = Callable[
    [GovernedUniform, TransitionObservation, datetime], WhiskerAssessment
]


@dataclass(frozen=True)
class CallableWhisker:
    """Adapter that lets existing deterministic or probabilistic checks plug
    into the common whisker result contract without moving their semantics.
    """

    whisker_id: str
    surfaces: frozenset[TransitionSurface]
    evaluator: WhiskerEvaluator
    mode: WhiskerMode = WhiskerMode.ENFORCE
    cost_class: WhiskerCostClass = WhiskerCostClass.DETERMINISTIC
    priority: int = 100

    def evaluate(
        self,
        uniform: GovernedUniform,
        observation: TransitionObservation,
        *,
        moment: datetime,
    ) -> WhiskerResult:
        started = perf_counter_ns()
        try:
            assessment = self.evaluator(uniform, observation, moment)
        except Exception as exc:  # fail closed at the local control boundary
            assessment = WhiskerAssessment(
                disposition=WhiskerDisposition.BLOCK,
                reason_codes=(f"WHISKER_EVALUATION_ERROR:{type(exc).__name__}",),
            )
        duration = perf_counter_ns() - started
        return WhiskerResult(
            whisker_id=self.whisker_id,
            surface=observation.surface,
            mode=self.mode,
            cost_class=self.cost_class,
            disposition=assessment.disposition,
            reason_codes=assessment.reason_codes,
            evidence_refs=assessment.evidence_refs,
            uniform_digest=uniform.uniform_digest,
            transition_digest=observation.transition_digest,
            evaluated_at=moment,
            duration_ns=duration,
        )


class WhiskerCascadeResult(BaseModel):
    schema_version: Literal["whisker_cascade_result.v1"] = (
        "whisker_cascade_result.v1"
    )
    uniform_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    transition_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    results: tuple[WhiskerResult, ...]
    terminal_disposition: WhiskerDisposition | None = None
    completed_at: datetime
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def may_continue_to_next_governed_boundary(self) -> bool:
        return self.terminal_disposition is None

    @property
    def can_authorize_execution(self) -> bool:
        return False

    @property
    def result_digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class WhiskerCascade:
    def __init__(self, probes: Iterable[WhiskerProbe]) -> None:
        self._probes = tuple(
            sorted(
                probes,
                key=lambda probe: (
                    probe.cost_class.rank,
                    probe.priority,
                    probe.whisker_id,
                ),
            )
        )

    @property
    def ordered_probe_ids(self) -> tuple[str, ...]:
        return tuple(probe.whisker_id for probe in self._probes)

    def run(
        self,
        uniform: GovernedUniform,
        observation: TransitionObservation,
        *,
        moment: datetime | None = None,
    ) -> WhiskerCascadeResult:
        moment = moment or utcnow()
        results: list[WhiskerResult] = []
        terminal: WhiskerDisposition | None = None
        for probe in self._probes:
            if observation.surface not in probe.surfaces:
                continue
            result = probe.evaluate(uniform, observation, moment=moment)
            results.append(result)
            if result.is_binding_terminal:
                terminal = result.disposition
                break
        return WhiskerCascadeResult(
            uniform_digest=uniform.uniform_digest,
            transition_digest=observation.transition_digest,
            results=tuple(results),
            terminal_disposition=terminal,
            completed_at=moment,
        )


def uniform_freshness_whisker(
    *,
    mode: WhiskerMode = WhiskerMode.ENFORCE,
    priority: int = 0,
) -> CallableWhisker:
    def evaluate(
        uniform: GovernedUniform,
        observation: TransitionObservation,
        moment: datetime,
    ) -> WhiskerAssessment:
        del observation
        if uniform.is_fresh(moment):
            return WhiskerAssessment(
                disposition=WhiskerDisposition.PASS,
                reason_codes=("UNIFORM_FRESH",),
            )
        return WhiskerAssessment(
            disposition=WhiskerDisposition.BLOCK,
            reason_codes=("UNIFORM_STALE_OR_NOT_YET_ACTIVE",),
        )

    return CallableWhisker(
        whisker_id="uniform.freshness.v1",
        surfaces=frozenset(TransitionSurface),
        evaluator=evaluate,
        mode=mode,
        cost_class=WhiskerCostClass.DETERMINISTIC,
        priority=priority,
    )


def uniform_binding_whisker(
    *,
    mode: WhiskerMode = WhiskerMode.ENFORCE,
    priority: int = 1,
) -> CallableWhisker:
    def evaluate(
        uniform: GovernedUniform,
        observation: TransitionObservation,
        moment: datetime,
    ) -> WhiskerAssessment:
        del moment
        reasons: list[str] = []
        if observation.actor_id != uniform.actor_id:
            reasons.append("UNIFORM_ACTOR_MISMATCH")
        if observation.action_digest != uniform.action_digest:
            reasons.append("UNIFORM_ACTION_MISMATCH")
        if observation.state_ref != uniform.state_ref:
            reasons.append("UNIFORM_STATE_MISMATCH")
        if (
            uniform.consequence_ref is not None
            and observation.consequence_ref != uniform.consequence_ref
        ):
            reasons.append("UNIFORM_CONSEQUENCE_MISMATCH")
        if reasons:
            return WhiskerAssessment(
                disposition=WhiskerDisposition.BLOCK,
                reason_codes=tuple(reasons),
            )
        return WhiskerAssessment(
            disposition=WhiskerDisposition.PASS,
            reason_codes=("UNIFORM_BINDING_MATCH",),
        )

    return CallableWhisker(
        whisker_id="uniform.binding.v1",
        surfaces=frozenset(TransitionSurface),
        evaluator=evaluate,
        mode=mode,
        cost_class=WhiskerCostClass.DETERMINISTIC,
        priority=priority,
    )


def default_uniform_whiskers() -> tuple[CallableWhisker, ...]:
    return (uniform_freshness_whisker(), uniform_binding_whisker())
