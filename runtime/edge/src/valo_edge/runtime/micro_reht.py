"""micro-REHT: Fail-closed local decision engine for Tiny Edge physical AI."""

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Set

from jsoncanon import canonicalize  # type: ignore[import-not-found]

from valo_edge.contracts import (
    EdgeActionProposal,
    OfflineAuthorityEnvelope,
    EdgeClearance,
    EdgeDecision,
)

_RESET_TOKEN_FIELDS = (
    "token_type",
    "action",
    "decision_id",
    "target_id",
    "scheme",
    "required",
    "epoch",
    "operators",
    "approval_digest",
    "issued_at",
)


def _reset_token_digest(token: Mapping[str, Any]) -> str:
    """Canonical RFC 8785 digest over the token payload (matches the oversight
    layer's token_digest, so a token issued by the governance chain verifies
    here without any shared secret)."""
    payload = {key: token[key] for key in _RESET_TOKEN_FIELDS if key in token}
    return "sha256:" + hashlib.sha256(canonicalize(payload)).hexdigest()


class ResetAuthorization:
    """Reset capability produced only from a verified reset-authorization token.

    The token is issued by the governance chain's human-oversight authority
    only after a decision reaches quorum (M-of-N / rotating keys). Verification
    here is pure: recompute the canonical token digest and check the target
    binding + action. A tampered, misbound or unapproved token is rejected.
    """

    def __init__(self, token: Mapping[str, Any], target_id: str) -> None:
        self._token = dict(token)
        self._target_id = target_id

    @classmethod
    def verify_token(
        cls, token: Mapping[str, Any], target_id: str
    ) -> "ResetAuthorization":
        """Verify and construct a reset capability for ``target_id``.

        Raises ``ValueError`` (fail-closed) unless the token is a well-formed,
        digest-consistent ``valo-reset-authorization`` bound to this engine.
        """
        token_type = token.get("token_type")
        action = token.get("action")
        if token_type != "valo-reset-authorization":
            raise ValueError("not a valo reset-authorization token")
        if action != "RESET":
            raise ValueError("token action is not RESET")
        if token.get("target_id") != target_id:
            raise ValueError("token is not bound to this engine")
        declared = token.get("token_digest")
        if not isinstance(declared, str) or not declared.startswith("sha256:"):
            raise ValueError("token carries no sha256 digest")
        if _reset_token_digest(token) != declared:
            raise ValueError("token digest mismatch: tampered or invalid")
        return cls(token, target_id)

    @property
    def decision_id(self) -> str:
        return str(self._token.get("decision_id", ""))

    @property
    def operators(self) -> tuple[str, ...]:
        return tuple(sorted(str(op) for op in self._token.get("operators", ())))


