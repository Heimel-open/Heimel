from datetime import datetime, timezone

import pytest

from paios.document_ingest import (
    DocumentBlock,
    DocumentLocation,
    ParsedDocument,
    blocks_as_observations,
)
from paios.peripherals import EvidenceStage


def _parsed() -> ParsedDocument:
    return ParsedDocument(
        document_id="doc-1",
        parser_provider="example",
        parser_model="parser-v1",
        parser_version="1.0",
        source_integrity_ref="sha256:abc",
        blocks=(
            DocumentBlock(
                block_id="b1",
                block_type="paragraph",
                text="Payment limit is 25,000.",
                location=DocumentLocation(page=2, x0=0.1, y0=0.2, x1=0.8, y1=0.3),
                confidence=0.97,
            ),
        ),
    )


def test_blocks_become_raw_located_evidence() -> None:
    ts = datetime(2026, 9, 3, tzinfo=timezone.utc)
    observations = blocks_as_observations(
        _parsed(),
        subject_id="person-1",
        observed_at=ts,
        received_at=ts,
        mandate_id="mandate-1",
        purpose="review",
    )

    assert len(observations) == 1
    observation = observations[0]
    assert observation.stage is EvidenceStage.RAW
    assert observation.modality == "document_block"
    assert observation.payload["text"] == "Payment limit is 25,000."
    assert observation.provenance["document_id"] == "doc-1"
    assert observation.provenance["block_id"] == "b1"
    assert observation.provenance["page"] == 2
    assert observation.provenance["bbox"] == (0.1, 0.2, 0.8, 0.3)
    assert observation.integrity_ref == "sha256:abc"


def test_parser_output_never_promotes_itself_beyond_raw() -> None:
    ts = datetime(2026, 9, 3, tzinfo=timezone.utc)
    observation = blocks_as_observations(
        _parsed(), subject_id="person-1", observed_at=ts, received_at=ts
    )[0]

    assert observation.stage is EvidenceStage.RAW
    assert observation.mandate_id is None
    assert observation.purpose is None


def test_invalid_location_fails_closed() -> None:
    parsed = ParsedDocument(
        document_id="doc-1",
        parser_provider="example",
        parser_model="parser-v1",
        parser_version=None,
        source_integrity_ref="sha256:abc",
        blocks=(
            DocumentBlock(
                block_id="b1",
                block_type="table",
                text="x",
                location=DocumentLocation(page=0),
            ),
        ),
    )
    ts = datetime(2026, 9, 3, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="location.page"):
        blocks_as_observations(
            parsed, subject_id="person-1", observed_at=ts, received_at=ts
        )


def test_duplicate_block_ids_fail_closed() -> None:
    block = DocumentBlock(
        block_id="b1",
        block_type="paragraph",
        text="x",
        location=DocumentLocation(page=1),
    )
    parsed = ParsedDocument(
        document_id="doc-1",
        parser_provider="example",
        parser_model="parser-v1",
        parser_version=None,
        source_integrity_ref="sha256:abc",
        blocks=(block, block),
    )
    ts = datetime(2026, 9, 3, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="duplicate block_id"):
        blocks_as_observations(
            parsed, subject_id="person-1", observed_at=ts, received_at=ts
        )
