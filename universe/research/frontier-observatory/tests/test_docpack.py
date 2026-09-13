"""Tests for the canonical document package pipeline (issue #77).

Covers the six scenarios from the issue plus the required invariants:
immutable source identity, observation-candidate != accepted meaning,
linkage to hash/page/coordinates, conflict handling, unresolved questions
preserved, and source never overwritten by later layers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from docpack import (  # noqa: E402
    CanonicalDocumentPackage,
    ChainRecord,
    DocumentPipeline,
    ExtractedObservation,
    InterpretationCandidate,
    ParseConfidenceEvidence,
    ReasoningStage,
    SourceConflict,
    SourceLocationRef,
    UnresolvedDocumentQuestion,
    build_package_from_mineru,
    canonical_digest,
)

NORWEGIAN_SOURCE = b"Dette er en norsk kilde.\nSetning nummer to."


def _pipeline():
    pipe = DocumentPipeline()
    identity = pipe.from_source("kilde.txt", NORWEGIAN_SOURCE)
    pipe.set_extraction_provenance(
        parser_name="mineru",
        parser_version="2.2.1",
        model_version="mineru-v2",
    )
    return pipe, identity


def _obs(
    pipe,
    oid,
    text,
    page=1,
    bbox=(10.0, 20.0, 100.0, 40.0),
    confidence=0.95,
    kind="statement",
    object_type="text",
    reading_order=0,
):
    location = SourceLocationRef(
        document_hash=pipe.source_identity.source_digest,
        page=page,
        coordinates=bbox,
        object_type=object_type,
    )
    return ExtractedObservation(
        observation_id=oid,
        location=location,
        original_text=text,
        kind=kind,
        confidence=ParseConfidenceEvidence(
            parser_name="mineru",
            parser_version="2.2.1",
            confidence=confidence,
            method="layout_block",
            model_version="mineru-v2",
        ),
        reading_order=reading_order,
    )


def test_source_identity_is_immutable_and_deterministic():
    pipe, identity = _pipeline()
    assert identity.source_digest == pipe.source_identity.source_digest
    assert identity.digest() == identity.digest()

    pipe2 = DocumentPipeline()
    identity2 = pipe2.from_source("kilde.txt", NORWEGIAN_SOURCE)
    assert identity2.source_digest == identity.source_digest

    pipe3 = DocumentPipeline()
    identity3 = pipe3.from_source("kilde.txt", b"annerledes innhold")
    assert identity3.source_digest != identity.source_digest


def test_source_identity_cannot_be_replaced():
    pipe, _ = _pipeline()
    with pytest.raises(ValueError):
        pipe.from_source("annet.txt", b"en annen kilde")


def test_observation_must_link_to_source_hash():
    pipe, _ = _pipeline()
    wrong_hash = "0" * 64
    location = SourceLocationRef(
        document_hash=wrong_hash, page=1, coordinates=(0.0, 0.0, 10.0, 10.0)
    )
    obs = ExtractedObservation(
        observation_id="orphan", location=location, original_text="løs"
    )
    with pytest.raises(ValueError, match="references"):
        pipe.add_observation(obs)


def test_observation_is_candidate_not_accepted_meaning():
    pipe, _ = _pipeline()
    obs = _obs(pipe, "o1", "En observasjon.")
    assert obs.is_accepted_meaning is False

    with pytest.raises(ValueError, match="candidate"):
        ExtractedObservation(
            observation_id="o-bad",
            location=obs.location,
            original_text="X",
            is_accepted_meaning=True,
        )

    pipe.add_observation(obs)
    acceptance = pipe.accept_observation("o1", created_by="hermes")
    assert acceptance.role == "acceptance"
    assert acceptance.based_on == ("o1",)
    package = pipe.build()
    assert package.observations[0].is_accepted_meaning is False


def test_observation_linked_to_hash_page_coordinates():
    pipe, identity = _pipeline()
    bbox = (12.5, 30.0, 140.0, 55.0)
    obs = _obs(pipe, "o1", "Tekst", page=3, bbox=bbox)
    pipe.add_observation(obs)
    package = pipe.build()

    loc = package.observations[0].location
    assert loc.document_hash == identity.source_digest
    assert loc.page == 3
    assert loc.coordinates == bbox
    assert package.verify() == []


def test_original_norwegian_survives_translation_and_summarization():
    pipe, _ = _pipeline()
    original = "Havet er blått og uendelig."
    obs = _obs(pipe, "o1", original)
    translated = obs.translated("en", "The sea is blue and endless.")
    pipe.add_observation(translated)

    summary = InterpretationCandidate(
        interpretation_id="i1",
        text="The sea is described as blue and endless.",
        based_on=("o1",),
        role="summary",
        created_by="hermes",
    )
    pipe.add_interpretation(summary)
    pipe.add_conclusion(
        "Blue, endless sea.", based_on=("i1",), created_by="hermes"
    )

    package = pipe.build()
    observation = package.observations[0]
    assert observation.original_text == original
    assert ("en", "The sea is blue and endless.") in observation.translations
    assert observation.original_text != observation.translations[0][1]
    assert package.statements[0].stage == ReasoningStage.CONCLUSION


def test_translation_is_additive_not_overwriting():
    pipe, _ = _pipeline()
    obs = _obs(pipe, "o1", "Original tekst.")
    pipe.add_observation(obs)
    translated = pipe.observations[0].translated("en", "Original text.")
    assert translated.original_text == "Original tekst."
    assert len(translated.translations) == 1
    both = translated.translated("de", "Originaltext.")
    assert both.original_text == "Original tekst."
    assert ("de", "Originaltext.") in both.translations


def test_parser_error_remains_identifiable_after_reasoning_stages():
    pipe, _ = _pipeline()
    pipe.add_observation(
        _obs(pipe, "o1", "Uklar OCR-tekst", confidence=0.4)
    )
    question = UnresolvedDocumentQuestion(
        question_id="q1",
        question="Innholdet kan ikke fastslås sikkert.",
        cause="low_confidence_extraction",
        related_observation_id="o1",
    )
    pipe.add_question(question)
    pipe.add_interpretation(
        InterpretationCandidate(
            interpretation_id="i1",
            text="Tolkning med forbehold.",
            based_on=("o1",),
            created_by="hermes",
        )
    )
    pipe.add_conclusion(
        "Konklusjon basert på usikker observasjon.",
        based_on=("i1",),
        created_by="hermes",
    )
    package = pipe.build()

    assert len(package.questions) == 1
    question_record = package.questions[0]
    assert question_record.question_id == "q1"
    assert question_record.related_observation_id == "o1"
    assert "i1" in package.statements[0].based_on
    assert package.verify() == []


def test_conflicting_source_passages_not_silently_reconciled():
    pipe, _ = _pipeline()
    left = _obs(pipe, "o1", "Systemet er åpent.", bbox=(0.0, 0.0, 50.0, 20.0))
    right = _obs(pipe, "o2", "Systemet er lukket.", bbox=(60.0, 0.0, 120.0, 20.0))
    pipe.add_observation(left)
    pipe.add_observation(right)
    conflict = pipe.add_conflict(
        "o1", "o2", note="To steder sier det motsatte."
    )
    package = pipe.build()

    assert len(package.conflicts) == 1
    recorded: SourceConflict = package.conflicts[0]
    assert recorded.left_observation_id == "o1"
    assert recorded.right_observation_id == "o2"
    texts = {o.original_text for o in package.observations}
    assert "Systemet er åpent." in texts
    assert "Systemet er lukket." in texts
    assert "åpent og lukket" not in " ".join(texts)
    assert package.verify() == []


def test_conflict_keeps_both_locations():
    pipe, _ = _pipeline()
    left = _obs(pipe, "o1", "A", bbox=(0.0, 0.0, 10.0, 10.0), page=1)
    right = _obs(pipe, "o2", "B", bbox=(0.0, 0.0, 10.0, 10.0), page=4)
    pipe.add_observation(left)
    pipe.add_observation(right)
    conflict = pipe.add_conflict("o1", "o2")
    package = pipe.build()

    assert conflict.left_location.page == 1
    assert conflict.right_location.page == 4


def test_formula_and_table_references_resolve_to_exact_locations():
    pipe, _ = _pipeline()
    formula = _obs(
        pipe,
        "o-formula",
        "E = mc^2",
        page=2,
        bbox=(5.0, 5.0, 30.0, 15.0),
        kind="formula",
        object_type="formula",
    )
    table = _obs(
        pipe,
        "o-table",
        "| a | b |\n|---|---|\n| 1 | 2 |",
        page=3,
        bbox=(0.0, 0.0, 100.0, 50.0),
        kind="table",
        object_type="table",
    )
    pipe.add_observation(formula)
    pipe.add_observation(table)
    package = pipe.build()

    by_id = {o.observation_id: o for o in package.observations}
    assert by_id["o-formula"].kind == "formula"
    assert by_id["o-formula"].location.coordinates == (5.0, 5.0, 30.0, 15.0)
    assert by_id["o-formula"].location.page == 2
    assert by_id["o-table"].kind == "table"
    assert by_id["o-table"].location.coordinates == (0.0, 0.0, 100.0, 50.0)
    assert by_id["o-table"].location.page == 3
    assert package.verify() == []


def test_low_confidence_ocr_creates_unresolved_question():
    pages = [
        {
            "page_no": 1,
            "layout_blocks": [
                {"type": "text", "bbox": (0, 0, 50, 20), "text": "God tekst", "score": 0.99},
                {"type": "text", "bbox": (0, 25, 50, 45), "text": "Uklar tekst", "score": 0.31},
            ],
        }
    ]
    package, questions = build_package_from_mineru(
        "side1.txt", NORWEGIAN_SOURCE, pages
    )
    assert len(questions) == 1
    assert questions[0].related_observation_id == "p1-b1"
    assert questions[0].cause == "low_confidence_extraction"
    assert len(package.questions) == 1
    assert package.verify() == []


def test_high_confidence_block_does_not_create_question():
    pages = [
        {
            "page_no": 1,
            "layout_blocks": [
                {"type": "text", "bbox": (0, 0, 50, 20), "text": "Klart", "score": 0.95},
            ],
        }
    ]
    _, questions = build_package_from_mineru("side1.txt", NORWEGIAN_SOURCE, pages)
    assert questions == []


def test_reparse_with_new_version_preserves_previous_history():
    pages_v1 = [
        {
            "page_no": 1,
            "layout_blocks": [
                {"type": "text", "bbox": (0, 0, 50, 20), "text": "Gammel utgave", "score": 0.9},
            ],
        }
    ]
    package_v1, _ = build_package_from_mineru(
        "side1.txt", NORWEGIAN_SOURCE, pages_v1, parser_version="1.0.0"
    )
    interpretation_v1 = InterpretationCandidate(
        interpretation_id="i-v1",
        text="Gammel tolkning",
        based_on=(package_v1.observations[0].observation_id,),
        created_by="hermes",
    )
    pipe = DocumentPipeline(package_id="reparse", previous=package_v1)
    pipe.from_source("side1.txt", NORWEGIAN_SOURCE)
    pipe.set_extraction_provenance(parser_name="mineru", parser_version="2.0.0")
    pipe.add_observation(
        _obs(pipe, "o-new", "Ny utgave", bbox=(0.0, 0.0, 50.0, 20.0))
    )
    pipe.add_interpretation(interpretation_v1)
    pipe.add_conclusion("Ny konklusjon", based_on=("i-v1",), created_by="hermes")
    package_v2 = pipe.build()

    assert package_v2.predecessor_digest == package_v1.package_digest
    assert len(package_v2.interpretations) == 1
    assert package_v2.interpretations[0].interpretation_id == "i-v1"
    assert package_v2.statements[0].stage == ReasoningStage.CONCLUSION
    assert package_v2.verify() == []

    assert package_v1.verify() == []
    assert package_v1.package_digest != package_v2.package_digest


def test_interpretation_does_not_overwrite_source():
    pipe, identity = _pipeline()
    obs = _obs(pipe, "o1", "Kilden sier dette.")
    pipe.add_observation(obs)
    pipe.add_interpretation(
        InterpretationCandidate(
            interpretation_id="i1",
            text="Kilden ser ut til å mene noe annet.",
            based_on=("o1",),
            created_by="hermes",
        )
    )
    pipe.add_conclusion(
        "Tolkningen endrer ikke kilden.",
        based_on=("i1",),
        created_by="hermes",
    )
    package = pipe.build()

    assert package.observations[0].original_text == "Kilden sier dette."
    assert package.observations[0].location.document_hash == identity.source_digest
    assert package.source_identity.source_digest == identity.source_digest
    assert len(package.observations) == 1
    assert package.verify() == []


def test_deterministic_digests_and_frozen_contracts():
    pipe, _ = _pipeline()
    obs = _obs(pipe, "o1", "Bestemt tekst.")
    pipe.add_observation(obs)
    package = pipe.build()

    pipe2, _ = _pipeline()
    obs2 = _obs(pipe2, "o1", "Bestemt tekst.")
    pipe2.add_observation(obs2)
    package2 = pipe2.build()

    assert package.observations[0].digest() == obs2.digest()

    deterministic_a = DocumentPipeline(package_id="fixed-id")
    deterministic_a.from_source("kilde.txt", NORWEGIAN_SOURCE)
    deterministic_a.set_extraction_provenance("mineru", "2.2.1")
    deterministic_a.add_observation(_obs(deterministic_a, "o1", "Bestemt tekst."))
    package_a = deterministic_a.build()

    deterministic_b = DocumentPipeline(package_id="fixed-id")
    deterministic_b.from_source("kilde.txt", NORWEGIAN_SOURCE)
    deterministic_b.set_extraction_provenance("mineru", "2.2.1")
    deterministic_b.add_observation(_obs(deterministic_b, "o1", "Bestemt tekst."))
    package_b = deterministic_b.build()

    assert package_a.package_digest == package_b.package_digest

    with pytest.raises(Exception):
        package.observations[0].original_text = "prøver å endre"


def test_chain_is_hash_linked_and_ordered():
    pipe, _ = _pipeline()
    pipe.add_observation(_obs(pipe, "o1", "Tekst A"))
    pipe.add_observation(_obs(pipe, "o2", "Tekst B"))
    pipe.add_interpretation(
        InterpretationCandidate(
            interpretation_id="i1", text="Tolkning", based_on=("o1",)
        )
    )
    pipe.add_assumption("Antakelse", based_on=("i1",))
    pipe.add_hypothesis("Hypotese", based_on=("i1",))
    pipe.add_conclusion("Konklusjon", based_on=("i1",))
    package = pipe.build()

    stages = [r.stage for r in package.chain]
    assert stages == [
        ReasoningStage.SOURCE,
        ReasoningStage.SOURCE_IDENTITY,
        ReasoningStage.STRUCTURED_EXTRACTION,
        ReasoningStage.OBSERVATION,
        ReasoningStage.INTERPRETATION,
        ReasoningStage.ASSUMPTION,
        ReasoningStage.HYPOTHESIS,
        ReasoningStage.CONCLUSION,
    ]
    for prev, record in zip(package.chain, package.chain[1:]):
        assert record.prev_digest == prev.digest()
    assert package.verify() == []


def test_chain_rejects_reordered_stages():
    pipe, _ = _pipeline()
    pipe.add_observation(_obs(pipe, "o1", "Tekst"))
    package = pipe.build()
    from docpack import ChainRecord

    reversed_chain = tuple(reversed(package.chain))
    tampered = CanonicalDocumentPackage(
        package_id="tampered",
        source_identity=package.source_identity,
        observations=package.observations,
        chain=reversed_chain,
    )
    violations = tampered.verify()
    assert any("order" in v for v in violations)
    assert any("link" in v for v in violations)


def test_package_digest_detects_tampering():
    pipe, _ = _pipeline()
    obs = _obs(pipe, "o1", "Opprinnelig.")
    pipe.add_observation(obs)
    package = pipe.build()

    tampered_obs = ExtractedObservation(
        observation_id=obs.observation_id,
        location=obs.location,
        original_text="Forfalsket.",
    )
    tampered = CanonicalDocumentPackage(
        package_id=package.package_id,
        source_identity=package.source_identity,
        observations=(tampered_obs,),
        package_digest=package.package_digest,
    )
    violations = tampered.verify()
    assert any("digest" in v for v in violations)


def test_reading_order_kept_and_challengeable():
    pipe, _ = _pipeline()
    a = _obs(pipe, "o1", "Første.", bbox=(0.0, 0.0, 10.0, 10.0), reading_order=1)
    b = _obs(pipe, "o2", "Andre.", bbox=(0.0, 20.0, 10.0, 30.0), reading_order=2)
    pipe.add_observation(a)
    pipe.add_observation(b)

    pipe.add_interpretation(
        InterpretationCandidate(
            interpretation_id="ro-1",
            text="Les i motsatt rekkefølge.",
            based_on=("o1", "o2"),
            role="reading_order_proposal",
            created_by="hermes",
        )
    )
    package = pipe.build()

    assert package.observations[0].reading_order == 1
    assert package.observations[1].reading_order == 2
    assert any(
        i.role == "reading_order_proposal" for i in package.interpretations
    )
    assert package.verify() == []


def test_human_correction_is_additive_attributable_reversible():
    pipe, _ = _pipeline()
    obs = _obs(pipe, "o1", "Original påstand.")
    pipe.add_observation(obs)
    original = InterpretationCandidate(
        interpretation_id="i-orig",
        text="Påstand A",
        based_on=("o1",),
        created_by="hermes",
    )
    pipe.add_interpretation(original)
    correction = InterpretationCandidate(
        interpretation_id="i-correction",
        text="Påstand B (rettelse)",
        based_on=("o1",),
        role="correction",
        created_by="human_reviewer",
        rationale="Original feilaktig.",
    )
    pipe.add_interpretation(correction)
    package = pipe.build()

    roles = {i.role for i in package.interpretations}
    assert {"interpretation", "correction"} <= roles
    assert package.interpretations[0].text == "Påstand A"
    assert package.interpretations[1].text == "Påstand B (rettelse)"
    assert package.interpretations[1].created_by == "human_reviewer"
    assert package.verify() == []


def test_distinct_semantic_objects_kept_separate():
    pages = [
        {
            "page_no": 1,
            "layout_blocks": [
                {"type": "text", "bbox": (0, 0, 50, 20), "text": "Løpetekst", "score": 0.99},
                {"type": "table", "bbox": (0, 30, 100, 90), "text": "|x|y|", "score": 0.95},
                {"type": "formula", "bbox": (0, 100, 60, 120), "text": "F(x)", "score": 0.9},
                {"type": "image", "bbox": (0, 130, 80, 180), "text": "", "score": 0.85},
                {"type": "caption", "bbox": (0, 185, 80, 195), "text": "Figur 1", "score": 0.9},
                {"type": "footnote", "bbox": (0, 200, 80, 210), "text": "Fotnote.", "score": 0.9},
            ],
        }
    ]
    package, _ = build_package_from_mineru("side.txt", NORWEGIAN_SOURCE, pages)
    kinds = [o.kind for o in package.observations]
    assert kinds == ["statement", "table", "formula", "diagram", "caption", "footnote"]
    assert len({o.observation_id for o in package.observations}) == 6
    assert package.verify() == []
