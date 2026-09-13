import json
from vaig.digest import canonical_digest
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

# ============================================================
# REFUSAL RESOLUTION PROTOCOL (RRP) — Core Schema & State Machine
# ============================================================

class RefusalCategory(Enum):
    POLICY_VIOLATION = "policy_violation"
    SAFETY_BOUNDARY = "safety_boundary"
    CAPABILITY_LIMIT = "capability_limit"
    JURISDICTIONAL_LIMIT = "jurisdictional_limit"
    EPISTEMIC_UNCERTAINTY = "epistemic_uncertainty"
    SYSTEM_INTEGRITY = "system_integrity"


class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionState(Enum):
    EMITTED = "emitted"
    ENRICHED = "enriched"
    ROUTED = "routed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    RESCOPED = "rescoped"
    REJECTED = "rejected"
    RESOLVED = "resolved"
    TERMINATED = "terminated"


class AuthorityDecision(Enum):
    APPROVE = "approve"
    RESCOPE = "rescope"
    REJECT = "reject"
    ESCALATE = "escalate"
    TERMINATE = "terminate"


@dataclass
class RefusalEvent:
    refusal_id: str
    timestamp: str
    category: RefusalCategory
    severity: SeverityLevel
    triggered_rule: str
    operator_id: str
    session_id: str
    input_summary: str
    rationale: str
    permitted_actions: List[str]
    model_state_digest: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        data = asdict(self)
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        return data


@dataclass
class UncertaintyInventory:
    refusal_id: str
    unresolved_questions: List[str]
    missing_evidence: List[str]
    ambiguity_sources: List[str]
    confidence_notes: str
    context_integrity_status: str
    risk_if_ignored: str

    def to_dict(self):
        return asdict(self)


@dataclass
class AuthorityAssignment:
    refusal_id: str
    authority_role: str
    authority_id: str
    scope_of_authority: List[str]
    decision_latency_sla: str
    permitted_decisions: List[AuthorityDecision]
    assignment_rationale: str

    def to_dict(self):
        data = asdict(self)
        data["permitted_decisions"] = [d.value for d in self.permitted_decisions]
        return data


@dataclass
class AccountabilityThreadEntry:
    entry_id: str
    timestamp: str
    actor_type: str
    actor_id: str
    action: str
    rationale: str
    linked_state: ResolutionState
    payload_hash: str

    def to_dict(self):
        data = asdict(self)
        data["linked_state"] = self.linked_state.value
        return data


@dataclass
class AccountabilityThread:
    thread_id: str
    refusal_id: str
    entries: List[AccountabilityThreadEntry] = field(default_factory=list)

    def append(self, entry: AccountabilityThreadEntry):
        self.entries.append(entry)

    def to_dict(self):
        return {
            "thread_id": self.thread_id,
            "refusal_id": self.refusal_id,
            "entries": [entry.to_dict() for entry in self.entries]
        }


