from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from valo_gateway.contracts import (
    ActionEnvelope,
    AuthorityEnvelope,
    Clearance,
    Decision,
    ExecutionPermit,
)
from valo_gateway.gateway import ToolExecutionResult, ValoGateway

PROPOSED_EFFECT_KEY = "proposed_effect"
EFFECT_DIGEST_KEY = "effect_digest"
AUTHORITY_DECISION_KEY = "authority_decision"
AUTHORITY_KEY = "authority"
CLEARANCE_KEY = "clearance"
PERMIT_KEY = "permit"
PERMIT_ID_KEY = "permit_id"
HUMAN_EVIDENCE_KEY = "human_evidence"
EFFECT_RESULT_KEY = "effect_result"


@dataclass(frozen=True)
class LangGraphAuthorization:
    """Fresh authorization result returned by the configured HEIMEL authorizer."""

    decision: Decision
    authority: AuthorityEnvelope
    clearance: Clearance
    permit: ExecutionPermit | None = None


class FreshAuthorizer(Protocol):
    """Resolve fresh authority for one exact proposed effect.

    Implementations may call REHT/RACS or another HEIMEL-compatible authority
    provider. Human approval is evidence only; the authorizer remains the only
    component allowed to return ALLOW plus an execution permit.
    """

    def authorize(
        self,
        *,
        action: ActionEnvelope,
        evidence: Any | None = None,
    ) -> LangGraphAuthorization: ...


GatewayBindingResolver = Callable[[ActionEnvelope], dict[str, Any]]


