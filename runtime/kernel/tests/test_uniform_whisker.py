from __future__ import annotations

from datetime import UTC, datetime, timedelta

from valo_kernel.contracts.common import canonical_digest
from valo_kernel.contracts.uniform_whisker import (
    CallableWhisker,
    GovernedUniform,
    TransitionObservation,
    TransitionSurface,
    WhiskerAssessment,
    WhiskerCascade,
    WhiskerCostClass,
    WhiskerDisposition,
    WhiskerMode,
    default_uniform_whiskers,
    uniform_binding_whisker,
    uniform_freshness_whisker,
)


def _digest(label: str) -> str:
    return canonical_digest({"label": label})


def _uniform(now: datetime) -> GovernedUniform:
    return GovernedUniform(
        uniform_id="uniform:1",
        tenant_id="tenant:1",
        actor_id="agent:1",
        identity_ref="identity:1",
        capability="payment.submit",
        target="invoice:123",
        action_digest=_digest("action"),
        source_context_digest=_digest("execution-context"),
        state_ref="state:42",
        authority_refs=("authority:1",),
        delegation_refs=("delegation:1",),
        purpose_ref="purpose:settle-invoice",
        constraint_refs=("constraint:limit",),
        evidence_refs=("evidence:standing",),
        permitted_effect_classes=("PAYMENT",),
        consequence_ref="consequence:invoice-123",
        issued_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=5),
        revocation_epoch=7,
    )


def _observation(
    now: datetime,
    *,
    surface: TransitionSurface = TransitionSurface.EFFECT_COMMIT,
    actor_id: str = "agent:1",
    action_digest: str | None = None,
    state_ref: str = "state:42",
    consequence_ref: str | None = "consequence:invoice-123",
) -> TransitionObservation:
    return TransitionObservation(
        transition_id="transition:1",
        surface=surface,
        actor_id=actor_id,
        action_digest=action_digest or _digest("action"),
        payload_digest=_digest("payload"),
        state_ref=state_ref,
        consequence_ref=consequence_ref,
        observed_at=now,
    )


def test_uniform_is_portable_context_not_authorization() -> None:
    now = datetime.now(UTC)
    uniform = _uniform(now)

    assert uniform.is_fresh(now)
    assert uniform.can_issue_clearance is False
    assert uniform.can_authorize_execution is False
    assert uniform.authority_effect == "NO_AUTHORITY_CREATION"
    assert len(uniform.uniform_digest) == 64


def test_default_uniform_whiskers_pass_exact_fresh_binding() -> None:
    now = datetime.now(UTC)
    uniform = _uniform(now)
    result = WhiskerCascade(default_uniform_whiskers()).run(
        uniform,
        _observation(now),
        moment=now,
    )

    assert [item.whisker_id for item in result.results] == [
        "uniform.freshness.v1",
        "uniform.binding.v1",
    ]
    assert all(item.disposition is WhiskerDisposition.PASS for item in result.results)
    assert result.terminal_disposition is None
    assert result.may_continue_to_next_governed_boundary is True
    assert result.can_authorize_execution is False
    assert all(item.can_authorize_execution is False for item in result.results)


def test_stale_uniform_blocks_before_later_whiskers() -> None:
    now = datetime.now(UTC)
    uniform = _uniform(now)
    after_expiry = uniform.valid_until + timedelta(microseconds=1)

    result = WhiskerCascade(default_uniform_whiskers()).run(
        uniform,
        _observation(now),
        moment=after_expiry,
    )

    assert len(result.results) == 1
    assert result.results[0].whisker_id == "uniform.freshness.v1"
    assert result.results[0].disposition is WhiskerDisposition.BLOCK
    assert result.terminal_disposition is WhiskerDisposition.BLOCK


def test_binding_whisker_catches_actor_action_state_and_consequence_drift() -> None:
    now = datetime.now(UTC)
    result = WhiskerCascade((uniform_binding_whisker(),)).run(
        _uniform(now),
        _observation(
            now,
            actor_id="agent:other",
            action_digest=_digest("mutated-action"),
            state_ref="state:43",
            consequence_ref="consequence:other",
        ),
        moment=now,
    )

    assert result.terminal_disposition is WhiskerDisposition.BLOCK
    assert set(result.results[0].reason_codes) == {
        "UNIFORM_ACTOR_MISMATCH",
        "UNIFORM_ACTION_MISMATCH",
        "UNIFORM_STATE_MISMATCH",
        "UNIFORM_CONSEQUENCE_MISMATCH",
    }


