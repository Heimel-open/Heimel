"""Versioned, frozen contracts for the Tofoo canonical document pipeline.

Strict separation is preserved by construction:
    source -> immutable source identity -> structured extraction
    -> observation -> interpretation -> assumption -> hypothesis -> conclusion

Every contract is frozen (immutable after construction), carries a
``schema_version`` and exposes a deterministic ``digest()`` over its
canonical encoding. No later layer may erase or overwrite an earlier one;
later layers only add references to earlier layers.
"""

from __future__ import annotations

import dataclasses
import enum
from dataclasses import dataclass
from typing import Any, Mapping

from .digest import canonical_digest

CONTRACT_SCHEMA_VERSION = "1.0"

STATEMENT_KINDS = frozenset(
    {"statement", "table", "formula", "diagram", "caption", "footnote"}
)

INTERPRETATION_ROLES = frozenset(
    {
        "interpretation",
        "acceptance",
        "correction",
        "reading_order_proposal",
        "summary",
    }
)


class ReasoningStage(str, enum.Enum):
    SOURCE = "source"
    SOURCE_IDENTITY = "source_identity"
    STRUCTURED_EXTRACTION = "structured_extraction"
    OBSERVATION = "observation"
    INTERPRETATION = "interpretation"
    ASSUMPTION = "assumption"
    HYPOTHESIS = "hypothesis"
    CONCLUSION = "conclusion"


STAGE_ORDER: tuple[ReasoningStage, ...] = (
    ReasoningStage.SOURCE,
    ReasoningStage.SOURCE_IDENTITY,
    ReasoningStage.STRUCTURED_EXTRACTION,
    ReasoningStage.OBSERVATION,
    ReasoningStage.INTERPRETATION,
    ReasoningStage.ASSUMPTION,
    ReasoningStage.HYPOTHESIS,
    ReasoningStage.CONCLUSION,
)


class Contract:
    """Base for all versioned, digestable contracts."""

    schema_version: str = CONTRACT_SCHEMA_VERSION

    def to_canonical(self) -> dict[str, Any]:
        fields = dataclasses.fields(self)
        payload = {
            f.name: getattr(self, f.name)
            for f in fields
            if f.name != "package_digest"
        }
        return {"_type": type(self).__name__, **payload}

    def digest(self) -> str:
        return canonical_digest(self.to_canonical())


@dataclass(frozen=True)
class SourceLocationRef(Contract):
    """A stable, addressable location inside one source document."""

    document_hash: str
    page: int
    coordinates: tuple[float, float, float, float]
    coordinate_system: str = "mineru"
    object_type: str = "text"
    object_id: str = ""
    schema_version: str = CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.page < 0:
            raise ValueError(f"page must be >= 0, got {self.page}")
        if len(self.coordinates) != 4:
            raise ValueError(
                "coordinates must be (x0, y0, x1, y1), got "
                f"{self.coordinates!r}"
            )


@dataclass(frozen=True)
class ParseConfidenceEvidence(Contract):
    """Provenance for how a block was parsed and how confident the parser is."""

    parser_name: str
    parser_version: str
    confidence: float
    method: str
    model_version: str = ""
    schema_version: str = CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence!r}"
            )

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.8


@dataclass(frozen=True)
class ExtractedObservation(Contract):
    """One parser-produced observation candidate.

    An observation is always a *candidate*, never accepted meaning. The
    ``is_accepted_meaning`` flag is therefore structurally forbidden from
    ever being True here; acceptance is modelled as a separate
    ``InterpretationCandidate`` with role ``acceptance``.
    """

    observation_id: str
    location: SourceLocationRef
    original_text: str
    translations: tuple[tuple[str, str], ...] = ()
    kind: str = "statement"
    confidence: ParseConfidenceEvidence | None = None
    reading_order: int | None = None
    is_accepted_meaning: bool = False
    schema_version: str = CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.is_accepted_meaning:
            raise ValueError(
                "parser output is an observation candidate, "
                "never accepted meaning"
            )
        if self.kind not in STATEMENT_KINDS:
            raise ValueError(f"unknown observation kind {self.kind!r}")

    def translated(self, language: str, text: str) -> ExtractedObservation:
        """Return a new observation with an additive translation.

        The original-language ``original_text`` is never overwritten.
        """
        return dataclasses.replace(
            self,
            translations=tuple([*self.translations, (language, text)]),
        )


