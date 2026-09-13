#!/usr/bin/env python3
"""GOS-001D — evidence, assumption, stakeholder and dataset governance graph.

Canonical anchor: ``nsolland/Index`` PR #483
(``2026-07-27-governance-os-ai-board-control-system.md``).

Builds the deterministic governance graph over epistemic artifacts:

* ``EvidenceNode`` — immutable evidence with digest, provenance, freshness,
  independence, quality and contamination state. Never an instruction.
* ``AssumptionNode`` — falsifiable claim with a validity window and
  invalidation triggers.
* ``StakeholderNode`` / ``AffectedPartyNode`` — retained even when minority;
  affected-party evidence is never omitted from a summary.
* ``DatasetRegistry`` — datasets bound to purpose and permitted use.
* ``EvidenceGraph`` — cycle detection (circular evidence), stale surfacing,
  contamination flag and semantic-degradation surfacing.

Mechanical invariant: none of these artifacts is an instruction surface.
Evidence and assumptions inform a decision but never execute, clear, permit,
approve or grant authority. ``AUTHORITY_EFFECT`` is always ``"none"``,
there is no decision/authority field on evidence, and attempts to coerce
evidence into an instruction fail closed. REHT/RACS authority semantics are
not touched here; this module is evidence-plane only.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "gos-evidence-v1"
AUTHORITY_EFFECT = "none"

# Assumption / evidence state vocabulary.
VALID = "valid"
INVALIDATED = "invalidated"
STALE = "stale"
EXPIRED = "expired"
NOT_ACTIVE = "not_active"

# Evidence kinds.
KIND_OBSERVATION = "observation"
KIND_MEASUREMENT = "measurement"
KIND_REPORT = "report"
KIND_TEST_RESULT = "test_result"
KIND_CORROBORATION = "corroboration"

# Independence classes.
INDEPENDENT = "independent"
DERIVED = "derived"
SHARED_SOURCE = "shared_source"

# Contamination signals.
CONTAM_VERBATIM_REPRODUCTION = "verbatim_reproduction"
CONTAM_SHARED_SOURCE = "shared_source_confound"
CONTAM_DERIVED_FROM_CONTAMINATED = "derived_from_contaminated"

# Semantic-integrity signals.
SEM_LOSSY_TRANSFORM = "lossy_transform"
SEM_MISSING_SOURCE_DIGEST = "missing_source_digest"
SEM_MISSING_CONTENT_DIGEST = "missing_content_digest"
SEM_CHAIN_GAP = "transformation_chain_gap"
SEM_LANGUAGE_MISMATCH = "language_mismatch"

# Freshness signals.
STALE_VALIDITY_EXPIRED = "validity_window_expired"
STALE_MAX_AGE_EXCEEDED = "max_age_exceeded"
STALE_REVIEW_DUE = "review_overdue"

# Representation signals.
REPRESENTATION_NO_EVIDENCE = "no_affected_party_evidence"
REPRESENTATION_MISSING_TEXT = "missing_representation"
REPRESENTATION_PROXY_ONLY = "proxy_only_voice"
REPRESENTATION_CONSENT_MISSING = "consent_missing"

# Failure modes for malformed input.
FAIL_MALFORMED_JSON = "malformed_json"
FAIL_UNKNOWN_FIELD = "unknown_field"
FAIL_INSTRUCTION_SURFACE = "instruction_surface_field"

# Field names that would make an artifact instruction-like. Rejected on
# construction and never accepted through the mapping parser.
_FORBIDDEN_AUTHORITY_TOKENS = frozenset(
    token.strip().lower()
    for token in (
        "execute", "execution", "executes", "executed", "executable",
        "authority", "authorize", "authorized", "authorizes",
        "authorisation", "authorization",
        "clearance", "clear", "cleared", "clearing",
        "permit", "permission", "permitted", "permissions", "permitting",
        "approve", "approved", "approval", "approves",
        "dispatch", "command", "grant", "granted", "grants",
        "deny", "denied", "denies", "halt", "halted",
        "allow", "allowed", "allows", "allowance",
    )
)

# Declarative data-use policy fields. Pure metadata describing what a dataset
# MAY be used for; they grant no action authority to any actor.
DECLARATIVE_POLICY_FIELDS = frozenset(
    {"permitted_use", "prohibited_use", "purpose_ref", "use_policy_ref"}
)

_ALLOWED_EVIDENCE_FIELDS = frozenset(
    {
        "evidence_id",
        "kind",
        "content",
        "original_language",
        "language",
        "source_ref",
        "recorded_at",
        "valid_until",
        "provenance",
        "derived_from",
        "independence",
        "transformation_history",
    }
)

_ALLOWED_EVIDENCE_TRANSFORM_KEYS = frozenset(
    {
        "from_language",
        "to_language",
        "method",
        "performed_by",
        "performed_at",
        "source_digest",
        "content_digest",
    }
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_aware(value: datetime | None, name: str) -> None:
    if value is not None and value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")


def _require_digest(value: str | None, name: str) -> None:
    if value is not None and not _SHA256_RE.match(value):
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")


def _require_identifier(value: str, name: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} is required")


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize deterministically (sorted keys, compact separators)."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_default,
    )


def deterministic_digest(payload: Mapping[str, Any]) -> str:
    """Return a stable sha256 hex digest for any mapping payload."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def content_digest(*, content: str, language: str) -> str:
    """Digest of the linguistic content; translation changes the digest."""
    return deterministic_digest({"content": content, "language": language})


