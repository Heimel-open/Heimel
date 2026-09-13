"""
VACS Profile v0.1
VALO authority profile for ACS packets.
"""

from typing import Any, Dict, List

try:
    from .validator import ACSValidator
except ImportError:  # Direct execution from vacs/tests.
    from validator import ACSValidator


class VACSProfileValidationError(Exception):
    pass


class VACSProfileValidator:
    """
    Validates the VALO VACS profile extension around an ACS packet.

    ACS remains the baseline packet standard.
    VACS adds VALO authority semantics: who, whom, authority source,
    execution boundary and signoff consistency.
    """

    PROFILE_ID = "valo-authority-v0.1"

    def __init__(self):
        self.errors: List[str] = []
        self.acs_validator = ACSValidator()

    def validate(self, packet: Dict[str, Any]) -> bool:
        self.errors = []

        if not self.acs_validator.validate(packet):
            self.errors.extend([f"ACS: {error}" for error in self.acs_validator.get_errors()])
            return False

        profile = packet.get("vacs_profile")
        if profile is None:
            self.errors.append("Missing required VACS field: vacs_profile")
            return False

        if profile != self.PROFILE_ID:
            self.errors.append(f"Unsupported VACS profile: {profile}")

        self._validate_policy(packet.get("policy", {}))

        principal = packet.get("principal")
        if not isinstance(principal, dict):
            self.errors.append("Missing required VACS object: principal")
        else:
            self._validate_principal(principal, packet)

        boundary = packet.get("boundary")
        if not isinstance(boundary, dict):
            self.errors.append("Missing required VACS object: boundary")
        else:
            self._validate_boundary(boundary, packet)

        return len(self.errors) == 0

    def _validate_policy(self, policy: Dict[str, Any]) -> None:
        for field in ["policy_id", "policy_hash"]:
            if not policy.get(field):
                self.errors.append(f"VACS policy missing required field: {field}")

        policy_hash = policy.get("policy_hash", "")
        if policy_hash and not policy_hash.startswith("sha256:"):
            self.errors.append("VACS policy_hash must start with sha256:")

    def _validate_principal(self, principal: Dict[str, Any], packet: Dict[str, Any]) -> None:
        for field in ["who", "whom", "authority_source"]:
            if not principal.get(field):
                self.errors.append(f"Principal missing required field: {field}")

        if principal.get("who") and principal.get("who") != packet.get("agent_id"):
            self.errors.append("Principal who must match ACS agent_id")

        signoff = principal.get("human_signoff", {})
        if signoff and not isinstance(signoff, dict):
            self.errors.append("human_signoff must be an object")
            return

        policy_requires_signoff = packet.get("policy", {}).get("required_signoff", False)
        signoff_required = signoff.get("required", False)

        if policy_requires_signoff and not signoff_required:
            self.errors.append("Policy requires signoff but VACS human_signoff.required is not true")

        if signoff_required:
            for field in ["signer", "role", "signed_at", "signature", "authority_chain"]:
                if not signoff.get(field):
                    self.errors.append(f"Human signoff missing required field: {field}")

            authority_chain = signoff.get("authority_chain")
            if authority_chain is not None and (not isinstance(authority_chain, list) or not authority_chain):
                self.errors.append("Human signoff authority_chain must be a non-empty list")

            if signoff.get("status") == "revoked":
                self.errors.append("Human signoff has been revoked")

    def _validate_boundary(self, boundary: Dict[str, Any], packet: Dict[str, Any]) -> None:
        for field in ["when", "where", "resources", "forbidden_domains"]:
            if field not in boundary:
                self.errors.append(f"Boundary missing required field: {field}")

        resources = boundary.get("resources", [])
        if not isinstance(resources, list) or not resources:
            self.errors.append("Boundary resources must be a non-empty list")

        forbidden_domains = boundary.get("forbidden_domains", [])
        if not isinstance(forbidden_domains, list):
            self.errors.append("Boundary forbidden_domains must be a list")

        target = packet.get("intent", {}).get("target")
        if target and resources and target not in resources:
            self.errors.append("ACS intent target must be listed in VACS boundary resources")

        action = packet.get("intent", {}).get("action")
        if action in forbidden_domains:
            self.errors.append("ACS intent action is forbidden by VACS boundary")

    def get_errors(self) -> List[str]:
        return self.errors