@dataclass(frozen=True)
class InterpretationCandidate(Contract):
    """A candidate interpretation built on top of observation candidates."""

    interpretation_id: str
    text: str
    based_on: tuple[str, ...] = ()
    role: str = "interpretation"
    created_by: str = ""
    created_at: str = ""
    rationale: str = ""
    schema_version: str = CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.role not in INTERPRETATION_ROLES:
            raise ValueError(f"unknown interpretation role {self.role!r}")
        if self.based_on and not all(isinstance(x, str) for x in self.based_on):
            raise ValueError("based_on must be a tuple of string ids")


@dataclass(frozen=True)
class SourceConflict(Contract):
    """Two contradictory source passages, kept visible and never merged."""

    conflict_id: str
    left_observation_id: str
    right_observation_id: str
    left_location: SourceLocationRef
    right_location: SourceLocationRef
    note: str = ""
    schema_version: str = CONTRACT_SCHEMA_VERSION


@dataclass(frozen=True)
class UnresolvedDocumentQuestion(Contract):
    """An open question raised by low-confidence or ambiguous extraction."""

    question_id: str
    question: str
    location: SourceLocationRef | None = None
    cause: str = ""
    related_observation_id: str = ""
    schema_version: str = CONTRACT_SCHEMA_VERSION


@dataclass(frozen=True)
class SourceIdentity(Contract):
    """Immutable identity of the original source.

    Computed once from the source bytes; nothing downstream may alter it.
    """

    source_digest: str
    name: str
    byte_length: int
    algorithm: str = "sha256"
    schema_version: str = CONTRACT_SCHEMA_VERSION


@dataclass(frozen=True)
class ExtractionProvenance(Contract):
    """Parser and model versions retained as part of provenance."""

    parser_name: str
    parser_version: str
    model_version: str = ""
    tool: str = "mineru"
    schema_version: str = CONTRACT_SCHEMA_VERSION


@dataclass(frozen=True)
class ReasoningStatement(Contract):
    """Assumption, hypothesis or conclusion layer of the reasoning chain."""

    statement_id: str
    stage: ReasoningStage
    text: str
    based_on: tuple[str, ...] = ()
    created_by: str = ""
    created_at: str = ""
    schema_version: str = CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.stage not in (
            ReasoningStage.ASSUMPTION,
            ReasoningStage.HYPOTHESIS,
            ReasoningStage.CONCLUSION,
        ):
            raise ValueError(
                f"stage {self.stage!r} is not a reasoning statement stage"
            )


@dataclass(frozen=True)
class ChainRecord(Contract):
    """One link in the package's hash-linked reasoning chain."""

    stage: ReasoningStage
    content_digest: str
    prev_digest: str = ""
    actor: str = ""
    timestamp: str = ""
    schema_version: str = CONTRACT_SCHEMA_VERSION


