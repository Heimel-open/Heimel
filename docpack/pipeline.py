"""Append-only pipeline that assembles a CanonicalDocumentPackage.

Nothing is ever deleted or overwritten: later layers only reference earlier
layers. Source identity is fixed at construction time and all observations
must point back at it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .digest import canonical_digest, digest_of_bytes
from .models import (
    STAGE_ORDER,
    ChainRecord,
    CanonicalDocumentPackage,
    ExtractedObservation,
    ExtractionProvenance,
    InterpretationCandidate,
    ParseConfidenceEvidence,
    ReasoningStage,
    ReasoningStatement,
    SourceConflict,
    SourceIdentity,
    SourceLocationRef,
    UnresolvedDocumentQuestion,
)


@dataclass
class _PipelineState:
    source_identity: SourceIdentity | None = None
    observations: list[ExtractedObservation] = field(default_factory=list)
    interpretations: list[InterpretationCandidate] = field(default_factory=list)
    conflicts: list[SourceConflict] = field(default_factory=list)
    questions: list[UnresolvedDocumentQuestion] = field(default_factory=list)
    statements: list[ReasoningStatement] = field(default_factory=list)
    extraction_provenance: ExtractionProvenance | None = None
    predecessor_digest: str = ""


class DocumentPipeline:
    """Builder enforcing strict layer separation for Tofoo reasoning."""

    def __init__(
        self,
        package_id: str | None = None,
        previous: CanonicalDocumentPackage | None = None,
    ) -> None:
        self._package_id = package_id or uuid.uuid4().hex
        self._state = _PipelineState()
        if previous is not None:
            self._state.predecessor_digest = previous.package_digest
            self._state.observations = list(previous.observations)
            self._state.interpretations = list(previous.interpretations)
            self._state.conflicts = list(previous.conflicts)
            self._state.questions = list(previous.questions)
            self._state.statements = list(previous.statements)
            self._state.extraction_provenance = previous.extraction_provenance

    @property
    def source_identity(self) -> SourceIdentity | None:
        return self._state.source_identity

    @property
    def observations(self) -> tuple[ExtractedObservation, ...]:
        return tuple(self._state.observations)

    def from_source(self, name: str, data: bytes) -> SourceIdentity:
        """Fix the immutable source identity for this package."""
        if self._state.source_identity is not None:
            raise ValueError("source identity is immutable and already set")
        identity = SourceIdentity(
            source_digest=digest_of_bytes(data),
            name=name,
            byte_length=len(data),
        )
        self._state.source_identity = identity
        return identity

    def set_extraction_provenance(
        self,
        parser_name: str,
        parser_version: str,
        model_version: str = "",
        tool: str = "mineru",
    ) -> ExtractionProvenance:
        provenance = ExtractionProvenance(
            parser_name=parser_name,
            parser_version=parser_version,
            model_version=model_version,
            tool=tool,
        )
        self._state.extraction_provenance = provenance
        return provenance

    def add_observation(
        self, observation: ExtractedObservation
    ) -> ExtractedObservation:
        """Append one observation candidate; it can never be removed."""
        identity = self._require_source()
        if observation.location.document_hash != identity.source_digest:
            raise ValueError(
                f"observation {observation.observation_id} references "
                f"document hash {observation.location.document_hash[:8]}... "
                f"but source is {identity.source_digest[:8]}..."
            )
        if observation.is_accepted_meaning:
            raise ValueError(
                f"observation {observation.observation_id} must stay a "
                "candidate; acceptance lives in the interpretation layer"
            )
        self._state.observations.append(observation)
        return observation

    def add_observations(
        self, observations: Sequence[ExtractedObservation]
    ) -> list[ExtractedObservation]:
        added: list[ExtractedObservation] = []
        for obs in observations:
            self.add_observation(obs)
            added.append(obs)
        return added

    def add_interpretation(
        self,
        interpretation: InterpretationCandidate,
    ) -> InterpretationCandidate:
        observed_ids = {o.observation_id for o in self._state.observations}
        missing = [
            ref
            for ref in interpretation.based_on
            if ref not in observed_ids
            and not any(c.conflict_id == ref for c in self._state.conflicts)
            and not any(
                q.question_id == ref for q in self._state.questions
            )
        ]
        if missing:
            raise ValueError(
                f"interpretation {interpretation.interpretation_id} "
                f"references unknown ids {missing}"
            )
        self._state.interpretations.append(interpretation)
        return interpretation

    def accept_observation(
        self,
        observation_id: str,
        created_by: str = "",
        created_at: str = "",
        rationale: str = "",
    ) -> InterpretationCandidate:
        """Record acceptance as an attributable interpretation-layer event.

        The observation itself remains a candidate and is not overwritten.
        """
        observed = {o.observation_id: o for o in self._state.observations}
        if observation_id not in observed:
            raise ValueError(f"unknown observation {observation_id!r}")
        interpretation = InterpretationCandidate(
            interpretation_id=f"acc-{observation_id}",
            text=observed[observation_id].original_text,
            based_on=(observation_id,),
            role="acceptance",
            created_by=created_by,
            created_at=created_at,
            rationale=rationale,
        )
        return self.add_interpretation(interpretation)

    def add_conflict(
        self,
        left_observation_id: str,
        right_observation_id: str,
        note: str = "",
        conflict_id: str | None = None,
    ) -> SourceConflict:
        observed = {o.observation_id: o for o in self._state.observations}
        for oid in (left_observation_id, right_observation_id):
            if oid not in observed:
                raise ValueError(f"unknown observation {oid!r}")
        conflict = SourceConflict(
            conflict_id=conflict_id or f"conflict-{left_observation_id}-{right_observation_id}",
            left_observation_id=left_observation_id,
            right_observation_id=right_observation_id,
            left_location=observed[left_observation_id].location,
            right_location=observed[right_observation_id].location,
            note=note,
        )
        self._state.conflicts.append(conflict)
        return conflict

    def add_question(
        self,
        question: UnresolvedDocumentQuestion,
    ) -> UnresolvedDocumentQuestion:
        observed = {o.observation_id for o in self._state.observations}
        if (
            question.related_observation_id
            and question.related_observation_id not in observed
        ):
            raise ValueError(
                f"question {question.question_id} references unknown "
                f"observation {question.related_observation_id}"
            )
        self._state.questions.append(question)
        return question

    def add_statement(
        self,
        stage: ReasoningStage,
        text: str,
        based_on: Sequence[str] = (),
        created_by: str = "",
        created_at: str = "",
        statement_id: str | None = None,
    ) -> ReasoningStatement:
        known = (
            {o.observation_id for o in self._state.observations}
            | {i.interpretation_id for i in self._state.interpretations}
            | {q.question_id for q in self._state.questions}
        )
        missing = [ref for ref in based_on if ref not in known]
        if missing:
            raise ValueError(
                f"statement references unknown ids {missing}"
            )
        statement = ReasoningStatement(
            statement_id=statement_id or f"{stage.value}-{uuid.uuid4().hex[:8]}",
            stage=stage,
            text=text,
            based_on=tuple(based_on),
            created_by=created_by,
            created_at=created_at,
        )
        self._state.statements.append(statement)
        return statement

    def add_assumption(
        self, text: str, based_on: Sequence[str] = (), **kwargs: str
    ) -> ReasoningStatement:
        return self.add_statement(ReasoningStage.ASSUMPTION, text, based_on, **kwargs)

    def add_hypothesis(
        self, text: str, based_on: Sequence[str] = (), **kwargs: str
    ) -> ReasoningStatement:
        return self.add_statement(ReasoningStage.HYPOTHESIS, text, based_on, **kwargs)

    def add_conclusion(
        self, text: str, based_on: Sequence[str] = (), **kwargs: str
    ) -> ReasoningStatement:
        return self.add_statement(ReasoningStage.CONCLUSION, text, based_on, **kwargs)

    def _require_source(self) -> SourceIdentity:
        if self._state.source_identity is None:
            raise ValueError("from_source() must be called before adding layers")
        return self._state.source_identity

    def _stage_has_content(self, stage: ReasoningStage) -> bool:
        if stage in (
            ReasoningStage.STRUCTURED_EXTRACTION,
            ReasoningStage.OBSERVATION,
        ):
            return bool(self._state.observations)
        if stage == ReasoningStage.INTERPRETATION:
            return bool(self._state.interpretations)
        if stage in (
            ReasoningStage.ASSUMPTION,
            ReasoningStage.HYPOTHESIS,
            ReasoningStage.CONCLUSION,
        ):
            return any(
                s.stage == stage for s in self._state.statements
            )
        return True

    def _chain_content_digest(self, stage: ReasoningStage) -> str:
        identity = self._require_source()
        if stage == ReasoningStage.SOURCE:
            return canonical_digest(identity.source_digest)
        if stage == ReasoningStage.SOURCE_IDENTITY:
            return canonical_digest(identity.to_canonical())
        if stage in (
            ReasoningStage.STRUCTURED_EXTRACTION,
            ReasoningStage.OBSERVATION,
        ):
            return canonical_digest(
                [o.digest() for o in self._state.observations]
            )
        if stage == ReasoningStage.INTERPRETATION:
            return canonical_digest(
                [i.digest() for i in self._state.interpretations]
            )
        matching = [
            s.digest() for s in self._state.statements if s.stage == stage
        ]
        return canonical_digest(matching)

    def build(self) -> CanonicalDocumentPackage:
        identity = self._require_source()

        chain: list[ChainRecord] = []
        prev_digest = ""
        for stage in STAGE_ORDER:
            if not self._stage_has_content(stage):
                continue
            content_digest = self._chain_content_digest(stage)
            record = ChainRecord(
                stage=stage,
                content_digest=content_digest,
                prev_digest=prev_digest,
            )
            prev_digest = record.digest()
            chain.append(record)

        package = CanonicalDocumentPackage(
            package_id=self._package_id,
            source_identity=identity,
            extraction_provenance=self._state.extraction_provenance,
            observations=tuple(self._state.observations),
            interpretations=tuple(self._state.interpretations),
            conflicts=tuple(self._state.conflicts),
            questions=tuple(self._state.questions),
            statements=tuple(self._state.statements),
            chain=tuple(chain),
            predecessor_digest=self._state.predecessor_digest,
            package_digest="",
        )
        package_digest = canonical_digest(package.to_canonical())
        finalized = CanonicalDocumentPackage(
            package_id=package.package_id,
            schema_version=package.schema_version,
            source_identity=package.source_identity,
            extraction_provenance=package.extraction_provenance,
            observations=package.observations,
            interpretations=package.interpretations,
            conflicts=package.conflicts,
            questions=package.questions,
            statements=package.statements,
            chain=package.chain,
            predecessor_digest=package.predecessor_digest,
            package_digest=package_digest,
        )
        violations = finalized.verify()
        if violations:
            raise ValueError("package failed verification:\n- " + "\n- ".join(violations))
        return finalized
