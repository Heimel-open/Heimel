"""
VACS execution handoff boundary.

This module does not execute external side effects. It prepares a governed
handoff object only after an ACS/VACS packet has validated and the computed
ACS decision is ALLOW.

The handoff is provider-agnostic. GitHub, SAP, Salesforce, banking, ERP,
cloud and MCP tools should all cross the same authority boundary.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from .clearance import (
        ClearanceStatus,
        GovernanceClearance,
        verify_clearance,
    )
    from .hashlog import ACSHashLog
    from .policy_engine import ACSPolicyEngine, Decision
    from .profile import VACSProfileValidator
    from .receipt import ACSReceiptGenerator
    from .validator import ACSValidator
except ImportError:  # Direct execution from vacs/tests.
    from clearance import (
        ClearanceStatus,
        GovernanceClearance,
        verify_clearance,
    )
    from hashlog import ACSHashLog
    from policy_engine import ACSPolicyEngine, Decision
    from profile import VACSProfileValidator
    from receipt import ACSReceiptGenerator
    from validator import ACSValidator


# Evaluation verdict vs execution authority: VAIG evaluates, REHT clears.
# `Decision` from policy_engine is an EVALUATION/RECOMMENDATION only and must
# never be treated as execution authority on its own.
EVALUATION_ONLY_DECISIONS = {d.value for d in Decision}


class ExecutionStatus(Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class ExecutionBlockReason(Enum):
    VALIDATION_FAILED = "validation_failed"
    DECISION_MISMATCH = "decision_mismatch"
    DECISION_NOT_ALLOW = "decision_not_allow"
    PROVIDER_MISMATCH = "provider_mismatch"
    NO_REHT_CLEARANCE = "no_reht_clearance"
    CLEARANCE_INVALID = "clearance_invalid"


class ExecutionHandoffAdapter:
    """
    Converts a governed ACS/VACS packet into an execution handoff.

    The adapter is intentionally a boundary object. It consumes identity,
    authority, evidence, policy and risk from the packet. It does not become
    an identity provider, policy engine or external system client.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        acs_validator: Optional[ACSValidator] = None,
        vacs_validator: Optional[VACSProfileValidator] = None,
        policy_engine: Optional[ACSPolicyEngine] = None,
        receipt_generator: Optional[ACSReceiptGenerator] = None,
        hash_log: Optional[ACSHashLog] = None,
    ):
        self.provider = provider
        self.acs_validator = acs_validator or ACSValidator()
        self.vacs_validator = vacs_validator or VACSProfileValidator()
        self.policy_engine = policy_engine or ACSPolicyEngine()
        self.receipt_generator = receipt_generator or ACSReceiptGenerator()
        self.hash_log = hash_log or ACSHashLog()

    def prepare(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a governed handoff or return a blocked governance result."""
        validation_errors = self._validate(packet)
        provider = self._provider(packet)

        if validation_errors:
            return self._blocked(
                packet=packet,
                decision=Decision.HALT,
                reason=ExecutionBlockReason.VALIDATION_FAILED,
                details=validation_errors,
                provider=provider,
            )

        computed_decision = self.policy_engine.evaluate(packet)
        declared_decision = packet.get("decision")
        if declared_decision != computed_decision.value:
            return self._blocked(
                packet=packet,
                decision=computed_decision,
                reason=ExecutionBlockReason.DECISION_MISMATCH,
                details=[
                    f"packet decision {declared_decision} does not match computed decision {computed_decision.value}"
                ],
                provider=provider,
            )

        if self.provider and provider != self.provider:
            return self._blocked(
                packet=packet,
                decision=computed_decision,
                reason=ExecutionBlockReason.PROVIDER_MISMATCH,
                details=[f"packet provider {provider} does not match adapter provider {self.provider}"],
                provider=provider,
            )

        # VAIG EVALUATES; REHT CLEARS. A VAIG-local ALLOW is an evaluation
        # verdict only — it is NOT execution authority. The execution boundary
        # MUST hold a verified REHT GovernanceClearance before READY is possible.
        if computed_decision != Decision.ALLOW:
            return self._blocked(
                packet=packet,
                decision=computed_decision,
                reason=ExecutionBlockReason.DECISION_NOT_ALLOW,
                details=[f"execution requires ALLOW, got {computed_decision.value}"],
                provider=provider,
            )

        clearance = self._extract_clearance(packet)
        clearance_status = verify_clearance(clearance, packet)
        if clearance_status is not ClearanceStatus.VALID:
            return self._blocked(
                packet=packet,
                decision=computed_decision,
                reason=(
                    ExecutionBlockReason.NO_REHT_CLEARANCE
                    if clearance_status is ClearanceStatus.MISSING
                    else ExecutionBlockReason.CLEARANCE_INVALID
                ),
                details=[
                    f"REHT clearance required before READY; status={clearance_status.value}. "
                    "VAIG evaluation alone is not execution authority."
                ],
                provider=provider,
            )

        receipt = self.receipt_generator.generate(packet, computed_decision)
        log_entry = self.hash_log.append(receipt)

        return {
            "status": ExecutionStatus.READY.value,
            "provider": provider,
            "packet_id": packet.get("packet_id"),
            "decision": computed_decision.value,
            "evaluation": computed_decision.value,
            "reht_clearance_id": getattr(clearance, "clearance_id", None),
            "execution": self._execution_payload(packet, provider),
            "receipt": receipt,
            "audit": {
                "entry_hash": log_entry.get("entry_hash"),
                "previous_hash": log_entry.get("previous_hash"),
            },
        }

    def _extract_clearance(self, packet: Dict[str, Any]) -> "GovernanceClearance | None":
        """Extract a GovernanceClearance from the packet (or None).

        The clearance is supplied by the REHT clearance authority, not computed
        locally by VAIG. If the packet carries a ``reht_clearance`` dict it is
        coerced into the canonical structure; otherwise None (=> fail closed).
        """
        raw = packet.get("reht_clearance")
        if not raw:
            return None
        if isinstance(raw, GovernanceClearance):
            return raw
        try:
            return GovernanceClearance(**raw)
        except TypeError:
            return None

    def _validate(self, packet: Dict[str, Any]) -> List[str]:
        if packet.get("vacs_profile"):
            if self.vacs_validator.validate(packet):
                return []
            return self.vacs_validator.get_errors()

        if self.acs_validator.validate(packet):
            return []
        return self.acs_validator.get_errors()

    def _blocked(
        self,
        packet: Dict[str, Any],
        decision: Decision,
        reason: ExecutionBlockReason,
        details: List[str],
        provider: str,
    ) -> Dict[str, Any]:
        receipt = self.receipt_generator.generate(packet, decision)
        log_entry = self.hash_log.append(receipt)

        return {
            "status": ExecutionStatus.BLOCKED.value,
            "provider": provider,
            "packet_id": packet.get("packet_id"),
            "decision": decision.value,
            "block_reason": reason.value,
            "details": details,
            "receipt": receipt,
            "audit": {
                "entry_hash": log_entry.get("entry_hash"),
                "previous_hash": log_entry.get("previous_hash"),
            },
        }

    def _provider(self, packet: Dict[str, Any]) -> str:
        boundary = packet.get("boundary", {})
        method = boundary.get("execution_method", "external")
        return boundary.get("execution_provider") or method.split(":", 1)[0]

    def _execution_payload(self, packet: Dict[str, Any], provider: str) -> Dict[str, Any]:
        intent = packet.get("intent", {})
        principal = packet.get("principal", {})
        boundary = packet.get("boundary", {})

        return {
            "provider": provider,
            "method": boundary.get("execution_method", "external"),
            "target": intent.get("target"),
            "action": intent.get("action"),
            "scope": intent.get("scope"),
            "actor": principal.get("who", packet.get("agent_id")),
            "represented_party": principal.get("whom"),
            "authority_source": principal.get("authority_source"),
            "allowed_resources": boundary.get("resources", []),
            "where": boundary.get("where"),
            "when": boundary.get("when"),
        }


class GitHubExecutionHandoffAdapter(ExecutionHandoffAdapter):
    """Provider-specific convenience wrapper around the universal handoff."""

    def __init__(self, **kwargs):
        super().__init__(provider="github", **kwargs)