@dataclass(frozen=True)
class ValidityWindow:
    """Time-bounded window during which an artifact is live."""

    starts_at: datetime
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware(self.starts_at, "starts_at")
        _require_aware(self.valid_until, "valid_until")
        if self.valid_until is not None and self.valid_until <= self.starts_at:
            raise ValueError("valid_until must be after starts_at")

    def active(self, now: datetime | None = None) -> bool:
        current = now or _utcnow()
        if current < self.starts_at:
            return False
        if self.valid_until is not None and current >= self.valid_until:
            return False
        return True


@dataclass(frozen=True)
class TransformationStep:
    """One step in the multilingual transformation history of an artifact."""

    from_language: str
    to_language: str
    method: str
    performed_by: str
    performed_at: datetime
    source_digest: str | None = None
    content_digest: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.from_language, "from_language")
        _require_identifier(self.to_language, "to_language")
        _require_identifier(self.method, "method")
        _require_identifier(self.performed_by, "performed_by")
        if self.from_language == self.to_language:
            raise ValueError("from_language and to_language must differ")
        _require_aware(self.performed_at, "performed_at")
        _require_digest(self.source_digest, "source_digest")
        _require_digest(self.content_digest, "content_digest")


@dataclass(frozen=True)
class EvidenceNode:
    """A piece of evidence. Structurally incapable of carrying instruction.

    There is no decision/authority/clearance/permit field on an evidence node.
    Construction with such keyword arguments raises ``TypeError`` and
    ``to_instruction`` fails closed. ``authority_effect`` is always ``"none"``.
    """

    evidence_id: str
    kind: str
    content: str
    original_language: str
    language: str
    source_ref: str
    recorded_at: datetime
    valid_until: datetime | None = None
    provenance: tuple[str, ...] = ()
    derived_from: tuple[str, ...] = ()
    independence: str = INDEPENDENT
    transformation_history: tuple[TransformationStep, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.evidence_id, "evidence_id")
        _require_identifier(self.kind, "kind")
        _require_identifier(self.content, "content")
        _require_identifier(self.original_language, "original_language")
        _require_identifier(self.language, "language")
        _require_identifier(self.source_ref, "source_ref")
        if self.independence not in (INDEPENDENT, DERIVED, SHARED_SOURCE):
            raise ValueError(f"unknown independence class: {self.independence}")
        _require_aware(self.recorded_at, "recorded_at")
        _require_aware(self.valid_until, "valid_until")
        if self.valid_until is not None and self.valid_until <= self.recorded_at:
            raise ValueError("valid_until must be after recorded_at")

    @property
    def digest(self) -> str:
        """Deterministic digest over the node's identity-relevant fields."""
        return deterministic_digest(self.to_dict())

    @property
    def content_digest_value(self) -> str:
        return content_digest(content=self.content, language=self.language)

    @property
    def authority_effect(self) -> str:
        return AUTHORITY_EFFECT

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "kind": self.kind,
            "content": self.content,
            "original_language": self.original_language,
            "language": self.language,
            "source_ref": self.source_ref,
            "recorded_at": self.recorded_at,
            "valid_until": self.valid_until,
            "provenance": self.provenance,
            "derived_from": self.derived_from,
            "independence": self.independence,
            "transformation_history": [
                {
                    "from_language": step.from_language,
                    "to_language": step.to_language,
                    "method": step.method,
                    "performed_by": step.performed_by,
                    "performed_at": step.performed_at,
                    "source_digest": step.source_digest,
                    "content_digest": step.content_digest,
                }
                for step in self.transformation_history
            ],
        }

    def to_instruction(self) -> None:
        """Fail closed: evidence can never be coerced into an instruction."""
        raise ValueError(
            "evidence is never instruction; refusing to build an instruction"
        )


