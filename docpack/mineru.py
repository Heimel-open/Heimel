"""MinerU-compatible intake: turn structured document output into candidates.

MinerU's layout model emits per-page blocks with a ``bbox`` of
``(x0, y0, x1, y1)``, a block ``type`` (e.g. ``text``, ``table``,
``formula``, ``image``, ``caption``, ``footnote``), raw ``text`` and a
parser ``score``/confidence. This adapter converts those blocks into
``ExtractedObservation`` *candidates* that stay linked to the immutable
source identity, page number and exact coordinates.

Tables, formulas, diagrams, captions and footnotes remain distinct
semantic objects (they keep their block ``type`` and ``object_id``).

Low-confidence blocks raise an ``UnresolvedDocumentQuestion`` instead of
claiming a confident answer.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .digest import digest_of_bytes
from .models import (
    ExtractedObservation,
    ParseConfidenceEvidence,
    SourceLocationRef,
    UnresolvedDocumentQuestion,
)
from .pipeline import DocumentPipeline

LOW_CONFIDENCE_THRESHOLD = 0.8

MINERU_KIND = {
    "text": "statement",
    "title": "statement",
    "paragraph": "statement",
    "table": "table",
    "formula": "formula",
    "image": "diagram",
    "figure": "diagram",
    "caption": "caption",
    "footnote": "footnote",
}


def mineru_block_to_observation(
    source_digest: str,
    page: int,
    block_index: int,
    block: Mapping[str, Any],
    parser_name: str,
    parser_version: str,
    model_version: str,
) -> ExtractedObservation:
    """Convert a single MinerU layout block into an observation candidate."""
    bbox = tuple(float(v) for v in block.get("bbox", (0, 0, 0, 0)))
    if len(bbox) != 4:
        raise ValueError(f"block bbox must have 4 values, got {bbox!r}")
    block_type = str(block.get("type", "text"))
    kind = MINERU_KIND.get(block_type, "statement")

    score = block.get("score", block.get("confidence", 1.0))
    confidence = ParseConfidenceEvidence(
        parser_name=parser_name,
        parser_version=parser_version,
        confidence=float(score),
        method="layout_block",
        model_version=model_version,
    )

    location = SourceLocationRef(
        document_hash=source_digest,
        page=page,
        coordinates=bbox,
        object_type=block_type,
        object_id=str(block.get("id", block.get("object_id", ""))),
    )

    observation_id = f"p{page}-b{block_index}"
    return ExtractedObservation(
        observation_id=observation_id,
        location=location,
        original_text=str(block.get("text", "")),
        kind=kind,
        confidence=confidence,
        reading_order=block_index,
    )


def mineru_pages_to_observations(
    source_digest: str,
    pages: Sequence[Mapping[str, Any]],
    parser_name: str = "mineru",
    parser_version: str = "0.0.0",
    model_version: str = "",
) -> tuple[list[ExtractedObservation], list[UnresolvedDocumentQuestion]]:
    """Flatten MinerU pages (each with ``layout_blocks``/``blocks``) to candidates.

    Returns ``(observations, questions)``. Questions are raised for every
    low-confidence block instead of asserting its content.
    """
    observations: list[ExtractedObservation] = []
    questions: list[UnresolvedDocumentQuestion] = []

    for page_index, page in enumerate(pages):
        page_no = int(page.get("page_no", page.get("page", page_index + 1)))
        blocks: Sequence[Mapping[str, Any]] = page.get(
            "layout_blocks", page.get("blocks", [])
        )
        for block_index, block in enumerate(blocks):
            observation = mineru_block_to_observation(
                source_digest=source_digest,
                page=page_no,
                block_index=block_index,
                block=block,
                parser_name=parser_name,
                parser_version=parser_version,
                model_version=model_version,
            )
            observations.append(observation)
            if observation.confidence is not None and (
                observation.confidence.confidence < LOW_CONFIDENCE_THRESHOLD
            ):
                questions.append(
                    UnresolvedDocumentQuestion(
                        question_id=f"q-p{page_no}-b{block_index}",
                        question=(
                            f"Low-confidence extraction on page {page_no} "
                            f"({observation.kind} block): content cannot be "
                            "asserted as fact."
                        ),
                        location=observation.location,
                        cause="low_confidence_extraction",
                        related_observation_id=observation.observation_id,
                    )
                )
    return observations, questions


def build_package_from_mineru(
    name: str,
    data: bytes,
    pages: Sequence[Mapping[str, Any]],
    parser_name: str = "mineru",
    parser_version: str = "0.0.0",
    model_version: str = "",
    package_id: str | None = None,
) -> tuple[CanonicalDocumentPackage, list[UnresolvedDocumentQuestion]]:
    """End-to-end: raw source bytes + MinerU pages -> a frozen package."""
    from .models import CanonicalDocumentPackage  # noqa: F401  (re-export)

    pipeline = DocumentPipeline(package_id=package_id)
    pipeline.from_source(name, data)
    pipeline.set_extraction_provenance(
        parser_name=parser_name,
        parser_version=parser_version,
        model_version=model_version,
    )
    observations, questions = mineru_pages_to_observations(
        source_digest=pipeline.source_identity.source_digest,
        pages=pages,
        parser_name=parser_name,
        parser_version=parser_version,
        model_version=model_version,
    )
    pipeline.add_observations(observations)
    for question in questions:
        pipeline.add_question(question)
    return pipeline.build(), questions


__all__ = [
    "build_package_from_mineru",
    "digest_of_bytes",
    "mineru_block_to_observation",
    "mineru_pages_to_observations",
]