class RefusalLifecycle:
    """
    Stateful controller for refusal-to-action handling.
    Enforces valid transitions and logs every state change.
    """

    VALID_TRANSITIONS = {
        ResolutionState.EMITTED: [ResolutionState.ENRICHED, ResolutionState.TERMINATED],
        ResolutionState.ENRICHED: [ResolutionState.ROUTED, ResolutionState.RESOLVED, ResolutionState.TERMINATED],
        ResolutionState.ROUTED: [ResolutionState.UNDER_REVIEW, ResolutionState.RESOLVED, ResolutionState.TERMINATED],
        ResolutionState.UNDER_REVIEW: [
            ResolutionState.APPROVED,
            ResolutionState.RESCOPED,
            ResolutionState.REJECTED,
            ResolutionState.TERMINATED,
        ],
        ResolutionState.APPROVED: [ResolutionState.RESOLVED],
        ResolutionState.RESCOPED: [ResolutionState.RESOLVED],
        ResolutionState.REJECTED: [ResolutionState.RESOLVED],
        ResolutionState.RESOLVED: [],
        ResolutionState.TERMINATED: [],
    }

    def __init__(self, refusal_event: RefusalEvent):
        self.refusal_event = refusal_event
        self.state = ResolutionState.EMITTED
        self.uncertainty_inventory: Optional[UncertaintyInventory] = None
        self.authority_assignment: Optional[AuthorityAssignment] = None
        self.accountability_thread = AccountabilityThread(
            thread_id=f"thread-{refusal_event.refusal_id}",
            refusal_id=refusal_event.refusal_id,
        )
        self._log_state_change(
            actor_type="system",
            actor_id="vaig",
            action="refusal_emitted",
            rationale=refusal_event.rationale,
        )

    def transition_to(self, new_state: ResolutionState, actor_type: str, actor_id: str, action: str, rationale: str):
        if new_state not in self.VALID_TRANSITIONS[self.state]:
            raise ValueError(f"Invalid transition from {self.state.value} to {new_state.value}")
        self.state = new_state
        self._log_state_change(actor_type, actor_id, action, rationale)

    def enrich(self, inventory: UncertaintyInventory):
        self.uncertainty_inventory = inventory
        self.transition_to(
            ResolutionState.ENRICHED,
            actor_type="system",
            actor_id="rrp_enrichment_service",
            action="uncertainty_inventory_created",
            rationale="Residual uncertainty mapped after refusal.",
        )

    def route(self, assignment: AuthorityAssignment):
        self.authority_assignment = assignment
        self.transition_to(
            ResolutionState.ROUTED,
            actor_type="system",
            actor_id="rrp_router",
            action="authority_assigned",
            rationale=assignment.assignment_rationale,
        )

    def start_review(self, reviewer_id: str):
        self.transition_to(
            ResolutionState.UNDER_REVIEW,
            actor_type="authority",
            actor_id=reviewer_id,
            action="review_started",
            rationale="Authority review initiated.",
        )

    def decide(self, reviewer_id: str, decision: AuthorityDecision, rationale: str):
        decision_to_state = {
            AuthorityDecision.APPROVE: ResolutionState.APPROVED,
            AuthorityDecision.RESCOPE: ResolutionState.RESCOPED,
            AuthorityDecision.REJECT: ResolutionState.REJECTED,
            AuthorityDecision.TERMINATE: ResolutionState.TERMINATED,
        }
        if decision not in decision_to_state:
            raise ValueError("ESCALATE requires separate routing logic.")
        self.transition_to(
            decision_to_state[decision],
            actor_type="authority",
            actor_id=reviewer_id,
            action=f"decision_{decision.value}",
            rationale=rationale,
        )

    def resolve(self, actor_id: str, rationale: str):
        self.transition_to(
            ResolutionState.RESOLVED,
            actor_type="system",
            actor_id=actor_id,
            action="lifecycle_resolved",
            rationale=rationale,
        )

    def _log_state_change(self, actor_type: str, actor_id: str, action: str, rationale: str):
        payload = {
            "state": self.state.value,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "rationale": rationale,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        entry = AccountabilityThreadEntry(
            entry_id=f"entry-{len(self.accountability_thread.entries)+1}",
            timestamp=payload["timestamp"],
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            rationale=rationale,
            linked_state=self.state,
            payload_hash=canonical_digest(payload),
        )
        self.accountability_thread.append(entry)

    def export(self):
        return {
            "refusal_event": self.refusal_event.to_dict(),
            "current_state": self.state.value,
            "uncertainty_inventory": self.uncertainty_inventory.to_dict() if self.uncertainty_inventory else None,
            "authority_assignment": self.authority_assignment.to_dict() if self.authority_assignment else None,
            "accountability_thread": self.accountability_thread.to_dict(),
        }


# ============================================================
# Example End-to-End Flow
# ============================================================

if __name__ == "__main__":
    refusal = RefusalEvent(
        refusal_id="ref-2026-0001",
        timestamp=datetime.now(timezone.utc).isoformat(),
        category=RefusalCategory.SAFETY_BOUNDARY,
        severity=SeverityLevel.HIGH,
        triggered_rule="VAIG-SAFETY-VOICE-IMPERSONATION",
        operator_id="operator-17",
        session_id="session-8831",
        input_summary="Request attempted to generate synthetic voice resembling enrolled executive speaker.",
        rationale="Voice similarity exceeded threshold and no consent token was present.",
        permitted_actions=["rescope", "escalate", "halt"],
        model_state_digest="sha256:abc123",
    )

    lifecycle = RefusalLifecycle(refusal)

    inventory = UncertaintyInventory(
        refusal_id=refusal.refusal_id,
        unresolved_questions=[
            "Is this a legitimate training simulation?",
            "Does the operator have consent documentation?",
        ],
        missing_evidence=["speaker_consent_token", "training_context_id"],
        ambiguity_sources=["operator_intent", "speaker_identity_match"],
        confidence_notes="Voice match score exceeded 0.92 threshold.",
        context_integrity_status="clean_context_no_prompt_injection_detected",
        risk_if_ignored="Unauthorized synthetic impersonation risk.",
    )
    lifecycle.enrich(inventory)

    assignment = AuthorityAssignment(
        refusal_id=refusal.refusal_id,
        authority_role="Boundary Override Authority",
        authority_id="boa-safety-01",
        scope_of_authority=["voice_synthesis", "executive_identity", "training_simulation"],
        decision_latency_sla="15m",
        permitted_decisions=[AuthorityDecision.APPROVE, AuthorityDecision.RESCOPE, AuthorityDecision.REJECT, AuthorityDecision.TERMINATE],
        assignment_rationale="High-severity safety refusal requires BOA safety review.",
    )
    lifecycle.route(assignment)
    lifecycle.start_review("boa-safety-01")
    lifecycle.decide("boa-safety-01", AuthorityDecision.REJECT, "Consent token absent; request cannot continue.")
    lifecycle.resolve("rrp_lifecycle_service", "Refusal resolved by rejection and audit closure.")

    print(json.dumps(lifecycle.export(), indent=2))
