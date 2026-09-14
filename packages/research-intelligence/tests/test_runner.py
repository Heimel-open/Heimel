import json
import tempfile
import unittest
from pathlib import Path

from heimel_research_intelligence.pipeline import SourcePolicy
from heimel_research_intelligence.runner import EvidenceStore, collect_once


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.policy = SourcePolicy(
            "eu",
            "https://commission.europa.eu/feed.xml",
            ("commission.europa.eu",),
        )

    def test_persists_and_deduplicates_across_runs(self):
        feed = b"<rss><channel><item><title>Authority sandbox</title><link>https://commission.europa.eu/r</link></item></channel></rss>"
        body = b"authority delegation evidence sandbox governance revocation permit constraint"

        def fetch(url):
            if url.endswith("feed.xml"):
                return feed, "application/xml", url
            return body, "text/plain", url

        with tempfile.TemporaryDirectory() as td:
            store = EvidenceStore(Path(td) / "evidence")
            first = collect_once([self.policy], store, threshold=12, fetch=fetch)
            second = collect_once([self.policy], store, threshold=12, fetch=fetch)
            self.assertEqual(first.accepted, 1)
            self.assertEqual(second.duplicates, 1)
            self.assertEqual(len(list(store.records_dir.glob("*.json"))), 1)

    def test_low_relevance_is_not_written(self):
        feed = b"<rss><channel><item><title>Unrelated</title><link>https://commission.europa.eu/r</link></item></channel></rss>"

        def fetch(url):
            if url.endswith("feed.xml"):
                return feed, "application/xml", url
            return b"weather and sports", "text/plain", url

        with tempfile.TemporaryDirectory() as td:
            store = EvidenceStore(Path(td) / "evidence")
            result = collect_once([self.policy], store, threshold=12, fetch=fetch)
            self.assertEqual(result.dropped, 1)
            self.assertFalse(store.index_path.exists())

    def test_source_failure_does_not_stop_other_sources(self):
        good = SourcePolicy("good", "https://commission.europa.eu/good.xml", ("commission.europa.eu",))
        bad = SourcePolicy("bad", "https://commission.europa.eu/bad.xml", ("commission.europa.eu",))
        feed = b"<rss><channel><item><title>Authority evidence</title><link>https://commission.europa.eu/r</link></item></channel></rss>"

        def fetch(url):
            if url.endswith("bad.xml"):
                raise OSError("down")
            if url.endswith("good.xml"):
                return feed, "application/xml", url
            return b"authority evidence governance sandbox permit", "text/plain", url

        with tempfile.TemporaryDirectory() as td:
            result = collect_once([bad, good], EvidenceStore(Path(td) / "evidence"), threshold=1, fetch=fetch)
            self.assertEqual(result.errors, 1)
            self.assertEqual(result.accepted, 1)

    def test_index_is_valid_json(self):
        feed = b"<rss><channel><item><title>Authority</title><link>https://commission.europa.eu/r</link></item></channel></rss>"

        def fetch(url):
            if url.endswith("feed.xml"):
                return feed, "application/xml", url
            return b"authority evidence governance", "text/plain", url

        with tempfile.TemporaryDirectory() as td:
            store = EvidenceStore(Path(td) / "evidence")
            collect_once([self.policy], store, threshold=1, fetch=fetch)
            index = json.loads(store.index_path.read_text())
            self.assertEqual(index["schema_version"], "heimel.research.index.v1")


if __name__ == "__main__":
    unittest.main()
