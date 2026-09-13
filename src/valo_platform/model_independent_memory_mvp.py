"""Model-independent memory governance MVP for VALO.

This module proves the first runnable version of the principle:
models and agents are replaceable, while memory, policy and receipts remain stable.

It intentionally avoids external infrastructure. Storage is in-memory for the MVP so the
full flow can run in tests and CLI demos before Postgres/pgvector are wired in.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryDecisionAction(str, Enum):
    REMEMBER = "REMEMBER"
    FORGET = "FORGET"
    CONDENSE = "CONDENSE"
    QUARANTINE = "QUARANTINE"
    EXPIRE = "EXPIRE"
    PROMOTE_TO_SKILL = "PROMOTE_TO_SKILL"
    PROMOTE_TO_POLICY = "PROMOTE_TO_POLICY"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"


class ExecutionDecisionAction(str, Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


class MemoryCandidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant: str
    owner: str
    scope: str = "project"
    type: str
    content: str
    source: str
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.5
    classification: str = "internal"
    proposed_policy: str = "default_memory_policy"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class MemoryObject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant: str
    owner: str
    scope: str
    type: str
    content: str
    source: str
    evidence: List[str]
    confidence: float
    policy: str
    access_control: Dict[str, Any] = Field(default_factory=dict)
    classification: str = "internal"
    expiry: Optional[datetime] = None
    version: int = 1
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class MemoryDecision(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    candidate_id: str
    action: MemoryDecisionAction
    reason: str
    receipt_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ContextPackage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant: str
    owner: str
    task: str
    role: str
    risk: str
    model: str
    memory_ids: List[str]
    context: str
    constraints: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ActionIntent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant: str
    owner: str
    tool: str
    operation: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    risk: str = "low"
    requires_approval: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ExecutionDecision(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    intent_id: str
    action: ExecutionDecisionAction
    reason: str
    receipt_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Receipt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    event_type: str
    payload: Dict[str, Any]
    previous_hash: Optional[str] = None
    hash: str = ""

    def seal(self) -> "Receipt":
        body = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
        }
        canonical = json.dumps(body, sort_keys=True, default=str)
        self.hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return self


class ModelAdapter(Protocol):
    name: str

    def generate(self, prompt: str) -> str:
        ...

    def embed(self, text: str) -> List[float]:
        ...

    def tool_call(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def stream(self, prompt: str) -> Iterable[str]:
        ...


@dataclass
class MockModelAdapter:
    name: str

    def generate(self, prompt: str) -> str:
        return f"[{self.name}] continued with governed context: {prompt[:160]}"

    def embed(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [byte / 255.0 for byte in digest[:16]]

    def tool_call(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"tool": tool, "payload": payload, "model": self.name, "status": "mocked"}

    def stream(self, prompt: str) -> Iterable[str]:
        for token in self.generate(prompt).split():
            yield token


@dataclass
class ReceiptEngine:
    receipts: List[Receipt] = field(default_factory=list)

    def create(self, event_type: str, payload: Dict[str, Any]) -> Receipt:
        previous_hash = self.receipts[-1].hash if self.receipts else None
        receipt = Receipt(event_type=event_type, payload=payload, previous_hash=previous_hash).seal()
        self.receipts.append(receipt)
        return receipt

    def list(self) -> List[Receipt]:
        return list(self.receipts)


@dataclass
class CanonicalMemoryStore:
    memories: Dict[str, MemoryObject] = field(default_factory=dict)

    def add(self, memory: MemoryObject) -> MemoryObject:
        self.memories[memory.id] = memory
        return memory

    def list(self, tenant: Optional[str] = None, owner: Optional[str] = None) -> List[MemoryObject]:
        values = list(self.memories.values())
        if tenant is not None:
            values = [memory for memory in values if memory.tenant == tenant]
        if owner is not None:
            values = [memory for memory in values if memory.owner == owner]
        return values

    def get(self, memory_id: str) -> Optional[MemoryObject]:
        return self.memories.get(memory_id)


class LearningExtractor:
    """Extracts memory candidates from a session transcript.

    This MVP uses simple deterministic rules. Later versions can adopt Mem0,
    Mnemosyne or another extractor behind this interface.
    """

    FACT_PATTERNS = [r"remember that (?P<value>.+)", r"fact: (?P<value>.+)"]
    PREFERENCE_PATTERNS = [r"i prefer (?P<value>.+)", r"preference: (?P<value>.+)"]
    DECISION_PATTERNS = [r"decision: (?P<value>.+)", r"we decided (?P<value>.+)"]
    SKILL_PATTERNS = [r"skill: (?P<value>.+)", r"next time (?P<value>.+)"]

    def extract(self, transcript: str, tenant: str, owner: str, source: str) -> List[MemoryCandidate]:
        candidates: List[MemoryCandidate] = []
        for memory_type, patterns in {
            "fact": self.FACT_PATTERNS,
            "preference": self.PREFERENCE_PATTERNS,
            "decision": self.DECISION_PATTERNS,
            "skill": self.SKILL_PATTERNS,
        }.items():
            for pattern in patterns:
                for match in re.finditer(pattern, transcript, flags=re.IGNORECASE):
                    content = match.group("value").strip().rstrip(".")
                    candidates.append(
                        MemoryCandidate(
                            tenant=tenant,
                            owner=owner,
                            type=memory_type,
                            content=content,
                            source=source,
                            evidence=[source],
                            confidence=0.75,
                        )
                    )
        if not candidates and transcript.strip():
            candidates.append(
                MemoryCandidate(
                    tenant=tenant,
                    owner=owner,
                    type="lesson",
                    content="Condensed session summary: " + transcript.strip()[:500],
                    source=source,
                    evidence=[source],
                    confidence=0.45,
                    proposed_policy="review_before_remember",
                )
            )
        return candidates


@dataclass
class MemoryGate:
    store: CanonicalMemoryStore
    receipts: ReceiptEngine

    def decide(self, candidate: MemoryCandidate, force: Optional[MemoryDecisionAction] = None) -> MemoryDecision:
        action = force or self._default_decision(candidate)
        reason = self._reason(candidate, action)
        receipt = self.receipts.create(
            "memory_decision",
            {
                "candidate_id": candidate.id,
                "tenant": candidate.tenant,
                "owner": candidate.owner,
                "type": candidate.type,
                "action": action.value,
                "reason": reason,
                "source": candidate.source,
            },
        )
        decision = MemoryDecision(candidate_id=candidate.id, action=action, reason=reason, receipt_id=receipt.id)
        if action in {
            MemoryDecisionAction.REMEMBER,
            MemoryDecisionAction.CONDENSE,
            MemoryDecisionAction.PROMOTE_TO_SKILL,
            MemoryDecisionAction.PROMOTE_TO_POLICY,
        }:
            memory_type = candidate.type
            if action == MemoryDecisionAction.PROMOTE_TO_SKILL:
                memory_type = "skill"
            if action == MemoryDecisionAction.PROMOTE_TO_POLICY:
                memory_type = "policy"
            self.store.add(
                MemoryObject(
                    tenant=candidate.tenant,
                    owner=candidate.owner,
                    scope=candidate.scope,
                    type=memory_type,
                    content=candidate.content,
                    source=candidate.source,
                    evidence=candidate.evidence,
                    confidence=candidate.confidence,
                    policy=candidate.proposed_policy,
                    classification=candidate.classification,
                    access_control={"read": [candidate.owner], "write": ["memory_governance"]},
                    status="active",
                )
            )
        return decision

    def _default_decision(self, candidate: MemoryCandidate) -> MemoryDecisionAction:
        if candidate.classification in {"secret", "restricted"}:
            return MemoryDecisionAction.REQUIRE_HUMAN_APPROVAL
        if candidate.confidence < 0.5:
            return MemoryDecisionAction.QUARANTINE
        if candidate.type == "skill":
            return MemoryDecisionAction.PROMOTE_TO_SKILL
        if candidate.type == "policy":
            return MemoryDecisionAction.PROMOTE_TO_POLICY
        return MemoryDecisionAction.REMEMBER

    def _reason(self, candidate: MemoryCandidate, action: MemoryDecisionAction) -> str:
        if action == MemoryDecisionAction.REMEMBER:
            return "Candidate is useful, sufficiently confident, and not restricted."
        if action == MemoryDecisionAction.QUARANTINE:
            return "Candidate confidence is too low for canonical memory."
        if action == MemoryDecisionAction.REQUIRE_HUMAN_APPROVAL:
            return "Candidate contains restricted context and requires review."
        return f"Memory governance selected {action.value}."


@dataclass
class ContextComposer:
    store: CanonicalMemoryStore
    receipts: ReceiptEngine

    def compose(self, tenant: str, owner: str, task: str, role: str, risk: str, model: str, max_items: int = 5) -> ContextPackage:
        memories = self._select_memories(tenant, owner, task, max_items)
        context_lines = [f"Task: {task}", f"Role: {role}", f"Risk: {risk}", "Relevant governed memory:"]
        for memory in memories:
            context_lines.append(f"- ({memory.type}, v{memory.version}, confidence={memory.confidence:.2f}) {memory.content}")
        constraints = ["no_execution_without_governance", "use_only_included_memory"]
        package = ContextPackage(
            tenant=tenant,
            owner=owner,
            task=task,
            role=role,
            risk=risk,
            model=model,
            memory_ids=[memory.id for memory in memories],
            context="\n".join(context_lines),
            constraints=constraints,
        )
        self.receipts.create(
            "context_composed",
            {
                "context_package_id": package.id,
                "tenant": tenant,
                "owner": owner,
                "model": model,
                "memory_ids": package.memory_ids,
                "constraints": constraints,
            },
        )
        return package

    def _select_memories(self, tenant: str, owner: str, task: str, max_items: int) -> List[MemoryObject]:
        task_terms = {term.lower() for term in re.findall(r"[a-zA-Z0-9_]+", task)}
        scored = []
        for memory in self.store.list(tenant=tenant, owner=owner):
            content_terms = {term.lower() for term in re.findall(r"[a-zA-Z0-9_]+", memory.content)}
            overlap = len(task_terms.intersection(content_terms))
            scored.append((overlap, memory.confidence, memory.created_at, memory))
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [item[3] for item in scored[:max_items]]


@dataclass
class ModelRouter:
    adapters: Dict[str, ModelAdapter]
    receipts: ReceiptEngine

    def generate(self, model: str, context: ContextPackage) -> str:
        adapter = self.adapters[model]
        result = adapter.generate(context.context)
        self.receipts.create(
            "model_generation",
            {
                "model": model,
                "context_package_id": context.id,
                "memory_ids": context.memory_ids,
                "result_hash": hashlib.sha256(result.encode("utf-8")).hexdigest(),
            },
        )
        return result

    def switch_model(self, from_model: str, to_model: str, context: ContextPackage) -> str:
        self.receipts.create(
            "model_switch",
            {
                "from_model": from_model,
                "to_model": to_model,
                "context_package_id": context.id,
                "memory_ids": context.memory_ids,
            },
        )
        return self.generate(to_model, context)


@dataclass
class ExecutionGovernance:
    receipts: ReceiptEngine

    def evaluate(self, intent: ActionIntent) -> ExecutionDecision:
        if intent.requires_approval or intent.risk in {"high", "critical"}:
            action = ExecutionDecisionAction.STEP_UP
            reason = "Execution requires human approval before action."
        elif intent.tool in {"email.send", "payment.approve", "system.deploy"} and intent.risk != "low":
            action = ExecutionDecisionAction.STEP_UP
            reason = "Sensitive tool with elevated risk requires approval."
        else:
            action = ExecutionDecisionAction.ALLOW
            reason = "Intent passed MVP execution governance checks."
        receipt = self.receipts.create(
            "execution_decision",
            {
                "intent_id": intent.id,
                "tenant": intent.tenant,
                "owner": intent.owner,
                "tool": intent.tool,
                "operation": intent.operation,
                "risk": intent.risk,
                "decision": action.value,
                "reason": reason,
            },
        )
        return ExecutionDecision(intent_id=intent.id, action=action, reason=reason, receipt_id=receipt.id)


@dataclass
class ValoMemoryMVP:
    store: CanonicalMemoryStore = field(default_factory=CanonicalMemoryStore)
    receipts: ReceiptEngine = field(default_factory=ReceiptEngine)

    def __post_init__(self) -> None:
        self.extractor = LearningExtractor()
        self.memory_gate = MemoryGate(self.store, self.receipts)
        self.context_composer = ContextComposer(self.store, self.receipts)
        self.model_router = ModelRouter(
            adapters={
                "qwen_local": MockModelAdapter("qwen_local"),
                "claude_api": MockModelAdapter("claude_api"),
            },
            receipts=self.receipts,
        )
        self.execution_governance = ExecutionGovernance(self.receipts)

    def run_demo(self) -> Dict[str, Any]:
        transcript = (
            "Remember that VALO must keep memory outside the model. "
            "Preference: use local Qwen for low-risk drafts. "
            "Decision: all email.send actions require execution governance. "
            "Skill: when switching models, compose minimal context from canonical memory."
        )
        candidates = self.extractor.extract(transcript, tenant="demo", owner="njal", source="session_demo_001")
        decisions = [self.memory_gate.decide(candidate) for candidate in candidates]
        qwen_context = self.context_composer.compose(
            tenant="demo",
            owner="njal",
            task="continue VALO model independent memory work",
            role="architect",
            risk="medium",
            model="qwen_local",
        )
        qwen_result = self.model_router.generate("qwen_local", qwen_context)
        claude_result = self.model_router.switch_model("qwen_local", "claude_api", qwen_context)
        intent = ActionIntent(
            tenant="demo",
            owner="njal",
            tool="email.send",
            operation="send_external_message",
            payload={"recipient": "customer@example.com"},
            risk="medium",
            requires_approval=True,
        )
        execution_decision = self.execution_governance.evaluate(intent)
        return {
            "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
            "memory_decisions": [decision.model_dump(mode="json") for decision in decisions],
            "stored_memories": [memory.model_dump(mode="json") for memory in self.store.list()],
            "context_package": qwen_context.model_dump(mode="json"),
            "qwen_result": qwen_result,
            "claude_result": claude_result,
            "execution_decision": execution_decision.model_dump(mode="json"),
            "receipts": [receipt.model_dump(mode="json") for receipt in self.receipts.list()],
        }


def build_default_mvp() -> ValoMemoryMVP:
    return ValoMemoryMVP()