def test_cascade_orders_cheap_deterministic_before_model_judge_and_short_circuits() -> None:
    now = datetime.now(UTC)
    calls: list[str] = []

    def model_judge(
        uniform: GovernedUniform,
        observation: TransitionObservation,
        moment: datetime,
    ) -> WhiskerAssessment:
        del uniform, observation, moment
        calls.append("model")
        return WhiskerAssessment(
            disposition=WhiskerDisposition.PASS,
            reason_codes=("MODEL_PASS",),
        )

    def deterministic_block(
        uniform: GovernedUniform,
        observation: TransitionObservation,
        moment: datetime,
    ) -> WhiskerAssessment:
        del uniform, observation, moment
        calls.append("deterministic")
        return WhiskerAssessment(
            disposition=WhiskerDisposition.BLOCK,
            reason_codes=("KNOWN_BAD_PATTERN",),
        )

    cascade = WhiskerCascade(
        (
            CallableWhisker(
                whisker_id="judge",
                surfaces=frozenset({TransitionSurface.INPUT}),
                evaluator=model_judge,
                cost_class=WhiskerCostClass.MODEL_JUDGE,
            ),
            CallableWhisker(
                whisker_id="regex",
                surfaces=frozenset({TransitionSurface.INPUT}),
                evaluator=deterministic_block,
                cost_class=WhiskerCostClass.DETERMINISTIC,
            ),
        )
    )

    assert cascade.ordered_probe_ids == ("regex", "judge")
    result = cascade.run(
        _uniform(now),
        _observation(now, surface=TransitionSurface.INPUT),
        moment=now,
    )

    assert calls == ["deterministic"]
    assert result.terminal_disposition is WhiskerDisposition.BLOCK


def test_shadow_block_is_recorded_but_cannot_stop_enforced_path() -> None:
    now = datetime.now(UTC)
    calls: list[str] = []

    def shadow_candidate(
        uniform: GovernedUniform,
        observation: TransitionObservation,
        moment: datetime,
    ) -> WhiskerAssessment:
        del uniform, observation, moment
        calls.append("shadow")
        return WhiskerAssessment(
            disposition=WhiskerDisposition.BLOCK,
            reason_codes=("SHADOW_WOULD_BLOCK",),
        )

    def enforced_pass(
        uniform: GovernedUniform,
        observation: TransitionObservation,
        moment: datetime,
    ) -> WhiskerAssessment:
        del uniform, observation, moment
        calls.append("enforce")
        return WhiskerAssessment(
            disposition=WhiskerDisposition.PASS,
            reason_codes=("ENFORCED_PASS",),
        )

    cascade = WhiskerCascade(
        (
            CallableWhisker(
                whisker_id="shadow-new-control",
                surfaces=frozenset({TransitionSurface.MODEL_OUTPUT}),
                evaluator=shadow_candidate,
                mode=WhiskerMode.SHADOW,
                cost_class=WhiskerCostClass.DETERMINISTIC,
                priority=0,
            ),
            CallableWhisker(
                whisker_id="existing-control",
                surfaces=frozenset({TransitionSurface.MODEL_OUTPUT}),
                evaluator=enforced_pass,
                mode=WhiskerMode.ENFORCE,
                cost_class=WhiskerCostClass.DETERMINISTIC,
                priority=1,
            ),
        )
    )

    result = cascade.run(
        _uniform(now),
        _observation(now, surface=TransitionSurface.MODEL_OUTPUT),
        moment=now,
    )

    assert calls == ["shadow", "enforce"]
    assert result.results[0].disposition is WhiskerDisposition.BLOCK
    assert result.results[0].is_binding_terminal is False
    assert result.terminal_disposition is None


def test_whisker_evaluation_error_fails_closed_in_enforce_mode() -> None:
    now = datetime.now(UTC)

    def broken(
        uniform: GovernedUniform,
        observation: TransitionObservation,
        moment: datetime,
    ) -> WhiskerAssessment:
        del uniform, observation, moment
        raise RuntimeError("provider unavailable")

    result = WhiskerCascade(
        (
            CallableWhisker(
                whisker_id="broken",
                surfaces=frozenset({TransitionSurface.ROUTING}),
                evaluator=broken,
            ),
        )
    ).run(
        _uniform(now),
        _observation(now, surface=TransitionSurface.ROUTING),
        moment=now,
    )

    assert result.terminal_disposition is WhiskerDisposition.BLOCK
    assert result.results[0].reason_codes == (
        "WHISKER_EVALUATION_ERROR:RuntimeError",
    )


def test_step_up_is_terminal_but_still_not_execution_authorization() -> None:
    now = datetime.now(UTC)

    def needs_human(
        uniform: GovernedUniform,
        observation: TransitionObservation,
        moment: datetime,
    ) -> WhiskerAssessment:
        del uniform, observation, moment
        return WhiskerAssessment(
            disposition=WhiskerDisposition.STEP_UP,
            reason_codes=("HUMAN_REVIEW_REQUIRED",),
        )

    result = WhiskerCascade(
        (
            CallableWhisker(
                whisker_id="risk-step-up",
                surfaces=frozenset({TransitionSurface.TOOL_REQUEST}),
                evaluator=needs_human,
            ),
        )
    ).run(
        _uniform(now),
        _observation(now, surface=TransitionSurface.TOOL_REQUEST),
        moment=now,
    )

    assert result.terminal_disposition is WhiskerDisposition.STEP_UP
    assert result.can_authorize_execution is False
    assert result.results[0].can_issue_clearance is False
