from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from valo_gateway.contracts import ActionEnvelope, Decision
from valo_gateway.gateway import ToolExecutionResult, ValoGateway
from valo_gateway.integrations.langgraph import (
    FreshAuthorizer,
    GatewayBindingResolver,
    LangGraphAuthorization,
)


@dataclass(frozen=True)
class FrameworkToolCall:
    provider: str
    call_id: str | None
    name: str
    arguments: dict[str, Any]
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class GovernedFrameworkResult:
    call: FrameworkToolCall
    action: ActionEnvelope
    authorization: LangGraphAuthorization
    execution: ToolExecutionResult | None


ActionFactory = Callable[[FrameworkToolCall], ActionEnvelope]


class GovernedFrameworkAdapter:
    """Framework-neutral ingress to the HEIMEL consequence boundary."""

    provider = "generic"

    def __init__(
        self,
        *,
        authorizer: FreshAuthorizer,
        gateway: ValoGateway,
        action_factory: ActionFactory,
        binding_resolver: GatewayBindingResolver,
    ) -> None:
        self._authorizer = authorizer
        self._gateway = gateway
        self._action_factory = action_factory
        self._binding_resolver = binding_resolver

    def execute(
        self,
        payload: Mapping[str, Any],
        *,
        evidence: Any | None = None,
    ) -> GovernedFrameworkResult:
        call = self.decode(payload)
        action = self._action_factory(call)
        if not isinstance(action, ActionEnvelope):
            raise TypeError("action_factory must return ActionEnvelope")

        authorization = self._authorizer.authorize(action=action, evidence=evidence)
        self._assert_authorization_binding(action, authorization)

        if authorization.decision is not Decision.ALLOW:
            if authorization.permit is not None:
                raise ValueError("DENY/ESCALATE must not carry an execution permit")
            return GovernedFrameworkResult(call, action, authorization, None)

        permit = authorization.permit
        if permit is None:
            raise ValueError("ALLOW requires a bound one-shot execution permit")

        bindings = dict(self._binding_resolver(action))
        forbidden = {"authority", "clearance", "permit", "action", "arguments"}.intersection(
            bindings
        )
        if forbidden:
            names = ", ".join(sorted(forbidden))
            raise ValueError(
                f"binding_resolver cannot override governed bindings: {names}"
            )

        execution = self._gateway.execute(
            authority=authorization.authority,
            clearance=authorization.clearance,
            permit=permit,
            action=action,
            arguments=action.parameters,
            **bindings,
        )
        return GovernedFrameworkResult(call, action, authorization, execution)

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        raise NotImplementedError

    def _call(
        self,
        payload: Mapping[str, Any],
        *,
        name: Any,
        arguments: Any,
        call_id: Any = None,
    ) -> FrameworkToolCall:
        if not isinstance(name, str) or not name:
            raise ValueError(f"{self.provider} tool call is missing a name")
        parsed = _arguments(arguments)
        return FrameworkToolCall(
            provider=self.provider,
            call_id=str(call_id) if call_id is not None else None,
            name=name,
            arguments=parsed,
            raw=payload,
        )

    @staticmethod
    def _assert_authorization_binding(
        action: ActionEnvelope,
        authorization: LangGraphAuthorization,
    ) -> None:
        if action.authority_envelope_id != authorization.authority.envelope_id:
            raise ValueError("authorizer authority does not match proposed effect binding")
        if authorization.clearance.action_digest != action.digest:
            raise ValueError("authorizer clearance is not bound to exact proposed effect")
        if (
            authorization.clearance.authority_envelope_id
            != authorization.authority.envelope_id
        ):
            raise ValueError("authorizer returned mismatched authority and clearance")
        permit = authorization.permit
        if permit is not None:
            if permit.action_digest != action.digest:
                raise ValueError("authorizer permit is not bound to exact proposed effect")
            if permit.authority_envelope_id != authorization.authority.envelope_id:
                raise ValueError("authorizer returned mismatched authority and permit")
            if permit.clearance_id != authorization.clearance.clearance_id:
                raise ValueError("authorizer returned mismatched clearance and permit")


class MCPGatewayAdapter(GovernedFrameworkAdapter):
    provider = "mcp"

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        if payload.get("method") != "tools/call":
            raise ValueError("MCP adapter accepts only tools/call")
        params = _mapping(payload.get("params"), "MCP params")
        return self._call(
            payload,
            call_id=payload.get("id"),
            name=params.get("name"),
            arguments=params.get("arguments", {}),
        )


class OpenAIGatewayAdapter(GovernedFrameworkAdapter):
    provider = "openai"

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        function = payload.get("function")
        if isinstance(function, Mapping):
            return self._call(
                payload,
                call_id=payload.get("call_id", payload.get("id")),
                name=function.get("name"),
                arguments=function.get("arguments", {}),
            )
        return self._call(
            payload,
            call_id=payload.get("call_id", payload.get("id")),
            name=payload.get("name"),
            arguments=payload.get("arguments", {}),
        )


class AnthropicGatewayAdapter(GovernedFrameworkAdapter):
    provider = "anthropic"

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        if payload.get("type") not in (None, "tool_use"):
            raise ValueError("Anthropic adapter accepts only tool_use blocks")
        return self._call(
            payload,
            call_id=payload.get("id"),
            name=payload.get("name"),
            arguments=payload.get("input", {}),
        )