def evidence_from_mapping(mapping: Mapping[str, Any]) -> EvidenceNode:
    """Build an EvidenceNode from a mapping, rejecting unknown fields.

    Unknown keys and any key that looks like an authority/instruction surface
    cause a fail-closed ``ValueError``. ``transformation_history`` may be a
    tuple of ``TransformationStep`` or a tuple of dicts.
    """
    unknown = set(mapping) - _ALLOWED_EVIDENCE_FIELDS
    if unknown:
        raise ValueError(f"unknown evidence fields: {sorted(unknown)}")
    missing_required = {
        "evidence_id",
        "kind",
        "content",
        "original_language",
        "language",
        "source_ref",
        "recorded_at",
    } - set(mapping)
    if missing_required:
        raise ValueError(
            f"missing required evidence fields: {sorted(missing_required)}"
        )
    for key in mapping:
        token = key.lower().replace("_", "")
        if any(blocked in token for blocked in _FORBIDDEN_AUTHORITY_TOKENS):
            raise ValueError(f"evidence field '{key}' is an instruction surface")

    history = mapping.get("transformation_history", ())
    if history and all(isinstance(step, dict) for step in history):
        steps: list[TransformationStep] = []
        for step in history:
            step_unknown = set(step) - _ALLOWED_EVIDENCE_TRANSFORM_KEYS
            if step_unknown:
                raise ValueError(
                    f"unknown transformation step fields: {sorted(step_unknown)}"
                )
            steps.append(TransformationStep(**step))
        mapping = {**mapping, "transformation_history": tuple(steps)}
    return EvidenceNode(**dict(mapping))


@dataclass(frozen=True)
class InvalidationTrigger:
    """A falsifying condition for an assumption.

    A trigger fires when counter-evidence of a matching kind (or any kind when
    ``evidence_kinds`` is empty) whose content contains
    ``matches_content_substring`` (when set) is bound to the assumption.
    """

    trigger_id: str
    condition: str
    evidence_kinds: tuple[str, ...] = ()
    matches_content_substring: str | None = None
    automatic: bool = True

    def __post_init__(self) -> None:
        _require_identifier(self.trigger_id, "trigger_id")
        _require_identifier(self.condition, "condition")

    def fires_against(self, evidence: EvidenceNode) -> bool:
        if self.evidence_kinds and evidence.kind not in self.evidence_kinds:
            return False
        if (
            self.matches_content_substring is not None
            and self.matches_content_substring not in evidence.content
        ):
            return False
        return True


