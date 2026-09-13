from valo_kernel.context_effects import (
    ContextAcquisition,
    ContextEffectDecision,
    ContextEffectReason,
    ContextIntent,
    assess_context_acquisition,
)


def test_gitspawn_fsmonitor_is_denied_before_trust() -> None:
    assessment = assess_context_acquisition(
        ContextAcquisition(
            intent=ContextIntent.STATUS,
            source_trusted=False,
            repository_config_enabled=True,
            executable_config_hooks=("core.fsmonitor",),
        )
    )

    assert assessment.decision is ContextEffectDecision.DENY
    assert assessment.reason is ContextEffectReason.NO_UNGOVERNED_CONTEXT_EFFECT_PATH
    assert assessment.possible_process_execution is True
    assert assessment.allowed is False


def test_surface_read_labels_do_not_downgrade_possible_execution() -> None:
    for intent in (
        ContextIntent.READ,
        ContextIntent.STATUS,
        ContextIntent.DIFF,
        ContextIntent.INSPECT,
    ):
        assessment = assess_context_acquisition(
            ContextAcquisition(
                intent=intent,
                source_trusted=False,
                repository_config_enabled=True,
                executable_config_hooks=("core.fsmonitor",),
            )
        )

        assert assessment.decision is ContextEffectDecision.DENY
        assert assessment.reason is ContextEffectReason.NO_UNGOVERNED_CONTEXT_EFFECT_PATH


def test_unknown_transitive_effects_fail_closed() -> None:
    assessment = assess_context_acquisition(
        ContextAcquisition(
            intent=ContextIntent.INSPECT,
            source_trusted=False,
            repository_config_enabled=True,
            transitive_effects_known=False,
        )
    )

    assert assessment.decision is ContextEffectDecision.DENY
    assert assessment.reason is ContextEffectReason.UNKNOWN_TRANSITIVE_EFFECT


def test_sanitized_repo_config_is_effect_free() -> None:
    assessment = assess_context_acquisition(
        ContextAcquisition(
            intent=ContextIntent.STATUS,
            source_trusted=False,
            repository_config_enabled=False,
            executable_config_hooks=("core.fsmonitor",),
        )
    )

    assert assessment.decision is ContextEffectDecision.ALLOW_EFFECT_FREE
    assert assessment.reason is ContextEffectReason.EFFECT_FREE
    assert assessment.possible_process_execution is False


def test_possible_execution_requires_explicit_governed_authorization() -> None:
    request = ContextAcquisition(
        intent=ContextIntent.DIFF,
        source_trusted=False,
        repository_config_enabled=True,
        executable_config_hooks=("core.fsmonitor",),
        governed_effect_path=True,
        effect_authorized=False,
    )

    denied = assess_context_acquisition(request)
    assert denied.decision is ContextEffectDecision.DENY
    assert denied.reason is ContextEffectReason.EFFECT_NOT_AUTHORIZED

    allowed = assess_context_acquisition(
        ContextAcquisition(
            intent=request.intent,
            source_trusted=request.source_trusted,
            repository_config_enabled=request.repository_config_enabled,
            executable_config_hooks=request.executable_config_hooks,
            governed_effect_path=True,
            effect_authorized=True,
        )
    )
    assert allowed.decision is ContextEffectDecision.ALLOW_GOVERNED
    assert allowed.reason is ContextEffectReason.GOVERNED_EFFECT_PATH
