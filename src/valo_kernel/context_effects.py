from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContextIntent(StrEnum):
    READ = "READ"
    STATUS = "STATUS"
    DIFF = "DIFF"
    INSPECT = "INSPECT"
    OTHER = "OTHER"


class ContextEffectDecision(StrEnum):
    ALLOW_EFFECT_FREE = "ALLOW_EFFECT_FREE"
    ALLOW_GOVERNED = "ALLOW_GOVERNED"
    DENY = "DENY"


class ContextEffectReason(StrEnum):
    EFFECT_FREE = "EFFECT_FREE"
    GOVERNED_EFFECT_PATH = "GOVERNED_EFFECT_PATH"
    UNKNOWN_TRANSITIVE_EFFECT = "UNKNOWN_TRANSITIVE_EFFECT"
    NO_UNGOVERNED_CONTEXT_EFFECT_PATH = "NO_UNGOVERNED_CONTEXT_EFFECT_PATH"
    EFFECT_NOT_AUTHORIZED = "EFFECT_NOT_AUTHORIZED"


@dataclass(frozen=True)
class ContextAcquisition:
    """A context-read request classified by possible consequence, not its label."""

    intent: ContextIntent
    source_trusted: bool
    repository_config_enabled: bool
    executable_config_hooks: tuple[str, ...] = ()
    transitive_effects_known: bool = True
    governed_effect_path: bool = False
    effect_authorized: bool = False


@dataclass(frozen=True)
class ContextEffectAssessment:
    decision: ContextEffectDecision
    reason: ContextEffectReason
    possible_process_execution: bool

    @property
    def allowed(self) -> bool:
        return self.decision is not ContextEffectDecision.DENY


def assess_context_acquisition(request: ContextAcquisition) -> ContextEffectAssessment:
    """Fail closed when context acquisition can transitively create an effect.

    Repository-controlled executable configuration is treated as consequence-
    bearing input. The surface intent (READ/STATUS/DIFF/INSPECT) does not reduce
    the assessed capability.
    """

    if not request.transitive_effects_known:
        return ContextEffectAssessment(
            decision=ContextEffectDecision.DENY,
            reason=ContextEffectReason.UNKNOWN_TRANSITIVE_EFFECT,
            possible_process_execution=False,
        )

    possible_process_execution = (
        request.repository_config_enabled
        and bool(request.executable_config_hooks)
        and not request.source_trusted
    )

    if not possible_process_execution:
        return ContextEffectAssessment(
            decision=ContextEffectDecision.ALLOW_EFFECT_FREE,
            reason=ContextEffectReason.EFFECT_FREE,
            possible_process_execution=False,
        )

    if not request.governed_effect_path:
        return ContextEffectAssessment(
            decision=ContextEffectDecision.DENY,
            reason=ContextEffectReason.NO_UNGOVERNED_CONTEXT_EFFECT_PATH,
            possible_process_execution=True,
        )

    if not request.effect_authorized:
        return ContextEffectAssessment(
            decision=ContextEffectDecision.DENY,
            reason=ContextEffectReason.EFFECT_NOT_AUTHORIZED,
            possible_process_execution=True,
        )

    return ContextEffectAssessment(
        decision=ContextEffectDecision.ALLOW_GOVERNED,
        reason=ContextEffectReason.GOVERNED_EFFECT_PATH,
        possible_process_execution=True,
    )