@dataclass(frozen=True)
class AssumptionNode:
    """A falsifiable claim with a validity window and invalidation triggers."""

    assumption_id: str
    claim: str
    owner: str
    validity_window: ValidityWindow
    invalidation_triggers: tuple[InvalidationTrigger, ...]
    supporting_evidence_refs: tuple[str, ...] = ()
    counter_evidence_refs: tuple[str, ...] = ()
    next_review_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.assumption_id, "assumption_id")
        _require_identifier(self.claim, "claim")
        _require_identifier(self.owner, "owner")
        if not self.invalidation_triggers:
            raise ValueError("assumption requires at least one invalidation trigger")
        _require_aware(self.next_review_at, "next_review_at")

    @property
    def authority_effect(self) -> str:
        return AUTHORITY_EFFECT


@dataclass(frozen=True)
class AssumptionStatus:
    assumption_id: str
    state: str
    reasons: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.state == VALID


def evaluate_assumption_status(
    assumption: AssumptionNode,
    evidence_by_id: Mapping[str, EvidenceNode],
    *,
    now: datetime | None = None,
) -> AssumptionStatus:
    """Continuously determine whether an assumption still holds."""
    current = now or _utcnow()
    window = assumption.validity_window

    if current < window.starts_at:
        return AssumptionStatus(
            assumption_id=assumption.assumption_id,
            state=NOT_ACTIVE,
            reasons=("validity_window_not_started",),
        )

    fired: list[str] = []
    for trigger in assumption.invalidation_triggers:
        for ref in assumption.counter_evidence_refs:
            evidence = evidence_by_id.get(ref)
            if evidence is None:
                continue
            if trigger.fires_against(evidence):
                fired.append(trigger.trigger_id)
    if fired:
        return AssumptionStatus(
            assumption_id=assumption.assumption_id,
            state=INVALIDATED,
            reasons=tuple(f"trigger_fired:{trigger_id}" for trigger_id in fired),
        )

    if window.valid_until is not None and current >= window.valid_until:
        return AssumptionStatus(
            assumption_id=assumption.assumption_id,
            state=EXPIRED,
            reasons=("validity_window_expired",),
        )

    if assumption.next_review_at is not None and current >= assumption.next_review_at:
        has_recent_support = False
        for ref in assumption.supporting_evidence_refs:
            evidence = evidence_by_id.get(ref)
            if (
                evidence is not None
                and evidence.valid_until is not None
                and current < evidence.valid_until
            ):
                has_recent_support = True
                break
        if not has_recent_support:
            return AssumptionStatus(
                assumption_id=assumption.assumption_id,
                state=STALE,
                reasons=("review_overdue_no_recent_supporting_evidence",),
            )

    return AssumptionStatus(
        assumption_id=assumption.assumption_id,
        state=VALID,
        reasons=(),
    )


@dataclass(frozen=True)
class StakeholderNode:
    """A stakeholder. ``affected_party`` marks affected-party standing."""

    stakeholder_id: str
    name: str
    group: str
    affected_party: bool = False
    vulnerable: bool = False
    has_direct_voice: bool = False
    consent_status: str = "not_recorded"
    minority: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.stakeholder_id, "stakeholder_id")
        _require_identifier(self.name, "name")
        _require_identifier(self.group, "group")
        if self.minority and not self.affected_party:
            raise ValueError("minority status implies affected-party standing")

    @property
    def authority_effect(self) -> str:
        return AUTHORITY_EFFECT


AffectedPartyNode = StakeholderNode


@dataclass(frozen=True)
class AffectedPartyEvidenceLink:
    """Binds an affected stakeholder to the evidence representing them."""

    link_id: str
    stakeholder_id: str
    evidence_id: str
    impact_class: str
    representation: str

    def __post_init__(self) -> None:
        _require_identifier(self.link_id, "link_id")
        _require_identifier(self.stakeholder_id, "stakeholder_id")
        _require_identifier(self.evidence_id, "evidence_id")
        _require_identifier(self.impact_class, "impact_class")
        _require_identifier(self.representation, "representation")


