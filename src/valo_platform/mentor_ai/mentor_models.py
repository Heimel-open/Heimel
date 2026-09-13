"""HistoricalCaseV1 & ScrambledCaseV1 — Mentor AI Factory data contracts.

Mentor AI Factory exists for junior training and method coaching in sandbox environments.
It outputs evaluation evidence ONLY and NEVER authorizes or executes real-world actions.
REHT remains the sole execution clearance boundary.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Tuple, Optional


def _canonical_digest(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class KnownOutcomeV1:
    actual_outcome_summary: str
    expert_decision_rationale: str
    acceptable_alternatives: Tuple[str, ...]
    schema_version: str = "v1"

    def canonical_payload(self) -> Mapping[str, object]:
        return asdict(self)

    @property
    def computed_digest(self) -> str:
        return _canonical_digest(self.canonical_payload())


@dataclass(frozen=True)
class HistoricalCaseV1:
    case_id: str
    tenant_id: str
    domain: str
    raw_content_digest: str
    known_outcome: KnownOutcomeV1
    legal_basis_approved: bool
    schema_version: str = "v1"

    def canonical_payload(self) -> Mapping[str, object]:
        return asdict(self)

    @property
    def computed_digest(self) -> str:
        return _canonical_digest(self.canonical_payload())


@dataclass(frozen=True)
class ScrambledCaseV1:
    scrambled_case_id: str
    original_case_id: str
    domain: str
    scrambled_scenario_text: str
    evidence_digests: Tuple[str, ...]
    scrambled_entity_mapping_digest: str  # Digest of entity transformation map (stored securely)
    schema_version: str = "v1"

    def canonical_payload(self) -> Mapping[str, object]:
        return asdict(self)

    @property
    def computed_digest(self) -> str:
        return _canonical_digest(self.canonical_payload())
