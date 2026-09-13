"""Fail-closed closure for relAIon capability proposals.

This is relAIon's domain adapter, not a replacement for VALO's generic
governance infrastructure.  It closes the mechanical claim that a governed
asset-pool proposal was produced with the bound scope; it does not claim that
an asset was booked, paid for, insured, or made accessible.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from paios.proposal import ActionEnvelope
from paios.relaion_asset_pool import PoolOffer, propose_pool_allocation


class ClosureState(str, Enum):
    COMPLETED_VERIFIED = "COMPLETED_VERIFIED"
    UNKNOWN = "UNKNOWN"
    FAIL = "FAIL"


ASSET_POOL_SCOPE = "relaion.asset_pool.governed_proposal.v1"
ASSET_POOL_EVIDENCE = (
    "offer_calculation",
    "proposal_envelope",
    "execution_fingerprint",
)


@dataclass(frozen=True)
class AcceptanceContract:
    capability: str
    need: str
    desired_effect: str
    acceptance_scope: str
    required_evidence: tuple[str, ...]
    canonical_integration_target: str

    def validate(self) -> tuple[str, ...]:
        errors = [
            name
            for name, value in (
                ("capability", self.capability),
                ("need", self.need),
                ("desired_effect", self.desired_effect),
                ("acceptance_scope", self.acceptance_scope),
                ("canonical_integration_target", self.canonical_integration_target),
            )
            if not value.strip()
        ]
        if not self.required_evidence:
            errors.append("required_evidence")
        return tuple(errors)


@dataclass(frozen=True)
class TypedClosureEvent:
    kind: str
    subject: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class VerificationResult:
    state: ClosureState
    reason: str
    verifier_id: str
    scope: str


@dataclass(frozen=True)
class ClosureRun:
    state: ClosureState
    contract: AcceptanceContract
    events: tuple[TypedClosureEvent, ...]
    verification: VerificationResult


def asset_pool_contract(*, canonical_target: str) -> AcceptanceContract:
    return AcceptanceContract(
        capability="relAIon.asset_pool.governed_proposal",
        need="identify an owner-safe, economically evaluated unused-capacity opportunity",
        desired_effect="produce a non-binding governed proposal without external effect",
        acceptance_scope=ASSET_POOL_SCOPE,
        required_evidence=ASSET_POOL_EVIDENCE,
        canonical_integration_target=canonical_target,
    )


def _fingerprint(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _stable_envelope(envelope: ActionEnvelope) -> dict[str, Any]:
    data = envelope.to_dict()
    data.pop("action_id", None)
    data.pop("created_at", None)
    return data


def verify_asset_pool_proposal(
    offer: PoolOffer,
    envelope: ActionEnvelope,
    contract: AcceptanceContract,
    *,
    verifier_id: str,
    builder_id: str,
    evidence: Mapping[str, Any],
) -> VerificationResult:
    """Independently recompute and exact-scope-check the proposal."""
    if verifier_id.strip() == builder_id.strip():
        return VerificationResult(ClosureState.UNKNOWN, "builder_self_verification", verifier_id, contract.acceptance_scope)
    if contract.validate():
        return VerificationResult(ClosureState.UNKNOWN, "invalid_contract", verifier_id, contract.acceptance_scope)
    if contract.acceptance_scope != ASSET_POOL_SCOPE:
        return VerificationResult(ClosureState.UNKNOWN, "scope_mismatch", verifier_id, contract.acceptance_scope)
    if tuple(evidence.get("required_evidence", ())) != contract.required_evidence:
        return VerificationResult(ClosureState.UNKNOWN, "evidence_scope_mismatch", verifier_id, contract.acceptance_scope)
    if evidence.get("execution_fingerprint") != _fingerprint(_stable_envelope(envelope)):
        return VerificationResult(ClosureState.FAIL, "execution_evidence_tampered", verifier_id, contract.acceptance_scope)

    expected = propose_pool_allocation(
        offer,
        actor_id=str(envelope.actor.get("id", "")),
        mandate_id=str(envelope.authority_context.get("mandate_id", "")),
        policy_id=str(envelope.policy_context.get("policy_id", "")),
    )
    if _stable_envelope(envelope) != _stable_envelope(expected):
        return VerificationResult(ClosureState.FAIL, "proposal_recomputation_mismatch", verifier_id, contract.acceptance_scope)
    return VerificationResult(ClosureState.COMPLETED_VERIFIED, "exact_scope_verified", verifier_id, contract.acceptance_scope)


def run_asset_pool_closure(
    offer: PoolOffer,
    *,
    contract: AcceptanceContract,
    actor_id: str,
    mandate_id: str,
    policy_id: str,
    builder_id: str,
    verifier_id: str,
    canonical_integration_ref: str,
) -> ClosureRun:
    """Run the complete relAIon proposal closure chain.

    Canonical integration is deliberately an input proof.  A local git
    checkout or a branch name is not accepted as proof of integration.
    """
    subject = offer.asset.asset_id
    events: list[TypedClosureEvent] = []
    if contract.validate():
        verification = VerificationResult(ClosureState.UNKNOWN, "invalid_contract", verifier_id, contract.acceptance_scope)
        return ClosureRun(ClosureState.UNKNOWN, contract, tuple(events), verification)
    if not canonical_integration_ref or not re.fullmatch(r"[^@\s]+@[0-9a-fA-F]{40}", canonical_integration_ref):
        verification = VerificationResult(ClosureState.UNKNOWN, "canonical_integration_proof_required", verifier_id, contract.acceptance_scope)
        return ClosureRun(ClosureState.UNKNOWN, contract, tuple(events), verification)

    events.append(TypedClosureEvent("need_bound", subject, {"need": contract.need}))
    events.append(TypedClosureEvent("contract_bound", subject, {"scope": contract.acceptance_scope, "evidence": contract.required_evidence}))
    events.append(TypedClosureEvent("implementation_bound", subject, {"capability": contract.capability}))
    envelope = propose_pool_allocation(offer, actor_id=actor_id, mandate_id=mandate_id, policy_id=policy_id)
    events.append(TypedClosureEvent("execution_observed", subject, {"action_type": envelope.action_type, "builder_id": builder_id}))
    evidence = {
        "required_evidence": contract.required_evidence,
        "offer_calculation": {"expected_net_yield": offer.expected_net_yield, "available_days": offer.available_days},
        "proposal_envelope": _stable_envelope(envelope),
        "execution_fingerprint": _fingerprint(_stable_envelope(envelope)),
    }
    events.append(TypedClosureEvent("evidence_emitted", subject, evidence))
    verification = verify_asset_pool_proposal(
        offer, envelope, contract, verifier_id=verifier_id, builder_id=builder_id, evidence=evidence
    )
    events.append(TypedClosureEvent("verification_recorded", subject, {"state": verification.state.value, "scope": verification.scope}))
    if verification.state is not ClosureState.COMPLETED_VERIFIED:
        return ClosureRun(verification.state, contract, tuple(events), verification)
    events.append(TypedClosureEvent("independent_sign_off", subject, {"authority": verifier_id}))
    events.append(TypedClosureEvent("canonical_integration", subject, {"ref": canonical_integration_ref}))
    return ClosureRun(ClosureState.COMPLETED_VERIFIED, contract, tuple(events), verification)