class StakeholderGraph:
    """Maps affected parties to their rights, exposure and evidence.

    Minority / affected-party evidence is retained: ``affected_party_evidence``
    is the canonical enumeration and never omits an affected party.
    """

    def __init__(
        self,
        *,
        stakeholders: Iterable[StakeholderNode] = (),
        evidence_links: Iterable[AffectedPartyEvidenceLink] = (),
    ) -> None:
        self._stakeholders: dict[str, StakeholderNode] = {}
        self._links: dict[str, AffectedPartyEvidenceLink] = {}
        for stakeholder in stakeholders:
            self.add_stakeholder(stakeholder)
        for link in evidence_links:
            self.add_evidence_link(link)

    def add_stakeholder(self, stakeholder: StakeholderNode) -> None:
        if stakeholder.stakeholder_id in self._stakeholders:
            raise ValueError(
                f"duplicate stakeholder id: {stakeholder.stakeholder_id}"
            )
        self._stakeholders[stakeholder.stakeholder_id] = stakeholder

    def add_evidence_link(self, link: AffectedPartyEvidenceLink) -> None:
        if link.stakeholder_id not in self._stakeholders:
            raise ValueError(f"unknown stakeholder: {link.stakeholder_id}")
        if link.link_id in self._links:
            raise ValueError(f"duplicate link id: {link.link_id}")
        self._links[link.link_id] = link

    @property
    def stakeholders(self) -> dict[str, StakeholderNode]:
        return dict(self._stakeholders)

    @property
    def evidence_links(self) -> dict[str, AffectedPartyEvidenceLink]:
        return dict(self._links)

    def affected_parties(self) -> tuple[StakeholderNode, ...]:
        return tuple(
            s for s in self._stakeholders.values() if s.affected_party
        )

    def evidence_for_stakeholder(
        self, stakeholder_id: str
    ) -> tuple[AffectedPartyEvidenceLink, ...]:
        return tuple(
            link
            for link in self._links.values()
            if link.stakeholder_id == stakeholder_id
        )

    def affected_party_evidence(
        self,
    ) -> tuple[tuple[StakeholderNode, AffectedPartyEvidenceLink], ...]:
        """Every affected party with its evidence, including minority.

        Retention is explicit: this canonical enumeration never omits an
        affected party, even when a summary would otherwise drop it.
        """
        return tuple(
            (self._stakeholders[link.stakeholder_id], link)
            for link in self._links.values()
            if self._stakeholders[link.stakeholder_id].affected_party
        )

    def coverage(self) -> dict[str, int]:
        """Affected-party coverage breakdown. Minority parties are counted."""
        grouped: dict[str, int] = {}
        for link in self._links.values():
            stakeholder = self._stakeholders[link.stakeholder_id]
            if not stakeholder.affected_party:
                continue
            group = stakeholder.group
            grouped[group] = grouped.get(group, 0) + 1
        return grouped

    def affected_party_ids_without_evidence(self) -> tuple[str, ...]:
        with_evidence = {link.stakeholder_id for link in self._links.values()}
        return tuple(
            s.stakeholder_id
            for s in self._stakeholders.values()
            if s.affected_party and s.stakeholder_id not in with_evidence
        )


@dataclass(frozen=True)
class RepresentationQualityReport:
    stakeholder_id: str
    adequate: bool
    reasons: tuple[str, ...]


def evaluate_representation_quality(
    graph: StakeholderGraph,
    *,
    require_consent: bool = False,
    stakeholder_ids: Iterable[str] | None = None,
) -> tuple[RepresentationQualityReport, ...]:
    """Verify that affected parties are actually represented in evidence."""
    ids = (
        tuple(stakeholder_ids)
        if stakeholder_ids is not None
        else tuple(s.stakeholder_id for s in graph.affected_parties())
    )
    reports: list[RepresentationQualityReport] = []
    for stakeholder_id in ids:
        stakeholder = graph.stakeholders[stakeholder_id]
        links = graph.evidence_for_stakeholder(stakeholder_id)
        reasons: list[str] = []
        if not links:
            reasons.append(REPRESENTATION_NO_EVIDENCE)
        if links and all(not link.representation.strip() for link in links):
            reasons.append(REPRESENTATION_MISSING_TEXT)
        if stakeholder.vulnerable and not stakeholder.has_direct_voice:
            reasons.append(REPRESENTATION_PROXY_ONLY)
        if require_consent and stakeholder.consent_status not in {
            "consented",
            "not_applicable",
        }:
            reasons.append(REPRESENTATION_CONSENT_MISSING)
        reports.append(
            RepresentationQualityReport(
                stakeholder_id=stakeholder_id,
                adequate=not reasons,
                reasons=tuple(reasons),
            )
        )
    return tuple(reports)


