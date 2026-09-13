"""Evidence-bound influence intelligence contracts for Governed Newsroom.

These models represent public observations and qualified relationships. They do
not establish motive, truth, risk or authority. Speider collects observations,
BARO proposes links, and the Verification Factory qualifies findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class InfluenceNodeType(str, Enum):
    PERSON = "person"
    ORGANISATION = "organisation"
    EVENT = "event"
    REPORT = "report"
    CLAIM = "claim"
    PUBLICATION = "publication"
    CONTRACT = "contract"
    FUNDING_INSTRUMENT = "funding_instrument"
    PUBLIC_BODY = "public_body"
    DECISION_PROCESS = "decision_process"


class InfluenceEdgeType(str, Enum):
    EMPLOYED_BY = "employed_by"
    ADVISES = "advises"
    FUNDS = "funds"
    COMMISSIONS = "commissions"
    SPONSORS = "sponsors"
    HOSTS = "hosts"
    SPEAKS_AT = "speaks_at"
    MODERATES = "moderates"
    AUTHORS = "authors"
    CITES = "cites"
    REPUBLISHES = "republishes"
    CONTROLS_PUBLICATION = "controls_publication"
    PARTICIPATES_IN = "participates_in"
    BENEFITS_FROM = "benefits_from"
    CONTRADICTS = "contradicts"
    DERIVES_FROM = "derives_from"


class EvidenceLevel(str, Enum):
    DOCUMENTARY = "documentary"
    CORROBORATED_INFERENCE = "corroborated_inference"
    SINGLE_SOURCE_INFERENCE = "single_source_inference"
    SPECULATION = "speculation"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProvenanceRef:
    source_uri: str
    captured_at: datetime
    content_digest: str
    adapter_id: str
    raw_artifact_ref: str | None = None


@dataclass(frozen=True)
class InfluenceNode:
    node_id: str
    node_type: InfluenceNodeType
    label: str
    aliases: tuple[str, ...] = ()
    public_identifiers: dict[str, str] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InfluenceObservation:
    observation_id: str
    subject_id: str
    predicate: InfluenceEdgeType
    object_id: str
    observed_at: datetime
    valid_from: datetime | None
    valid_until: datetime | None
    provenance: tuple[ProvenanceRef, ...]
    evidence_level: EvidenceLevel = EvidenceLevel.UNKNOWN
    limitations: tuple[str, ...] = ()
    BARO_hypothesis: bool = False

    def is_publishable_finding(self) -> bool:
        """Return whether this relationship may enter a verified finding set.

        Final use still requires Verification Factory disposition and REHT
        clearance. Speculation and unknown relationships are never publishable.
        """

        return (
            bool(self.provenance)
            and self.evidence_level
            in {EvidenceLevel.DOCUMENTARY, EvidenceLevel.CORROBORATED_INFERENCE}
        )


@dataclass(frozen=True)
class InfluenceGraphPackage:
    package_id: str
    nodes: tuple[InfluenceNode, ...]
    observations: tuple[InfluenceObservation, ...]
    generated_at: datetime
    scope: str
    unresolved_questions: tuple[str, ...] = ()

    def publishable_observations(self) -> tuple[InfluenceObservation, ...]:
        return tuple(item for item in self.observations if item.is_publishable_finding())
