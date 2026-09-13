"""Deterministic micro-REHT V1 authorization at the edge execution boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from typing import Any, Dict, Mapping, Optional

from valo_edge.contracts import (
    ConsequenceDecision,
    EdgeActionCommitmentV1,
    EdgeClearanceV1,
    EdgeEvidenceV1,
    SignatureV1,
    canonical_json_bytes,
    sha256_digest,
)
from valo_edge.runtime.contracts_v1 import (
    OfflineAuthorityEnvelopeV1,
    ParameterRuleV1,
    ParameterValueType,
    PermitStateV1,
    StatePredicateOperator,
    StatePredicateV1,
    MicroRehtStateV1,
)


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _hmac_signature(payload: Dict[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical_json_bytes(payload), hashlib.sha256).hexdigest()


def sign_authority_envelope_hmac(
    envelope: OfflineAuthorityEnvelopeV1,
    key: bytes,
) -> OfflineAuthorityEnvelopeV1:
    signature = SignatureV1(
        algorithm="HMAC-SHA256",
        key_id=envelope.signer_key_id,
        signature=_hmac_signature(envelope.signed_payload(), key),
    )
    return envelope.model_copy(update={"signature": signature})


class HmacAuthorityVerifier:
    """Small deterministic verifier for signed offline authority envelopes."""

    def __init__(self, keyring: Mapping[str, bytes]) -> None:
        self._keyring = dict(keyring)

    def verify(self, envelope: OfflineAuthorityEnvelopeV1) -> bool:
        signature = envelope.signature
        if signature is None or signature.algorithm != "HMAC-SHA256":
            return False
        if signature.key_id != envelope.signer_key_id:
            return False
        key = self._keyring.get(signature.key_id)
        if key is None:
            return False
        expected = _hmac_signature(envelope.signed_payload(), key)
        return hmac.compare_digest(signature.signature, expected)


def _lookup_path(payload: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _value_type_matches(value: Any, expected: ParameterValueType) -> bool:
    if expected == ParameterValueType.NUMBER:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == ParameterValueType.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == ParameterValueType.STRING:
        return isinstance(value, str)
    if expected == ParameterValueType.BOOLEAN:
        return isinstance(value, bool)
    if expected == ParameterValueType.OBJECT:
        return isinstance(value, dict)
    return False


def _parameter_rule_matches(value: Any, rule: ParameterRuleV1) -> bool:
    if rule.value_type is not None and not _value_type_matches(value, rule.value_type):
        return False
    if rule.allowed_values is not None and value not in rule.allowed_values:
        return False
    if rule.minimum is not None:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < rule.minimum:
            return False
    if rule.maximum is not None:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value > rule.maximum:
            return False
    return True


def _predicate_matches(state: Mapping[str, Any], predicate: StatePredicateV1) -> bool:
    present, actual = _lookup_path(state, predicate.path)
    if not present:
        return False
    expected = predicate.expected
    if predicate.operator == StatePredicateOperator.EQ:
        return actual == expected
    if predicate.operator == StatePredicateOperator.NE:
        return actual != expected
    if predicate.operator == StatePredicateOperator.LT:
        return actual < expected
    if predicate.operator == StatePredicateOperator.LTE:
        return actual <= expected
    if predicate.operator == StatePredicateOperator.GT:
        return actual > expected
    if predicate.operator == StatePredicateOperator.GTE:
        return actual >= expected
    if predicate.operator == StatePredicateOperator.IN:
        return actual in expected
    if predicate.operator == StatePredicateOperator.NOT_IN:
        return actual not in expected
    return False


class MicroRehtV1:
    """Fail-closed deterministic authorization using explicit authority and evidence."""

    def __init__(
        self,
        *,
        authority_verifier: HmacAuthorityVerifier,
        state: Optional[MicroRehtStateV1] = None,
        signer_key_id: str = "micro-reht-local",
        halt_recovery_digest: Optional[str] = None,
    ) -> None:
        self.authority_verifier = authority_verifier
        self.state = state or MicroRehtStateV1()
        self.signer_key_id = signer_key_id
        self.halt_recovery_digest = halt_recovery_digest

    def snapshot_state(self) -> MicroRehtStateV1:
        return self.state.model_copy(deep=True)

    def trigger_halt(self, reason: str, at_iso: str) -> None:
        self.state.halted = True
        self.state.halt_reason = reason
        self.state.halt_at_iso = at_iso

    def clear_halt(self, recovery_attestation_digest: str) -> bool:
        if not self.halt_recovery_digest:
            return False
        if not hmac.compare_digest(recovery_attestation_digest, self.halt_recovery_digest):
            return False
        self.state.halted = False
        self.state.halt_reason = ""
        self.state.halt_at_iso = None
        return True

    def consume_permit(self, permit_id: str, proposal_digest: str) -> bool:
        if self.state.halted:
            return False
        permit = self.state.issued_permits.get(permit_id)
        if permit is None or permit.proposal_digest != proposal_digest or permit.remaining_uses <= 0:
            return False
        permit.remaining_uses -= 1
        return True

    def evaluate(
        self,
        proposal: EdgeActionCommitmentV1,
        evidence: EdgeEvidenceV1,
        envelope: OfflineAuthorityEnvelopeV1,
        *,
        now_iso: str,
        prior_clearance: Optional[EdgeClearanceV1] = None,
    ) -> EdgeClearanceV1:
        now = _parse_iso(now_iso)
        proposal_digest = proposal.compute_digest()
        evidence_digest = evidence.compute_digest()
        envelope_digest = envelope.compute_digest()

        def clearance(
            decision: ConsequenceDecision,
            reason_codes: list[str],
            *,
            permit_id: Optional[str] = None,
            permit_uses: int = 0,
        ) -> EdgeClearanceV1:
            clearance_id = "clearance-" + sha256_digest(
                {
                    "proposal_digest": proposal_digest,
                    "evidence_digest": evidence_digest,
                    "envelope_digest": envelope_digest,
                    "decision": decision.value,
                    "now_iso": now_iso,
                }
            ).split(":", 1)[1][:16]
            return EdgeClearanceV1(
                clearance_id=clearance_id,
                proposal_digest=proposal_digest,
                evidence_digest=evidence_digest,
                authority_envelope_digest=envelope_digest,
                decision=decision,
                reason_codes=reason_codes,
                issued_at_iso=now_iso,
                valid_until_iso=min(proposal.valid_until_iso, envelope.valid_until_iso),
                boot_epoch=proposal.boot_epoch,
                sequence=proposal.sequence,
                permit_id=permit_id,
                permit_uses=permit_uses,
                signer_key_id=self.signer_key_id,
            )

        if self.state.halted:
            return clearance(
                ConsequenceDecision.HALT,
                ["PERSISTENT_HALT", self.state.halt_reason or "HALT_ACTIVE"],
            )

        if prior_clearance is not None and prior_clearance.decision != ConsequenceDecision.ALLOW:
            return clearance(
                prior_clearance.decision,
                [*prior_clearance.reason_codes, "PRIOR_DECISION_PRESERVED"],
            )

        if not self.authority_verifier.verify(envelope):
            return clearance(ConsequenceDecision.DENY, ["AUTHORITY_SIGNATURE_INVALID"])

        if proposal.authority_envelope_digest != envelope_digest:
            return clearance(ConsequenceDecision.DENY, ["AUTHORITY_COMMITMENT_MISMATCH"])

        if envelope.revoked:
            return clearance(ConsequenceDecision.DENY, ["AUTHORITY_REVOKED"])

        if now < _parse_iso(envelope.valid_from_iso) or now > _parse_iso(envelope.valid_until_iso):
            return clearance(ConsequenceDecision.DENY, ["AUTHORITY_EXPIRED_OR_NOT_YET_VALID"])

        if now < _parse_iso(proposal.issued_at_iso) or now > _parse_iso(proposal.valid_until_iso):
            return clearance(ConsequenceDecision.DENY, ["PROPOSAL_EXPIRED_OR_NOT_YET_VALID"])

        if evidence.proposal_digest != proposal_digest:
            return clearance(ConsequenceDecision.DENY, ["EVIDENCE_PROPOSAL_MISMATCH"])

        if evidence.contradictions:
            return clearance(ConsequenceDecision.DENY, ["EVIDENCE_CONTRADICTORY"])

        if not evidence.completeness:
            return clearance(ConsequenceDecision.DEFER, ["EVIDENCE_INCOMPLETE"])

        if evidence.freshness_ms > envelope.max_freshness_ms:
            return clearance(ConsequenceDecision.DENY, ["EVIDENCE_STALE"])

        if envelope.device_id != proposal.device_id:
            return clearance(ConsequenceDecision.DENY, ["DEVICE_SCOPE_MISMATCH"])

        if proposal.action_type not in envelope.allowed_action_types:
            return clearance(ConsequenceDecision.DENY, ["ACTION_NOT_AUTHORIZED"])

        if proposal.firmware_hash != envelope.required_firmware_hash:
            return clearance(ConsequenceDecision.DENY, ["FIRMWARE_NOT_AUTHORIZED"])
        if evidence.firmware_hash != proposal.firmware_hash:
            return clearance(ConsequenceDecision.DENY, ["FIRMWARE_EVIDENCE_MISMATCH"])

        if proposal.runtime_hash != envelope.required_runtime_hash:
            return clearance(ConsequenceDecision.DENY, ["RUNTIME_NOT_AUTHORIZED"])
        if evidence.runtime_hash != proposal.runtime_hash:
            return clearance(ConsequenceDecision.DENY, ["RUNTIME_EVIDENCE_MISMATCH"])

        if envelope.required_model_hash is not None:
            if proposal.model_hash != envelope.required_model_hash:
                return clearance(ConsequenceDecision.DENY, ["MODEL_NOT_AUTHORIZED"])
            if evidence.model_hash != proposal.model_hash:
                return clearance(ConsequenceDecision.DENY, ["MODEL_EVIDENCE_MISMATCH"])
        elif evidence.model_hash != proposal.model_hash:
            return clearance(ConsequenceDecision.DENY, ["MODEL_EVIDENCE_MISMATCH"])

        sensor_ids = {source.split("@", 1)[0] for source in evidence.sensor_sources}
        if not set(envelope.required_sensor_sources).issubset(sensor_ids):
            return clearance(ConsequenceDecision.DEFER, ["REQUIRED_SENSOR_EVIDENCE_MISSING"])

        physical_state = evidence.observed_state.get("physical", {})
        if not isinstance(physical_state, Mapping):
            return clearance(ConsequenceDecision.DENY, ["PHYSICAL_STATE_INVALID"])
        for predicate in envelope.state_predicates:
            try:
                matches = _predicate_matches(physical_state, predicate)
            except (TypeError, ValueError):
                matches = False
            if not matches:
                return clearance(ConsequenceDecision.DENY, [f"STATE_PREDICATE_FAILED:{predicate.path}"])

        for name, rule in envelope.parameter_rules.items():
            if name not in proposal.parameters:
                if rule.required:
                    return clearance(ConsequenceDecision.DENY, [f"PARAMETER_REQUIRED:{name}"])
                continue
            if not _parameter_rule_matches(proposal.parameters[name], rule):
                return clearance(ConsequenceDecision.DENY, [f"PARAMETER_OUT_OF_SCOPE:{name}"])

        if not envelope.allow_unruled_parameters:
            extras = set(proposal.parameters) - set(envelope.parameter_rules)
            if extras:
                return clearance(
                    ConsequenceDecision.DENY,
                    [f"UNRULED_PARAMETER:{name}" for name in sorted(extras)],
                )

        previous_digest = self.state.seen_nonce_digests.get(proposal.nonce)
        if previous_digest is not None:
            reason = "PROPOSAL_REPLAY" if previous_digest == proposal_digest else "PROPOSAL_MUTATION"
            return clearance(ConsequenceDecision.DENY, [reason])

        last_sequence = self.state.last_sequence_by_boot.get(proposal.boot_epoch)
        if last_sequence is not None and proposal.sequence <= last_sequence:
            return clearance(ConsequenceDecision.DENY, ["SEQUENCE_REPLAY"])

        budgets = envelope.budgets
        used = self.state.envelope_use_count.get(envelope.envelope_id, 0)
        if used >= budgets.max_uses:
            return clearance(ConsequenceDecision.DENY, ["USE_BUDGET_EXHAUSTED"])
        remaining_envelope_uses = budgets.max_uses - used
        permit_uses = min(budgets.permit_uses, remaining_envelope_uses)

        action_times = self.state.envelope_action_times.get(envelope.envelope_id, [])
        if budgets.max_actions_per_window is not None:
            if budgets.window_seconds is None:
                return clearance(ConsequenceDecision.DENY, ["RATE_WINDOW_INVALID"])
            window_start = now - timedelta(seconds=budgets.window_seconds)
            action_times = [
                timestamp
                for timestamp in action_times
                if _parse_iso(timestamp) >= window_start
            ]
            if len(action_times) + permit_uses > budgets.max_actions_per_window:
                return clearance(ConsequenceDecision.DENY, ["RATE_BUDGET_EXHAUSTED"])

        energy = 0.0
        if budgets.max_energy_j is not None:
            raw_energy = proposal.parameters.get(budgets.energy_parameter)
            if not isinstance(raw_energy, (int, float)) or isinstance(raw_energy, bool) or raw_energy < 0:
                return clearance(ConsequenceDecision.DENY, ["ENERGY_BUDGET_INPUT_INVALID"])
            energy = float(raw_energy)
            if (
                self.state.envelope_energy_used.get(envelope.envelope_id, 0.0)
                + energy * permit_uses
                > budgets.max_energy_j
            ):
                return clearance(ConsequenceDecision.DENY, ["ENERGY_BUDGET_EXHAUSTED"])

        if budgets.max_duration_ms is not None:
            duration = proposal.parameters.get(budgets.duration_parameter)
            if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
                return clearance(ConsequenceDecision.DENY, ["DURATION_BUDGET_INPUT_INVALID"])
            if duration > budgets.max_duration_ms:
                return clearance(ConsequenceDecision.DENY, ["DURATION_BUDGET_EXCEEDED"])

        value = 0.0
        if budgets.max_value is not None:
            raw_value = proposal.parameters.get(budgets.value_parameter)
            if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool) or raw_value < 0:
                return clearance(ConsequenceDecision.DENY, ["VALUE_BUDGET_INPUT_INVALID"])
            value = float(raw_value)
            if (
                self.state.envelope_value_used.get(envelope.envelope_id, 0.0)
                + value * permit_uses
                > budgets.max_value
            ):
                return clearance(ConsequenceDecision.DENY, ["VALUE_BUDGET_EXHAUSTED"])
        permit_id = "permit-" + sha256_digest(
            {
                "envelope_id": envelope.envelope_id,
                "proposal_digest": proposal_digest,
                "sequence": proposal.sequence,
                "now_iso": now_iso,
            }
        ).split(":", 1)[1][:16]

        result = clearance(
            ConsequenceDecision.ALLOW,
            ["AUTHORITY_VALID", "EVIDENCE_VALID", "SCOPE_VALID", "BUDGET_VALID"],
            permit_id=permit_id,
            permit_uses=permit_uses,
        )

        self.state.seen_nonce_digests[proposal.nonce] = proposal_digest
        self.state.last_sequence_by_boot[proposal.boot_epoch] = proposal.sequence
        self.state.envelope_use_count[envelope.envelope_id] = used + permit_uses
        action_times.extend([now_iso] * permit_uses)
        self.state.envelope_action_times[envelope.envelope_id] = action_times
        if budgets.max_energy_j is not None:
            self.state.envelope_energy_used[envelope.envelope_id] = (
                self.state.envelope_energy_used.get(envelope.envelope_id, 0.0)
                + energy * permit_uses
            )
        if budgets.max_value is not None:
            self.state.envelope_value_used[envelope.envelope_id] = (
                self.state.envelope_value_used.get(envelope.envelope_id, 0.0)
                + value * permit_uses
            )
        self.state.issued_permits[permit_id] = PermitStateV1(
            permit_id=permit_id,
            envelope_id=envelope.envelope_id,
            proposal_digest=proposal_digest,
            remaining_uses=permit_uses,
        )
        return result


__all__ = [
    "HmacAuthorityVerifier",
    "MicroRehtV1",
    "sign_authority_envelope_hmac",
]