@dataclass(frozen=True)
class DatasetRecord:
    """A governed dataset linked to a purpose and a permitted-use policy."""

    dataset_id: str
    name: str
    purpose_ref: str
    permitted_use: tuple[str, ...]
    owner: str
    version: str = "1"
    prohibited_use: tuple[str, ...] = ()
    contains_affected_party_data: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.dataset_id, "dataset_id")
        _require_identifier(self.name, "name")
        _require_identifier(self.purpose_ref, "purpose_ref")
        _require_identifier(self.owner, "owner")
        if not self.permitted_use:
            raise ValueError("permitted_use must be explicit")

    @property
    def authority_effect(self) -> str:
        return AUTHORITY_EFFECT

    def permits(self, use: str) -> bool:
        return use in self.permitted_use


class DatasetRegistry:
    """Purpose + permitted-use binding for governed datasets."""

    def __init__(self, datasets: Iterable[DatasetRecord] = ()) -> None:
        self._datasets: dict[str, DatasetRecord] = {}
        for dataset in datasets:
            self.register(dataset)

    def register(self, dataset: DatasetRecord) -> None:
        if dataset.dataset_id in self._datasets:
            raise ValueError(f"duplicate dataset id: {dataset.dataset_id}")
        self._datasets[dataset.dataset_id] = dataset

    def get(self, dataset_id: str) -> DatasetRecord | None:
        return self._datasets.get(dataset_id)

    def datasets_for_purpose(self, purpose_ref: str) -> tuple[DatasetRecord, ...]:
        return tuple(
            dataset
            for dataset in self._datasets.values()
            if dataset.purpose_ref == purpose_ref
        )

    def all(self) -> tuple[DatasetRecord, ...]:
        return tuple(self._datasets.values())


@dataclass(frozen=True)
class FreshnessPolicy:
    max_age: timedelta | None = None


def evaluate_freshness(
    evidence: EvidenceNode,
    *,
    now: datetime | None = None,
    policy: FreshnessPolicy = FreshnessPolicy(),
) -> tuple[bool, tuple[str, ...]]:
    current = now or _utcnow()
    reasons: list[str] = []
    if evidence.valid_until is not None and current >= evidence.valid_until:
        reasons.append(STALE_VALIDITY_EXPIRED)
    if policy.max_age is not None:
        age = current - evidence.recorded_at
        if age > policy.max_age:
            reasons.append(STALE_MAX_AGE_EXCEEDED)
    return (not reasons, tuple(reasons))


