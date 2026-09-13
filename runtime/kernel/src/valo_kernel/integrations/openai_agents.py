from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from valo_kernel.contracts.common import canonical_digest


class GateDisposition(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"
    DEFER = "DEFER"


class OpenAIToolCall(BaseModel):
    schema_version: Literal["openai_tool_call.v1"] = "openai_tool_call.v1"
    tool_name: str
    tool_call_id: str
    arguments: dict[str, Any]
    requested_at: datetime
    request_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"request_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_call(self) -> OpenAIToolCall:
        if not self.tool_name or not self.tool_call_id:
            raise ValueError("tool name and call id are required")
        if self.requested_at.tzinfo is None or self.requested_at.utcoffset() is None:
            raise ValueError("requested_at must be timezone-aware")
        if self.request_digest and self.request_digest != self.computed_digest:
            raise ValueError("tool call digest mismatch")
        return self


class ConsequenceDecision(BaseModel):
    schema_version: Literal["consequence_decision.v1"] = "consequence_decision.v1"
    disposition: GateDisposition
    decision_ref: str
    evaluated_at: datetime
    valid_until: datetime | None = None
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reason: str | None = None
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_decision(self) -> ConsequenceDecision:
        if not self.decision_ref:
            raise ValueError("decision_ref is required")
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        if self.valid_until is not None and (
            self.valid_until.tzinfo is None or self.valid_until.utcoffset() is None
        ):
            raise ValueError("valid_until must be timezone-aware")
        if self.disposition == GateDisposition.ALLOW:
            if self.action_digest is None:
                raise ValueError("ALLOW requires an exact action digest")
            if self.valid_until is None or self.valid_until <= self.evaluated_at:
                raise ValueError("ALLOW requires a positive freshness window")
        return self


class GateResult(BaseModel):
    schema_version: Literal["openai_consequence_gate_result.v1"] = (
        "openai_consequence_gate_result.v1"
    )
    allowed: bool
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision_ref: str | None = None
    disposition: GateDisposition
    action_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reason: str
    evaluated_at: datetime
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class ConsequenceAuthorizer(Protocol):
    def __call__(
        self, call: OpenAIToolCall
    ) -> ConsequenceDecision | Awaitable[ConsequenceDecision]: ...


def _seal_tool_call(
    *,
    tool_name: str,
    tool_call_id: str,
    arguments: dict[str, Any],
    requested_at: datetime,
) -> OpenAIToolCall:
    unsealed = OpenAIToolCall(
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        arguments=arguments,
        requested_at=requested_at,
    )
    return OpenAIToolCall.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "request_digest": unsealed.computed_digest,
        }
    )


def parse_tool_arguments(raw_arguments: str | None) -> dict[str, Any]:
    if raw_arguments is None:
        return {}
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise ValueError("tool arguments are not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("tool arguments must decode to a JSON object")
    return parsed


async def evaluate_tool_call(
    *,
    tool_name: str,
    tool_call_id: str,
    raw_arguments: str | None,
    authorizer: ConsequenceAuthorizer,
    now: datetime | None = None,
    clock: Callable[[], datetime] | None = None,
) -> GateResult:
    clock_fn = clock or (lambda: datetime.now(UTC))
    request_moment = now or clock_fn()
    if request_moment.tzinfo is None or request_moment.utcoffset() is None:
        raise ValueError("request time must be timezone-aware")

    try:
        arguments = parse_tool_arguments(raw_arguments)
    except ValueError as exc:
        malformed_digest = canonical_digest(
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "raw_arguments": raw_arguments,
            }
        )
        return GateResult(
            allowed=False,
            request_digest=malformed_digest,
            disposition=GateDisposition.DENY,
            reason=str(exc),
            evaluated_at=request_moment,
        )

    call = _seal_tool_call(
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        arguments=arguments,
        requested_at=request_moment,
    )

    decision_or_awaitable = authorizer(call)
    decision = (
        await decision_or_awaitable
        if inspect.isawaitable(decision_or_awaitable)
        else decision_or_awaitable
    )
    effect_moment = clock_fn()
    if effect_moment.tzinfo is None or effect_moment.utcoffset() is None:
        raise ValueError("effect time must be timezone-aware")

    if decision.request_digest != call.request_digest:
        return GateResult(
            allowed=False,
            request_digest=call.request_digest,
            decision_ref=decision.decision_ref,
            disposition=GateDisposition.DENY,
            reason="authority decision is bound to another tool call",
            evaluated_at=effect_moment,
        )

    if decision.evaluated_at < call.requested_at:
        return GateResult(
            allowed=False,
            request_digest=call.request_digest,
            decision_ref=decision.decision_ref,
            disposition=GateDisposition.DENY,
            reason="authority decision predates the consequence-time request",
            evaluated_at=effect_moment,
        )

    if effect_moment < decision.evaluated_at:
        return GateResult(
            allowed=False,
            request_digest=call.request_digest,
            decision_ref=decision.decision_ref,
            disposition=GateDisposition.DENY,
            reason="effect-boundary clock predates authority evaluation",
            evaluated_at=effect_moment,
        )

    if decision.disposition != GateDisposition.ALLOW:
        return GateResult(
            allowed=False,
            request_digest=call.request_digest,
            decision_ref=decision.decision_ref,
            disposition=decision.disposition,
            action_digest=decision.action_digest,
            reason=decision.reason or "consequence-time authority did not allow execution",
            evaluated_at=effect_moment,
        )

    if decision.valid_until is None or effect_moment >= decision.valid_until:
        return GateResult(
            allowed=False,
            request_digest=call.request_digest,
            decision_ref=decision.decision_ref,
            disposition=GateDisposition.DENY,
            action_digest=decision.action_digest,
            reason="consequence-time authority clearance is stale",
            evaluated_at=effect_moment,
        )

    return GateResult(
        allowed=True,
        request_digest=call.request_digest,
        decision_ref=decision.decision_ref,
        disposition=GateDisposition.ALLOW,
        action_digest=decision.action_digest,
        reason=decision.reason or "fresh consequence-time authority allows execution",
        evaluated_at=effect_moment,
    )


def make_openai_tool_input_guardrail(
    authorizer: ConsequenceAuthorizer,
    *,
    clock: Callable[[], datetime] | None = None,
):
    """Return an OpenAI Agents SDK ToolInputGuardrail without a hard SDK dependency."""

    try:
        from agents import ToolGuardrailFunctionOutput, ToolInputGuardrail
    except ImportError as exc:  # pragma: no cover - depends on optional external SDK
        raise RuntimeError(
            "openai-agents is required to construct the OpenAI tool guardrail"
        ) from exc

    now_fn = clock or (lambda: datetime.now(UTC))

    async def consequence_time_guardrail(data):
        result = await evaluate_tool_call(
            tool_name=data.context.tool_name,
            tool_call_id=data.context.tool_call_id,
            raw_arguments=data.context.tool_arguments,
            authorizer=authorizer,
            clock=now_fn,
        )
        output_info = result.model_dump(mode="json")
        if result.allowed:
            return ToolGuardrailFunctionOutput.allow(output_info=output_info)
        return ToolGuardrailFunctionOutput.raise_exception(output_info=output_info)

    return ToolInputGuardrail(
        guardrail_function=consequence_time_guardrail,
        name="valo_consequence_time_authority",
    )
