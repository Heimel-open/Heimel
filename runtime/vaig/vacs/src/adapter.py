"""
VACS adapter handoff v0.1.

This module does not execute external actions.
It builds the bounded handoff object an execution adapter may consume.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from .profile import VACSProfileValidator
    from .validator import ACSValidator
except ImportError:  # Direct execution from vacs/tests.
    from profile import VACSProfileValidator
    from validator import ACSValidator


class VACSExecutionHandoffError(Exception):
    pass


class VACSExecutionHandoffBuilder:
    """Builds a bounded execution handoff from a validated ACS/VACS packet."""

    SUPPORTED_ADAPTERS = {
        "github": {"methods": {"pull_request", "issue_comment", "workflow_dispatch"}},
        "generic_api": {"methods": {"POST", "PUT", "PATCH"}},
    }

    def __init__(self):
        self.errors: List[str] = []
        self.acs_validator = ACSValidator()
        self.vacs_validator = VACSProfileValidator()

    def build(
        self,
        packet: Dict[str, Any],
        adapter: str,
        method: str,
        receipt_path_available: bool = True,
    ) -> Dict[str, Any]:
        self.errors = []

        if packet.get("vacs_profile"):
            if not self.vacs_validator.validate(packet):
                self.errors.extend(self.vacs_validator.get_errors())
        elif not self.acs_validator.validate(packet):
            self.errors.extend(self.acs_validator.get_errors())

        if packet.get("decision") != "ALLOW":
            self.errors.append("Execution handoff requires decision == ALLOW")

        if not receipt_path_available:
            self.errors.append("Execution handoff requires an available receipt path")

        adapter_spec = self.SUPPORTED_ADAPTERS.get(adapter)
        if adapter_spec is None:
            self.errors.append(f"Unsupported execution adapter: {adapter}")
        elif method not in adapter_spec["methods"]:
            self.errors.append(f"Unsupported method for adapter {adapter}: {method}")

        if self.errors:
            raise VACSExecutionHandoffError("; ".join(self.errors))

        intent = packet.get("intent", {})
        boundary = packet.get("boundary", {})
        principal = packet.get("principal", {})

        return {
            "handoff_id": str(uuid.uuid4()),
            "handoff_version": "vacs-handoff-v0.1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "adapter": adapter,
            "method": method,
            "packet_id": packet.get("packet_id"),
            "agent_id": packet.get("agent_id"),
            "principal": {
                "who": principal.get("who", packet.get("agent_id")),
                "whom": principal.get("whom"),
                "authority_source": principal.get("authority_source"),
                "authority_reference": principal.get("authority_reference"),
            },
            "intent": {
                "action": intent.get("action"),
                "target": intent.get("target"),
                "scope": intent.get("scope"),
            },
            "boundary": {
                "when": boundary.get("when"),
                "where": boundary.get("where"),
                "resources": boundary.get("resources", [intent.get("target")]),
                "forbidden_domains": boundary.get("forbidden_domains", []),
                "execution_method": boundary.get("execution_method", method),
            },
            "decision": packet.get("decision"),
            "receipt_required": True,
        }

    def get_errors(self) -> List[str]:
        return self.errors