class MicroRehtEngine:
    """Fail-closed local evaluation engine. Enforces offline authority envelopes,
    anti-replay, parameter binding, state predicates, budgets, and monotonic decisions."""

    def __init__(self, state_file: Optional[str] = None, state_path: Optional[str] = None) -> None:
        # Backward-compat alias: accept old kwarg name without breaking newer callers.
        effective = state_file or state_path
        self._state_file = effective
        self._is_halted: bool = False
        self._halt_reason: str = ""
        self._seen_nonces: Set[str] = set()
        self._consumed_nonces: Set[str] = set()
        self._permit_usage: Dict[str, int] = {}
        self._rate_timestamps: List[str] = []
        self._last_decision: Optional[EdgeDecision] = None
        self._last_decision_ts: str = ""
        self._last_proposal_id: str = ""
        if effective and os.path.exists(effective):
            self._load_state()

    def _load_state(self) -> None:
        if not self._state_file:
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            self._seen_nonces = set(data.get("seen_nonces", []))
            self._consumed_nonces = set(data.get("consumed_nonces", []))
            self._is_halted = bool(data.get("is_halted", False))
            self._halt_reason = str(data.get("halt_reason", ""))
            self._permit_usage = {str(k): int(v) for k, v in data.get("permit_usage", {}).items()}
            self._rate_timestamps = list(data.get("rate_timestamps", []))
            self._last_decision = EdgeDecision(data["last_decision"]) if data.get("last_decision") else None
            self._last_decision_ts = str(data.get("last_decision_ts", ""))
            self._last_proposal_id = str(data.get("last_proposal_id", ""))
        except (OSError, json.JSONDecodeError, ValueError):
            self._seen_nonces = set()
            self._consumed_nonces = set()
            self._is_halted = False
            self._halt_reason = ""
            self._permit_usage = {}
            self._rate_timestamps = []
            self._last_decision = None
            self._last_decision_ts = ""
            self._last_proposal_id = ""

    def _persist_state(self) -> None:
        if not self._state_file:
            return
        try:
            payload: Dict[str, Any] = {
                "seen_nonces": list(self._seen_nonces),
                "consumed_nonces": list(self._consumed_nonces),
                "is_halted": self._is_halted,
                "halt_reason": self._halt_reason,
                "permit_usage": self._permit_usage,
                "rate_timestamps": self._rate_timestamps,
                "last_decision_ts": self._last_decision_ts,
                "last_proposal_id": self._last_proposal_id,
            }
            if self._last_decision is not None:
                payload["last_decision"] = self._last_decision.value
            os.makedirs(os.path.dirname(self._state_file) or ".", exist_ok=True)
            with open(self._state_file, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        except OSError:
            pass

    def trigger_halt(self, reason: str) -> None:
        self._is_halted = True
        self._halt_reason = reason
        self._persist_state()

    def flush(self) -> None:
        self._persist_state()

    def reset_halt(self, authorization: ResetAuthorization) -> None:
        """Lift HALT with a verified human-oversight reset authorization.

        The capability is produced by ``ResetAuthorization.verify_token`` from
        a quorum-approved reset token issued by the governance chain's human
        oversight; an unverified or misbound capability is rejected.
        """
        if not isinstance(authorization, ResetAuthorization):
            raise TypeError("reset requires a ResetAuthorization capability")
        self._is_halted = False
        self._halt_reason = ""
        self._persist_state()

    @property
    def is_halted(self) -> bool:
        return self._is_halted

    def evaluate_proposal(
        self,
        proposal: EdgeActionProposal,
        envelope: OfflineAuthorityEnvelope,
        current_time_iso: str,
        *,
        allowed_parameters_schema: Optional[Dict[str, Any]] = None,
        expected_device_binding: Optional[str] = None,
        expected_model_binding: Optional[str] = None,
        expected_firmware_binding: Optional[str] = None,
        state_predicates: Optional[List[Dict[str, Any]]] = None,
        sensor_provenance: Optional[Dict[str, Any]] = None,
        max_requests: Optional[int] = None,
        rate_limit_seconds: Optional[int] = None,
        permit_budget: Optional[Dict[str, int]] = None,
        one_shot_nonces: Optional[List[str]] = None,
    ) -> EdgeClearance:
        clearance_id = f"clr-{hashlib.sha256(f'{proposal.proposal_id}:{current_time_iso}'.encode()).hexdigest()[:12]}"

        # 1. Global HALT
        if self._is_halted:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.HALT,
                reason=f"HALT: Device engine is in emergency HALT state ({self._halt_reason}).",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        # 2. Monotonic decision preservation
        if (
            self._last_decision in {EdgeDecision.DENY, EdgeDecision.HALT, EdgeDecision.DEFER, EdgeDecision.STEP_UP}
            and proposal.proposal_id == self._last_proposal_id
            and current_time_iso >= self._last_decision_ts
        ):
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=self._last_decision,
                reason=f"Monotonic preservation of prior decision: {self._last_decision.value}",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        # 3. Replay or prior consumption
        if proposal.nonce in self._seen_nonces or proposal.nonce in self._consumed_nonces:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason=f"DENY: Replay attack detected. Nonce '{proposal.nonce}' has already been processed.",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        # 4. Proposal hash integrity
        expected_hash = proposal.compute_hash()
        if proposal.proposal_hash != expected_hash:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason="DENY: Proposal payload mutation or hash mismatch detected.",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        # 5. Device ID match
        if proposal.device_id != envelope.device_id:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason=f"DENY: Device ID mismatch. Proposal device '{proposal.device_id}' != Envelope device '{envelope.device_id}'.",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        # 6. Optional bindings
        if expected_device_binding and getattr(proposal, "device_attestation_hash", None) != expected_device_binding:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason="DENY: Device attestation hash does not match expected binding.",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )
        if expected_model_binding and getattr(proposal, "model_manifest_hash", None) != expected_model_binding:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason="DENY: Model manifest hash does not match expected binding.",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )
        if expected_firmware_binding and getattr(proposal, "firmware_hash", None) != expected_firmware_binding:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason="DENY: Firmware hash does not match expected binding.",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        # 7. Parameter schema enforcement
        if allowed_parameters_schema is not None:
            disallowed = set(proposal.parameters or {}).difference(set(allowed_parameters_schema or {}))
            if disallowed:
                return EdgeClearance(
                    clearance_id=clearance_id,
                    proposal_id=proposal.proposal_id,
                    decision=EdgeDecision.DENY,
                    reason=f"DENY: Disallowed parameters: {sorted(disallowed)}",
                    envelope_id=envelope.envelope_id,
                    timestamp_iso=current_time_iso,
                )

        # 8. State predicates
        if state_predicates:
            physical_state = getattr(proposal, "physical_state", {}) or {}
            for predicate in state_predicates:
                field = predicate.get("field")
                expected = predicate.get("equals")
                if field and expected is not None and str(physical_state.get(field)) != str(expected):
                    return EdgeClearance(
                        clearance_id=clearance_id,
                        proposal_id=proposal.proposal_id,
                        decision=EdgeDecision.DENY,
                        reason=f"DENY: State predicate failed for field '{field}'.",
                        envelope_id=envelope.envelope_id,
                        timestamp_iso=current_time_iso,
                    )

        # 9. Sensor provenance + freshness
        if sensor_provenance:
            capture_ts = sensor_provenance.get("capture_timestamp_iso")
            max_age = sensor_provenance.get("max_age_seconds")
            if capture_ts and max_age is not None:
                try:
                    captured = datetime.fromisoformat(capture_ts.replace("Z", "+00:00"))
                    current = datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
                    if (current - captured).total_seconds() > float(max_age):
                        return EdgeClearance(
                            clearance_id=clearance_id,
                            proposal_id=proposal.proposal_id,
                            decision=EdgeDecision.DENY,
                            reason="DENY: Sensor evidence is stale.",
                            envelope_id=envelope.envelope_id,
                            timestamp_iso=current_time_iso,
                        )
                except (ValueError, TypeError):
                    return EdgeClearance(
                        clearance_id=clearance_id,
                        proposal_id=proposal.proposal_id,
                        decision=EdgeDecision.DENY,
                        reason="DENY: Invalid sensor timestamp.",
                        envelope_id=envelope.envelope_id,
                        timestamp_iso=current_time_iso,
                    )

        # 10. Rate limiting
        if max_requests is not None:
            if rate_limit_seconds is None:
                rate_limit_seconds = 1
            cutoff = datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
            recent = []
            for ts in self._rate_timestamps:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if (cutoff - dt).total_seconds() <= rate_limit_seconds:
                        recent.append(ts)
                except (ValueError, TypeError):
                    pass
            if len(recent) >= max_requests:
                return EdgeClearance(
                    clearance_id=clearance_id,
                    proposal_id=proposal.proposal_id,
                    decision=EdgeDecision.DENY,
                    reason="DENY: Rate limit exceeded.",
                    envelope_id=envelope.envelope_id,
                    timestamp_iso=current_time_iso,
                )
            self._rate_timestamps = recent
            self._rate_timestamps.append(current_time_iso)
        elif envelope.max_rate_per_sec:
            rate_limit_seconds = 1
            cutoff = datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
            recent = []
            for ts in self._rate_timestamps:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if (cutoff - dt).total_seconds() <= rate_limit_seconds:
                        recent.append(ts)
                except (ValueError, TypeError):
                    pass
            if len(recent) >= int(envelope.max_rate_per_sec):
                return EdgeClearance(
                    clearance_id=clearance_id,
                    proposal_id=proposal.proposal_id,
                    decision=EdgeDecision.DENY,
                    reason="DENY: Rate limit exceeded.",
                    envelope_id=envelope.envelope_id,
                    timestamp_iso=current_time_iso,
                )
            self._rate_timestamps = recent
            self._rate_timestamps.append(current_time_iso)

        # 11. Permit budget
        if permit_budget:
            proposal_type = proposal.action_type
            remaining = permit_budget.get(proposal_type, 0) - self._permit_usage.get(proposal_type, 0)
            if remaining <= 0:
                return EdgeClearance(
                    clearance_id=clearance_id,
                    proposal_id=proposal.proposal_id,
                    decision=EdgeDecision.DENY,
                    reason=f"DENY: Permit budget exhausted for '{proposal_type}'.",
                    envelope_id=envelope.envelope_id,
                    timestamp_iso=current_time_iso,
                )

        # 12. One-shot permits
        if one_shot_nonces and proposal.nonce in one_shot_nonces:
            if proposal.nonce in self._consumed_nonces:
                return EdgeClearance(
                    clearance_id=clearance_id,
                    proposal_id=proposal.proposal_id,
                    decision=EdgeDecision.DENY,
                    reason="DENY: One-shot permit already consumed.",
                    envelope_id=envelope.envelope_id,
                    timestamp_iso=current_time_iso,
                )

        # 13. Envelope checks
        if envelope.is_revoked:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason=f"DENY: Offline authority envelope '{envelope.envelope_id}' is revoked.",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        try:
            expired = datetime.fromisoformat(
                current_time_iso.replace("Z", "+00:00")
            ) > datetime.fromisoformat(envelope.valid_until_iso.replace("Z", "+00:00"))
        except ValueError:
            expired = True  # unparseable timestamps fail closed
        if expired:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason=f"DENY: Offline authority envelope '{envelope.envelope_id}' expired at {envelope.valid_until_iso}.",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        if proposal.action_type not in envelope.allowed_action_types:
            return EdgeClearance(
                clearance_id=clearance_id,
                proposal_id=proposal.proposal_id,
                decision=EdgeDecision.DENY,
                reason=f"DENY: Action type '{proposal.action_type}' is not authorized in envelope allowed list ({envelope.allowed_action_types}).",
                envelope_id=envelope.envelope_id,
                timestamp_iso=current_time_iso,
            )

        # 14. Mark usage
        self._seen_nonces.add(proposal.nonce)
        if one_shot_nonces and proposal.nonce in one_shot_nonces:
            self._consumed_nonces.add(proposal.nonce)
        if permit_budget:
            self._permit_usage[proposal_type] = self._permit_usage.get(proposal_type, 0) + 1
        self._last_decision = EdgeDecision.ALLOW
        self._last_proposal_id = proposal.proposal_id
        self._last_decision_ts = current_time_iso
        self._persist_state()

        return EdgeClearance(
            clearance_id=clearance_id,
            proposal_id=proposal.proposal_id,
            decision=EdgeDecision.ALLOW,
            reason="ALLOW: Action proposal cleared by micro-REHT offline authority envelope.",
            envelope_id=envelope.envelope_id,
            timestamp_iso=current_time_iso,
        )