@dataclass(frozen=True)
class CanonicalDocumentPackage(Contract):
    """A frozen, versioned package tying every reasoning layer together."""

    package_id: str
    schema_version: str = CONTRACT_SCHEMA_VERSION
    source_identity: SourceIdentity | None = None
    extraction_provenance: ExtractionProvenance | None = None
    observations: tuple[ExtractedObservation, ...] = ()
    interpretations: tuple[InterpretationCandidate, ...] = ()
    conflicts: tuple[SourceConflict, ...] = ()
    questions: tuple[UnresolvedDocumentQuestion, ...] = ()
    statements: tuple[ReasoningStatement, ...] = ()
    chain: tuple[ChainRecord, ...] = ()
    predecessor_digest: str = ""
    package_digest: str = ""

    def verify(self) -> list[str]:
        """Return a list of integrity violations; empty list means valid."""
        violations: list[str] = []

        if self.source_identity is None:
            violations.append("package has no source identity")
            return violations

        source = self.source_identity.source_digest

        if self.package_digest != canonical_digest(self.to_canonical()):
            violations.append("package_digest does not match recomputed digest")

        if self.predecessor_digest and len(self.predecessor_digest) != 64:
            violations.append("predecessor_digest is not a sha256 hex digest")

        for obs in self.observations:
            if obs.is_accepted_meaning:
                violations.append(
                    f"observation {obs.observation_id} claims accepted "
                    "meaning; acceptance belongs to the interpretation layer"
                )
            if obs.location.document_hash != source:
                violations.append(
                    f"observation {obs.observation_id} references document "
                    f"hash {obs.location.document_hash[:8]}... but source is "
                    f"{source[:8]}..."
                )
            if obs.kind not in STATEMENT_KINDS:
                violations.append(
                    f"observation {obs.observation_id} has unknown kind "
                    f"{obs.kind!r}"
                )
            if obs.location.coordinates is None or len(
                obs.location.coordinates
            ) != 4:
                violations.append(
                    f"observation {obs.observation_id} lacks 4 coordinates"
                )

        observed_ids = {o.observation_id for o in self.observations}
        for interp in self.interpretations:
            missing = [
                ref
                for ref in interp.based_on
                if ref not in observed_ids
                and not any(c.conflict_id == ref for c in self.conflicts)
                and not any(
                    q.question_id == ref for q in self.questions
                )
            ]
            if missing:
                violations.append(
                    f"interpretation {interp.interpretation_id} references "
                    f"unknown ids {missing}"
                )

        for conflict in self.conflicts:
            if conflict.left_observation_id not in observed_ids:
                violations.append(
                    f"conflict {conflict.conflict_id} references unknown "
                    f"left observation {conflict.left_observation_id}"
                )
            if conflict.right_observation_id not in observed_ids:
                violations.append(
                    f"conflict {conflict.conflict_id} references unknown "
                    f"right observation {conflict.right_observation_id}"
                )
            if (
                conflict.left_location.document_hash != source
                or conflict.right_location.document_hash != source
            ):
                violations.append(
                    f"conflict {conflict.conflict_id} references a location "
                    "outside the source"
                )

        for question in self.questions:
            if (
                question.related_observation_id
                and question.related_observation_id not in observed_ids
            ):
                violations.append(
                    f"question {question.question_id} references unknown "
                    f"observation {question.related_observation_id}"
                )
            if (
                question.location is not None
                and question.location.document_hash != source
            ):
                violations.append(
                    f"question {question.question_id} references a location "
                    "outside the source"
                )

        for statement in self.statements:
            missing = [
                ref
                for ref in statement.based_on
                if ref not in observed_ids
                and ref not in {i.interpretation_id for i in self.interpretations}
                and not any(q.question_id == ref for q in self.questions)
            ]
            if missing:
                violations.append(
                    f"statement {statement.statement_id} references unknown "
                    f"ids {missing}"
                )

        chain_ok, chain_errors = self._verify_chain()
        violations.extend(chain_errors)

        return violations

    def _verify_chain(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        ordered = STAGE_ORDER
        stage_rank = {s.value: i for i, s in enumerate(ordered)}

        prev = None
        prev_rank = -1
        for record in self.chain:
            if record.stage.value not in stage_rank:
                errors.append(
                    f"chain record has unknown stage {record.stage.value!r}"
                )
                prev = record
                continue
            rank = stage_rank[record.stage.value]
            if rank < prev_rank:
                errors.append(
                    f"chain stage order violated: {record.stage.value} "
                    "appears after a later stage"
                )
            if prev is not None and record.prev_digest != prev.digest():
                errors.append(
                    "chain hash link broken between stages "
                    f"{prev.stage.value} -> {record.stage.value}"
                )
            expected = self._chain_content_digest(record.stage)
            if expected is not None and record.content_digest != expected:
                errors.append(
                    f"chain content digest mismatch for stage "
                    f"{record.stage.value}"
                )
            prev = record
            prev_rank = rank
        return (not errors, errors)

    def _chain_content_digest(
        self, stage: ReasoningStage
    ) -> str | None:
        """Recompute what a stage's content digest should be, if derivable."""
        if stage == ReasoningStage.SOURCE:
            if self.source_identity is None:
                return None
            return canonical_digest(self.source_identity.source_digest)
        if stage == ReasoningStage.SOURCE_IDENTITY:
            if self.source_identity is None:
                return None
            return canonical_digest(self.source_identity.to_canonical())
        if stage in (
            ReasoningStage.STRUCTURED_EXTRACTION,
            ReasoningStage.OBSERVATION,
        ):
            return canonical_digest([o.digest() for o in self.observations])
        if stage == ReasoningStage.INTERPRETATION:
            return canonical_digest(
                [i.digest() for i in self.interpretations]
            )
        if stage in (
            ReasoningStage.ASSUMPTION,
            ReasoningStage.HYPOTHESIS,
            ReasoningStage.CONCLUSION,
        ):
            matching = [
                s.digest()
                for s in self.statements
                if s.stage == stage
            ]
            return canonical_digest(matching)
        return None