class LangGraphGatewayAdapter:
    """Thin LangGraph integration around HEIMEL's consequence boundary.

    The adapter deliberately has no dependency on LangGraph itself. Its node
    methods accept and return mapping-shaped state updates, so they can be
    registered directly as LangGraph nodes while keeping LangGraph state
    non-authoritative.

    Invariants:
    - proposed effects are bound by their ActionEnvelope digest;
    - ALLOW comes only from the fresh authorizer;
    - human approval is fed back as evidence and always re-authorized;
    - consequence-bearing execution always traverses ValoGateway;
    - checkpointed permit data cannot make a consumed/revoked permit valid.
    """

    def __init__(
        self,
        *,
        authorizer: FreshAuthorizer,
        gateway: ValoGateway,
        binding_resolver: GatewayBindingResolver,
    ) -> None:
        self._authorizer = authorizer
        self._gateway = gateway
        self._binding_resolver = binding_resolver

    @staticmethod
    def proposal_update(action: ActionEnvelope) -> dict[str, Any]:
        """Freeze one exact proposed effect into graph state.

        Any previous authorization artifacts are cleared so a changed proposal
        cannot inherit an earlier decision or permit.
        """

        return {
            PROPOSED_EFFECT_KEY: action,
            EFFECT_DIGEST_KEY: action.digest,
            AUTHORITY_DECISION_KEY: None,
            AUTHORITY_KEY: None,
            CLEARANCE_KEY: None,
            PERMIT_KEY: None,
            PERMIT_ID_KEY: None,
            EFFECT_RESULT_KEY: None,
        }

    def authorization_node(self, state: Mapping[str, Any]) -> dict[str, Any]:
        action = self._require_action(state)
        self._assert_effect_digest(state, action)

        authorization = self._authorizer.authorize(
            action=action,
            evidence=state.get(HUMAN_EVIDENCE_KEY),
        )
        self._assert_authorization_binding(action, authorization)

        permit = authorization.permit
        if authorization.decision is Decision.ALLOW and permit is None:
            raise ValueError("ALLOW requires a bound one-shot execution permit")
        if authorization.decision is not Decision.ALLOW and permit is not None:
            raise ValueError("DENY/ESCALATE must not carry an execution permit")

        return {
            AUTHORITY_DECISION_KEY: authorization.decision.value,
            AUTHORITY_KEY: authorization.authority,
            CLEARANCE_KEY: authorization.clearance,
            PERMIT_KEY: permit,
            PERMIT_ID_KEY: permit.permit_id if permit is not None else None,
        }

    def gateway_node(self, state: Mapping[str, Any]) -> dict[str, Any]:
        action = self._require_action(state)
        self._assert_effect_digest(state, action)

        if state.get(AUTHORITY_DECISION_KEY) != Decision.ALLOW.value:
            raise PermissionError("HEIMEL gateway execution requires fresh ALLOW")

        authority = state.get(AUTHORITY_KEY)
        clearance = state.get(CLEARANCE_KEY)
        permit = state.get(PERMIT_KEY)
        if not isinstance(authority, AuthorityEnvelope):
            raise ValueError("missing bound authority for governed execution")
        if not isinstance(clearance, Clearance):
            raise ValueError("missing bound clearance for governed execution")
        if not isinstance(permit, ExecutionPermit):
            raise ValueError("missing bound one-shot permit for governed execution")
        if state.get(PERMIT_ID_KEY) != permit.permit_id:
            raise ValueError("checkpoint permit id does not match bound permit")

        bindings = dict(self._binding_resolver(action))
        forbidden = {"authority", "clearance", "permit", "action"}.intersection(bindings)
        if forbidden:
            names = ", ".join(sorted(forbidden))
            raise ValueError(f"binding_resolver cannot override governed bindings: {names}")

        result = self._gateway.execute(
            authority=authority,
            clearance=clearance,
            permit=permit,
            action=action,
            arguments=action.parameters,
            **bindings,
        )

        return {
            EFFECT_RESULT_KEY: result,
            PERMIT_KEY: None,
        }

    @staticmethod
    def route_after_authorization(state: Mapping[str, Any]) -> str:
        decision = state.get(AUTHORITY_DECISION_KEY)
        if decision not in {member.value for member in Decision}:
            raise ValueError("authority decision is missing or invalid")
        return str(decision)

    @staticmethod
    def human_evidence_update(evidence: Any) -> dict[str, Any]:
        """Add approval/evidence while forcing a fresh authorization pass."""

        return {
            HUMAN_EVIDENCE_KEY: evidence,
            AUTHORITY_DECISION_KEY: None,
            AUTHORITY_KEY: None,
            CLEARANCE_KEY: None,
            PERMIT_KEY: None,
            PERMIT_ID_KEY: None,
        }

    @staticmethod
    def receipt_from_state(state: Mapping[str, Any]):
        result = state.get(EFFECT_RESULT_KEY)
        if not isinstance(result, ToolExecutionResult):
            raise ValueError("state does not contain a gateway execution result")
        return result.receipt

    @staticmethod
    def _require_action(state: Mapping[str, Any]) -> ActionEnvelope:
        action = state.get(PROPOSED_EFFECT_KEY)
        if not isinstance(action, ActionEnvelope):
            raise ValueError("LangGraph state is missing an exact proposed effect")
        return action

    @staticmethod
    def _assert_effect_digest(
        state: Mapping[str, Any], action: ActionEnvelope
    ) -> None:
        if state.get(EFFECT_DIGEST_KEY) != action.digest:
            raise ValueError("proposed effect changed after graph binding")

    @staticmethod
    def _assert_authorization_binding(
        action: ActionEnvelope,
        authorization: LangGraphAuthorization,
    ) -> None:
        if action.authority_envelope_id != authorization.authority.envelope_id:
            raise ValueError("authorizer authority does not match proposed effect binding")
        if authorization.clearance.action_digest != action.digest:
            raise ValueError("authorizer clearance is not bound to exact proposed effect")
        if authorization.clearance.authority_envelope_id != authorization.authority.envelope_id:
            raise ValueError("authorizer returned mismatched authority and clearance")
        if authorization.permit is not None:
            if authorization.permit.action_digest != action.digest:
                raise ValueError("authorizer permit is not bound to exact proposed effect")
            if authorization.permit.authority_envelope_id != authorization.authority.envelope_id:
                raise ValueError("authorizer returned mismatched authority and permit")
            if authorization.permit.clearance_id != authorization.clearance.clearance_id:
                raise ValueError("authorizer returned mismatched clearance and permit")
