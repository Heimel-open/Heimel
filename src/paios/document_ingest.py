"""Provider-neutral document parsing contract for Relygon / PAIOS.

Document parsers are commodity perception components. Their output is admitted
as located raw evidence, never as authority, policy, truth, or permission to act.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from .peripherals import EvidenceStage, ObservationEnvelope, SourceRef


@dataclass(frozen=True)
class DocumentLocation:
    page: int
    x0: float | None = None
    y0: float | None = None
    x1: float | None = None
    y1: float | None = None

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if self.page < 1:
            errors.append("location.page must be >= 1")
        coords = (self.x0, self.y0, self.x1, self.y1)
        if any(value is not None for value in coords):
            if any(value is None for value in coords):
                errors.append("bounding box requires x0, y0, x1, y1")
            elif self.x1 < self.x0 or self.y1 < self.y0:
                errors.append("bounding box coordinates are invalid")
        return tuple(errors)


@dataclass(frozen=True)
class DocumentBlock:
    block_id: str
    block_type: str
    text: str
    location: DocumentLocation
    confidence: float | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = list(self.location.validate())
        if not self.block_id.strip():
            errors.append("block_id is required")
        if not self.block_type.strip():
            errors.append("block_type is required")
        if not self.text.strip():
            errors.append("block text is required")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            errors.append("block confidence must be between 0 and 1")
        return tuple(errors)


@dataclass(frozen=True)
class ParsedDocument:
    document_id: str
    parser_provider: str
    parser_model: str
    parser_version: str | None
    source_integrity_ref: str
    blocks: tuple[DocumentBlock, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.document_id.strip():
            errors.append("document_id is required")
        if not self.parser_provider.strip():
            errors.append("parser_provider is required")
        if not self.parser_model.strip():
            errors.append("parser_model is required")
        if not self.source_integrity_ref.strip():
            errors.append("source_integrity_ref is required")
        if not self.blocks:
            errors.append("at least one parsed block is required")
        seen: set[str] = set()
        for block in self.blocks:
            errors.extend(block.validate())
            if block.block_id in seen:
                errors.append(f"duplicate block_id: {block.block_id}")
            seen.add(block.block_id)
        return tuple(errors)


@runtime_checkable
class DocumentParser(Protocol):
    """Replaceable parser adapter. Parser output has no execution authority."""

    adapter_name: str

    def parse(self, document: bytes, *, document_id: str) -> ParsedDocument:
        ...


def blocks_as_observations(
    parsed: ParsedDocument,
    *,
    subject_id: str,
    observed_at,
    received_at,
    mandate_id: str | None = None,
    purpose: str | None = None,
) -> tuple[ObservationEnvelope, ...]:
    """Convert parsed blocks to provenance-preserving RAW observations.

    Interpretation, durable-memory promotion, policy resolution and action
    authorization remain downstream governed operations.
    """

    errors = parsed.validate()
    if errors:
        raise ValueError("; ".join(errors))

    source = SourceRef(
        provider=parsed.parser_provider,
        adapter="document_parser",
        model=parsed.parser_model,
        version=parsed.parser_version,
    )

    observations: list[ObservationEnvelope] = []
    for block in parsed.blocks:
        provenance = {
            "document_id": parsed.document_id,
            "block_id": block.block_id,
            "page": block.location.page,
            "bbox": (
                block.location.x0,
                block.location.y0,
                block.location.x1,
                block.location.y1,
            ),
            "parser_provider": parsed.parser_provider,
            "parser_model": parsed.parser_model,
            "parser_version": parsed.parser_version,
            "source_integrity_ref": parsed.source_integrity_ref,
        }
        observations.append(
            ObservationEnvelope(
                observation_id=f"{parsed.document_id}:{block.block_id}",
                subject_id=subject_id,
                observed_at=observed_at,
                received_at=received_at,
                modality="document_block",
                source=source,
                payload={
                    "block_type": block.block_type,
                    "text": block.text,
                    "attributes": dict(block.attributes),
                },
                provenance=provenance,
                confidence=block.confidence,
                mandate_id=mandate_id,
                purpose=purpose,
                integrity_ref=parsed.source_integrity_ref,
                stage=EvidenceStage.RAW,
            )
        )
    return tuple(observations)