class GoogleADKGatewayAdapter(GovernedFrameworkAdapter):
    provider = "google-adk"

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        call = payload.get("functionCall", payload)
        call = _mapping(call, "Google functionCall")
        return self._call(
            payload,
            call_id=call.get("id", payload.get("id")),
            name=call.get("name"),
            arguments=call.get("args", call.get("arguments", {})),
        )


class SemanticKernelGatewayAdapter(GovernedFrameworkAdapter):
    provider = "semantic-kernel"

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        name = payload.get("function_name", payload.get("name"))
        plugin = payload.get("plugin_name")
        if isinstance(plugin, str) and plugin and isinstance(name, str) and name:
            name = f"{plugin}.{name}"
        return self._call(
            payload,
            call_id=payload.get("id"),
            name=name,
            arguments=payload.get("arguments", {}),
        )


class CrewAIGatewayAdapter(GovernedFrameworkAdapter):
    provider = "crewai"

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        return self._call(
            payload,
            call_id=payload.get("id"),
            name=payload.get("tool", payload.get("name")),
            arguments=payload.get("arguments", payload.get("tool_input", {})),
        )


class AutoGenGatewayAdapter(GovernedFrameworkAdapter):
    provider = "autogen"

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        function = payload.get("function")
        if isinstance(function, Mapping):
            return self._call(
                payload,
                call_id=payload.get("id"),
                name=function.get("name"),
                arguments=function.get("arguments", {}),
            )
        return self._call(
            payload,
            call_id=payload.get("id"),
            name=payload.get("name"),
            arguments=payload.get("arguments", {}),
        )


class AutoGenGuardrailDecision(str, Enum):
    """Dependency-free mirror of the GuardrailProvider decision contract."""

    ALLOW = "allow"
    DENY = "deny"
    MODIFY = "modify"


@dataclass(frozen=True)
class AutoGenGuardrailResult:
    """Admission result returned by :class:`AutoGenGuardrailProviderAdapter`.

    ``ALLOW`` is deliberately only an admission result.  It is not an
    execution permit and must not be used to call an AutoGen tool directly.
    The effect must be submitted through ``execute`` so HEIMEL can resolve
    authority again at consequence time.
    """

    decision: AutoGenGuardrailDecision
    reason: str | None = None
    modified_args: Mapping[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class AutoGenGuardrailProviderAdapter:
    """Adapt AutoGen's proposed ``GuardrailProvider`` hook to HEIMEL.

    The adapter intentionally does not import AutoGen.  Its ``evaluate``
    method has the proposed keyword-only shape, so it can be passed to
    AutoGen when that protocol lands, while remaining usable by current
    AutoGen versions and tests.

    A guardrail approval is only a pre-execution admission decision.  Calling
    ``execute`` performs the normal AutoGen gateway flow, including a fresh
    authority/control-plane check immediately before the effect.
    """

    def __init__(self, gateway_adapter: AutoGenGatewayAdapter) -> None:
        self._gateway_adapter = gateway_adapter

    async def evaluate(
        self,
        *,
        tool_name: str,
        args: Mapping[str, Any],
        agent_name: str | None = None,
        call_id: str | None = None,
        cancellation_token: Any | None = None,
    ) -> AutoGenGuardrailResult:
        del cancellation_token
        if not isinstance(tool_name, str) or not tool_name:
            raise ValueError("AutoGen tool_name must be explicit")

        payload = {"id": call_id, "name": tool_name, "arguments": dict(args)}
        call = self._gateway_adapter.decode(payload)
        action = self._gateway_adapter._action_factory(call)
        authorization = self._gateway_adapter._authorizer.authorize(action=action)
        self._gateway_adapter._assert_authorization_binding(action, authorization)

        decision = authorization.decision
        if decision is Decision.ALLOW:
            result_decision = AutoGenGuardrailDecision.ALLOW
            reason = None
        elif decision is Decision.MODIFY:
            # HEIMEL never silently invents replacement arguments.  A caller
            # that needs modification must provide a separate, explicit
            # transformation before proposing the governed action.
            result_decision = AutoGenGuardrailDecision.DENY
            reason = "HEIMEL MODIFY requires an explicit re-proposed action"
        else:
            result_decision = AutoGenGuardrailDecision.DENY
            reason = f"HEIMEL authority decision: {decision.value}"

        return AutoGenGuardrailResult(
            decision=result_decision,
            reason=reason,
            metadata={
                "provider": "autogen",
                "agent_name": agent_name,
                "call_id": call_id,
                "action_digest": action.digest,
                "authority_decision": decision.value,
            },
        )

    def execute(
        self,
        *,
        tool_name: str,
        args: Mapping[str, Any],
        call_id: str | None = None,
        admission: AutoGenGuardrailResult | None = None,
    ) -> GovernedFrameworkResult:
        """Execute one admitted call through the fresh consequence boundary."""

        if admission is not None and admission.decision is not AutoGenGuardrailDecision.ALLOW:
            raise PermissionError(admission.reason or "AutoGen guardrail denied tool call")
        payload = {"id": call_id, "name": tool_name, "arguments": dict(args)}
        return self._gateway_adapter.execute(payload)


class HTTPWebhookGatewayAdapter(GovernedFrameworkAdapter):
    provider = "http-webhook"

    def decode(self, payload: Mapping[str, Any]) -> FrameworkToolCall:
        return self._call(
            payload,
            call_id=payload.get("id"),
            name=payload.get("effect", payload.get("name")),
            arguments=payload.get("arguments", payload.get("parameters", {})),
        )


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _arguments(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("tool arguments must be valid JSON") from exc
    if not isinstance(value, Mapping):
        raise ValueError("tool arguments must be an object")
    return dict(value)
