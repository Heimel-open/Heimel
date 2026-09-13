import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parent.parent
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from experience_memory import (  # noqa: E402
    ADAPTER_DEJA_VU,
    ExperienceRecord,
    EvidenceBinding,
    RecallAssessment,
    assess_recall,
    deja_vu_record,
    make_recall_receipt,
)


HEX = "a" * 64


class ExperienceMemoryTests(unittest.TestCase):
    def _record(self, **overrides):
        values = {
            "record_id": "mem-1",
            "adapter_id": ADAPTER_DEJA_VU,
            "provider_id": "codex",
            "session_id": "session-1",
            "source_ref": "local://session-1",
            "source_digest": HEX,
            "content_digest": HEX,
            "observed_at_ns": 100,
            "binding": EvidenceBinding(repo="nsolland/valo-factory"),
        }
        values.update(overrides)
        return ExperienceRecord(**values)

    def test_transcript_only_memory_is_context_not_truth(self):
        assessment = assess_recall(
            self._record(),
            current_repo="nsolland/valo-factory",
            now_ns=200,
        )
        self.assertEqual(assessment.state, "raw_context")
        self.assertTrue(assessment.injectable)
        self.assertIn("independent_verification_required", assessment.reasons)
        self.assertEqual(assessment.authority_effect, "none")

    def test_evidence_binding_upgrades_context_not_authority(self):
        record = self._record(
            binding=EvidenceBinding(
                repo="nsolland/valo-factory",
                commit_sha="729d8c8",
                test_refs=("ci://run/1",),
                receipt_refs=("veritas://receipt/1",),
            )
        )
        assessment = assess_recall(
            record,
            current_repo="nsolland/valo-factory",
            now_ns=200,
        )
        self.assertEqual(assessment.state, "corroborated_context")
        self.assertTrue(assessment.injectable)
        self.assertEqual(assessment.authority_effect, "none")

    def test_stale_and_superseded_memory_are_not_injected(self):
        stale = assess_recall(
            self._record(valid_until_ns=150),
            current_repo="nsolland/valo-factory",
            now_ns=200,
        )
        superseded = assess_recall(
            self._record(superseded_by="mem-2"),
            current_repo="nsolland/valo-factory",
            now_ns=200,
        )
        self.assertEqual(stale.state, "stale")
        self.assertFalse(stale.injectable)
        self.assertEqual(superseded.state, "superseded")
        self.assertFalse(superseded.injectable)

    def test_cross_repo_memory_requires_independent_verification(self):
        record = self._record(binding=EvidenceBinding(repo="nsolland/other"))
        assessment = assess_recall(
            record,
            current_repo="nsolland/valo-factory",
            now_ns=200,
        )
        self.assertEqual(assessment.state, "cross_repo_context")
        self.assertTrue(assessment.injectable)
        self.assertIn("independent_verification_required", assessment.reasons)

    def test_deja_vu_normalization_is_digest_bound_and_non_authoritative(self):
        record = deja_vu_record(
            record_id="deja-1",
            provider_id="claude-code",
            session_id="s-7",
            source_ref="deja://s-7",
            source_material="sanitized transcript source",
            recalled_context="prior decision context",
            observed_at_ns=123,
            repo="nsolland/valo-factory",
            file_refs=("lib/example.py",),
        )
        self.assertEqual(record.adapter_id, ADAPTER_DEJA_VU)
        self.assertEqual(record.authority_effect, "none")
        self.assertEqual(len(record.source_digest), 64)
        self.assertEqual(len(record.content_digest), 64)

    def test_recall_receipt_does_not_persist_raw_query_or_context(self):
        assessment = assess_recall(
            self._record(),
            current_repo="nsolland/valo-factory",
            now_ns=200,
        )
        receipt = make_recall_receipt(
            query="secret query text",
            adapter_id=ADAPTER_DEJA_VU,
            assessments=(assessment,),
            injected_context="sensitive recalled context",
            created_at_ns=300,
        )
        encoded = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("secret query text", encoded)
        self.assertNotIn("sensitive recalled context", encoded)
        self.assertEqual(receipt["authority_effect"], "none")
        self.assertEqual(len(receipt["query_digest"]), 64)
        self.assertEqual(len(receipt["injected_context_digest"]), 64)

    def test_adapter_registry_and_schema_lock_authority_effect(self):
        registry = json.loads(
            (ROOT / "config" / "experience-memory-adapters.json").read_text(
                encoding="utf-8"
            )
        )
        deja = next(item for item in registry["adapters"] if item["id"] == ADAPTER_DEJA_VU)
        self.assertEqual(deja["authority_effect"], "none")
        self.assertFalse(deja["required_runtime_dependency"])
        self.assertIn("stale_or_superseded_memory_is_not_injected", deja["requirements"])

        schema = json.loads(
            (ROOT / "schemas" / "experience-memory-record.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["properties"]["authority_effect"]["const"], "none")
        self.assertIn("binding", schema["required"])

    def test_authority_effect_cannot_be_changed(self):
        with self.assertRaises(ValueError):
            self._record(authority_effect="allow")
        with self.assertRaises(ValueError):
            RecallAssessment(
                record_id="mem-1",
                state="raw_context",
                injectable=True,
                reasons=("test",),
                authority_effect="allow",
            )


if __name__ == "__main__":
    unittest.main()
