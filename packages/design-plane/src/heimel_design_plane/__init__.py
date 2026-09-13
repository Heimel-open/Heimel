"""Shared bounded Design Plane for Heimel application domains."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Iterable, Mapping


class DesignPlaneError(RuntimeError):
    """Raised when a candidate cannot advance through the design plane."""


class PromotionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    EVIDENCE_READY = "EVIDENCE_READY"
    AUTHORITY_REQUIRED = "AUTHORITY_REQUIRED"


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Intent:
    intent_id: str
    domain: str
    objective: str
    constraints: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()
    measures: tuple[str, ...] = ()

    @property
    def digest(self) -> str:
        return _digest(self.__dict__)


@dataclass(frozen=True)
class CandidateDesign:
    candidate_id: str
    intent_digest: str
    mechanism: Mapping[str, object]
    predicted_effects: tuple[str, ...] = ()

    @property
    def digest(self) -> str:
        return _digest(
            {
                "candidate_id": self.candidate_id,
                "intent_digest": self.intent_digest,
                "mechanism": dict(self.mechanism),
                "predicted_effects": self.predicted_effects,
            }
        )


@dataclass(frozen=True)
class EvidenceVector:
    candidate_digest: str
    dimensions: Mapping[str, float]
    controls_passed: tuple[str, ...] = ()
    shadow_verified: bool = False
    provenance: tuple[str, ...] = ()

    @property
    def digest(self) -> str:
        return _digest(
            {
                "candidate_digest": self.candidate_digest,
                "dimensions": dict(self.dimensions),
                "controls_passed": self.controls_passed,
                "shadow_verified": self.shadow_verified,
                "provenance": self.provenance,
            }
        )


@dataclass(frozen=True)
class PromotionProposal:
    intent_digest: str
    candidate_digest: str
    evidence_digest: str
    domain: str
    effect_class: str
    status: PromotionStatus = PromotionStatus.AUTHORITY_REQUIRED

    @property
    def digest(self) -> str:
        return _digest(self.__dict__)


@dataclass(frozen=True)
class DomainBinding:
    domain: str
    search_object: str
    evidence_focus: tuple[str, ...]
    effect_class: str


DOMAIN_BINDINGS: dict[str, DomainBinding] = {
    "alpha": DomainBinding(
        domain="alpha",
        search_object="system_design",
        evidence_focus=("correctness", "security", "reliability", "cost", "complexity"),
        effect_class="system_change",
    ),
    "relaion": DomainBinding(
        domain="relaion",
        search_object="stewarded_development_path",
        evidence_focus=("lineage", "continuity", "stewardship", "capability", "relational_integrity"),
        effect_class="persistent_seed_change",
    ),
    "gcu": DomainBinding(
        domain="gcu",
        search_object="work_unit_execution_design",
        evidence_focus=("completion", "quality", "sla", "cost", "exception_rate"),
        effect_class="work_unit_execution",
    ),
    "traxin": DomainBinding(
        domain="traxin",
        search_object="organizational_workflow_design",
        evidence_focus=("throughput", "error_rate", "cost", "bottlenecks", "responsibility_integrity"),
        effect_class="workflow_change",
    ),
}


class DesignPlane:
    """Search/evaluation boundary that never grants consequence authority itself."""

    def __init__(self, intent: Intent) -> None:
        if intent.domain not in DOMAIN_BINDINGS:
            raise DesignPlaneError(f"unsupported domain: {intent.domain}")
        self.intent = intent
        self.binding = DOMAIN_BINDINGS[intent.domain]
        self._candidates: dict[str, CandidateDesign] = {}
        self._evidence: dict[str, EvidenceVector] = {}

    def register_candidate(self, candidate: CandidateDesign) -> None:
        if candidate.intent_digest != self.intent.digest:
            raise DesignPlaneError("candidate is not bound to active intent")
        self._candidates[candidate.digest] = candidate

    def attach_evidence(self, evidence: EvidenceVector) -> None:
        if evidence.candidate_digest not in self._candidates:
            raise DesignPlaneError("evidence references unknown candidate")
        self._evidence[evidence.candidate_digest] = evidence

    def pareto_candidates(self, dimensions: Iterable[str] | None = None) -> tuple[CandidateDesign, ...]:
        dims = tuple(dimensions or self.binding.evidence_focus)
        scored: list[tuple[CandidateDesign, EvidenceVector]] = []
        for digest, candidate in self._candidates.items():
            evidence = self._evidence.get(digest)
            if evidence is None:
                continue
            if not all(dim in evidence.dimensions for dim in dims):
                continue
            scored.append((candidate, evidence))

        frontier: list[CandidateDesign] = []
        for candidate, evidence in scored:
            dominated = False
            for other_candidate, other_evidence in scored:
                if other_candidate.digest == candidate.digest:
                    continue
                at_least_as_good = all(
                    other_evidence.dimensions[dim] >= evidence.dimensions[dim] for dim in dims
                )
                strictly_better = any(
                    other_evidence.dimensions[dim] > evidence.dimensions[dim] for dim in dims
                )
                if at_least_as_good and strictly_better:
                    dominated = True
                    break
            if not dominated:
                frontier.append(candidate)
        return tuple(frontier)

    def propose_promotion(
        self,
        candidate_digest: str,
        *,
        required_controls: Iterable[str] = (),
        require_shadow: bool = True,
    ) -> PromotionProposal:
        candidate = self._candidates.get(candidate_digest)
        if candidate is None:
            raise DesignPlaneError("unknown candidate")
        evidence = self._evidence.get(candidate_digest)
        if evidence is None:
            raise DesignPlaneError("promotion requires evidence")

        missing = set(required_controls) - set(evidence.controls_passed)
        if missing:
            raise DesignPlaneError(f"missing required controls: {sorted(missing)}")
        if require_shadow and not evidence.shadow_verified:
            raise DesignPlaneError("promotion requires shadow verification")

        return PromotionProposal(
            intent_digest=self.intent.digest,
            candidate_digest=candidate.digest,
            evidence_digest=evidence.digest,
            domain=self.intent.domain,
            effect_class=self.binding.effect_class,
            status=PromotionStatus.AUTHORITY_REQUIRED,
        )


__all__ = [
    "CandidateDesign",
    "DesignPlane",
    "DesignPlaneError",
    "DomainBinding",
    "DOMAIN_BINDINGS",
    "EvidenceVector",
    "Intent",
    "PromotionProposal",
    "PromotionStatus",
]