def evaluate_semantic_integrity(
    evidence: EvidenceNode,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Evaluate multilingual semantic integrity of an evidence chain.

    Returns ``(languages, flags)``. Every transformation step must carry
    digests, the chain must be continuous (each step's source digest matches
    the previous step's content digest, or the original content digest for the
    first step) and the final step must arrive at ``evidence.language``.
    """
    flags: list[str] = []
    steps = evidence.transformation_history

    original_digest = content_digest(
        content=evidence.content, language=evidence.original_language
    )
    if evidence.language != evidence.original_language:
        original_digest = deterministic_digest(
            {
                "content": evidence.content,
                "language": evidence.original_language,
            }
        )

    if not steps:
        if evidence.language != evidence.original_language:
            flags.append(SEM_CHAIN_GAP)
            flags.append(SEM_LANGUAGE_MISMATCH)
        return (evidence.original_language,), tuple(flags)

    previous_digest = original_digest
    languages: list[str] = [evidence.original_language]
    for step in steps:
        languages.append(step.to_language)
        if step.source_digest is None:
            flags.append(SEM_MISSING_SOURCE_DIGEST)
        elif step.source_digest != previous_digest:
            flags.append(SEM_CHAIN_GAP)
        if step.content_digest is None:
            flags.append(SEM_MISSING_CONTENT_DIGEST)
        else:
            previous_digest = step.content_digest
        if step.method == "lossy-compress":
            flags.append(SEM_LOSSY_TRANSFORM)

    if languages[-1] != evidence.language:
        flags.append(SEM_LANGUAGE_MISMATCH)

    return tuple(languages), tuple(flags)


@dataclass(frozen=True)
class SemanticIntegrityResult:
    evidence_id: str
    languages: tuple[str, ...]
    flags: tuple[str, ...]

    @property
    def degraded(self) -> bool:
        return bool(self.flags)


class EvidenceGraph:
    """Binds evidence, assumptions and stakeholders into one navigable graph.

    Provides stale surfacing, circular-evidence detection (via
    ``derived_from``), contamination flagging and semantic-degradation
    surfacing. Evidence is never instruction: there is no decision/authority
    field on any node.
    """

    def __init__(
        self,
        *,
        evidence: Iterable[EvidenceNode] = (),
        assumptions: Iterable[AssumptionNode] = (),
    ) -> None:
        self._evidence: dict[str, EvidenceNode] = {}
        self._assumptions: dict[str, AssumptionNode] = {}
        for record in evidence:
            self.add_evidence(record)
        for assumption in assumptions:
            self.add_assumption(assumption)

    def add_evidence(self, record: EvidenceNode) -> None:
        if record.evidence_id in self._evidence:
            raise ValueError(f"duplicate evidence id: {record.evidence_id}")
        self._evidence[record.evidence_id] = record

    def add_assumption(self, assumption: AssumptionNode) -> None:
        if assumption.assumption_id in self._assumptions:
            raise ValueError(f"duplicate assumption id: {assumption.assumption_id}")
        self._assumptions[assumption.assumption_id] = assumption

    @property
    def evidence(self) -> dict[str, EvidenceNode]:
        return dict(self._evidence)

    @property
    def assumptions(self) -> dict[str, AssumptionNode]:
        return dict(self._assumptions)

    def evidence_by_id(self) -> Mapping[str, EvidenceNode]:
        return self._evidence

    def evidence_for_assumption(
        self, assumption_id: str
    ) -> tuple[EvidenceNode, ...]:
        assumption = self._assumptions.get(assumption_id)
        if assumption is None:
            return ()
        refs = set(assumption.supporting_evidence_refs)
        refs.update(assumption.counter_evidence_refs)
        return tuple(
            self._evidence[ref] for ref in refs if ref in self._evidence
        )

    def assumptions_for_evidence(self, evidence_id: str) -> tuple[str, ...]:
        if evidence_id not in self._evidence:
            return ()
        return tuple(
            assumption_id
            for assumption_id, assumption in self._assumptions.items()
            if evidence_id
            in set(assumption.supporting_evidence_refs).union(
                assumption.counter_evidence_refs
            )
        )

    def stale_evidence(
        self,
        *,
        now: datetime | None = None,
        policy: FreshnessPolicy = FreshnessPolicy(),
    ) -> tuple[str, ...]:
        """Surface evidence whose validity window or max age has lapsed."""
        current = now or _utcnow()
        return tuple(
            evidence_id
            for evidence_id, evidence in self._evidence.items()
            if not evaluate_freshness(evidence, now=current, policy=policy)[0]
        )

    def circular_evidence(self) -> tuple[tuple[str, ...], ...]:
        """Detect circular derivation chains in the evidence graph (DFS)."""

        def _visit(node: str) -> tuple[tuple[str, ...], ...]:
            nonlocal state, stack, cycles
            state[node] = 1
            stack.append(node)
            found: tuple[tuple[str, ...], ...] = ()
            for neighbour in adjacency.get(node, ()):
                if state.get(neighbour, 0) == 0:
                    found += _visit(neighbour)
                elif state.get(neighbour, 0) == 1:
                    start = stack.index(neighbour)
                    cycle = tuple(stack[start:])
                    found += (cycle,)
            stack.pop()
            state[node] = 2
            return found

        adjacency: dict[str, tuple[str, ...]] = {}
        for evidence_id, record in self._evidence.items():
            adjacency[evidence_id] = tuple(
                ref for ref in record.derived_from if ref in self._evidence
            )

        state: dict[str, int] = {}
        stack: list[str] = []
        cycles: list[tuple[str, ...]] = []
        seen: set[tuple[str, ...]] = set()
        for evidence_id in self._evidence:
            if state.get(evidence_id, 0) == 0:
                for cycle in _visit(evidence_id):
                    canonical = tuple(
                        min(
                            cycle[i:] + cycle[:i]
                            for i in range(len(cycle))
                        )
                    )
                    if canonical not in seen:
                        seen.add(canonical)
                        cycles.append(cycle)
        return tuple(cycles)

    def contaminated_evidence(self) -> tuple[str, ...]:
        """Surface evidence that is not independent (contamination signals)."""
        evidence = self._evidence
        reasons: dict[str, list[str]] = {}

        digest_groups: dict[str, list[str]] = {}
        for evidence_id, record in evidence.items():
            digest_groups.setdefault(record.content_digest_value, []).append(
                evidence_id
            )
        for digest, ids in digest_groups.items():
            if len(ids) > 1:
                for evidence_id in ids:
                    reasons.setdefault(evidence_id, []).append(
                        CONTAM_VERBATIM_REPRODUCTION
                    )

        source_groups: dict[str, list[str]] = {}
        for evidence_id, record in evidence.items():
            source_groups.setdefault(record.source_ref, []).append(evidence_id)
        for source, ids in source_groups.items():
            if len(ids) > 1:
                for evidence_id in ids:
                    reasons.setdefault(evidence_id, []).append(CONTAM_SHARED_SOURCE)

        contaminated = {
            evidence_id: tuple(rs) for evidence_id, rs in reasons.items()
        }
        changed = True
        while changed:
            changed = False
            for evidence_id, record in evidence.items():
                if evidence_id in contaminated:
                    continue
                if any(ref in contaminated for ref in record.derived_from):
                    contaminated[evidence_id] = (CONTAM_DERIVED_FROM_CONTAMINATED,)
                    changed = True

        return tuple(contaminated)

    def semantically_degraded_evidence(self) -> tuple[str, ...]:
        """Surface evidence whose transformation history is not continuous."""
        degraded: list[str] = []
        for evidence_id, record in self._evidence.items():
            languages, flags = evaluate_semantic_integrity(record)
            if flags:
                degraded.append(evidence_id)
        return tuple(degraded)

    def integrity_result(self, evidence_id: str) -> SemanticIntegrityResult:
        record = self._evidence.get(evidence_id)
        if record is None:
            raise ValueError(f"unknown evidence id: {evidence_id}")
        languages, flags = evaluate_semantic_integrity(record)
        return SemanticIntegrityResult(
            evidence_id=evidence_id,
            languages=languages,
            flags=flags,
        )

    def contamination_flag(self, evidence_id: str) -> str:
        """Return ``"contaminated"`` or ``"clean"`` for an evidence node."""
        if evidence_id in self.contaminated_evidence():
            return "contaminated"
        return "clean"

    def all_issues(
        self,
        *,
        now: datetime | None = None,
        policy: FreshnessPolicy = FreshnessPolicy(),
    ) -> dict[str, Any]:
        """Surface all quality failures for the evidence graph at once."""
        return {
            "stale_evidence": self.stale_evidence(now=now, policy=policy),
            "circular_chains": self.circular_evidence(),
            "contaminated_evidence": self.contaminated_evidence(),
            "semantically_degraded_evidence": self.semantically_degraded_evidence(),
        }
