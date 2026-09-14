import unittest

from heimel_research_intelligence import Candidate, ResearchIntelligenceError, SourcePolicy, canonicalize_url, deduplicate, extract_text, ingest, parse_feed
from heimel_research_intelligence.cli import run


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.policy = SourcePolicy("eu", "https://commission.europa.eu/feed.xml", ("commission.europa.eu", "eur-lex.europa.eu"))

    def test_tracking_is_removed(self):
        self.assertEqual(canonicalize_url("https://EXAMPLE.com/a?utm_source=x&b=2#frag"), "https://example.com/a?b=2")

    def test_rejects_untrusted_candidate_domain(self):
        with self.assertRaises(ResearchIntelligenceError):
            ingest(Candidate("social", "https://evil.example/report"), self.policy, fetch=lambda u: (b"", "text/plain", u))

    def test_rejects_redirect_escape(self):
        with self.assertRaises(ResearchIntelligenceError):
            ingest(Candidate("eu", "https://commission.europa.eu/report"), self.policy, fetch=lambda u: (b"authority evidence", "text/plain", "https://evil.example/copy"))

    def test_hash_score_and_accept(self):
        body = b"authority delegation evidence sandbox governance revocation permit constraint"
        record = ingest(Candidate("eu", "https://commission.europa.eu/report", "Regulatory sandbox"), self.policy, fetch=lambda u: (body, "text/plain", u), threshold=12)
        self.assertEqual(record.disposition, "ACCEPT")
        self.assertTrue(record.content_sha256.startswith("sha256:"))
        self.assertGreaterEqual(record.relevance_score, 12)

    def test_deduplicates_by_content_hash(self):
        body = b"authority evidence sandbox governance"
        a = ingest(Candidate("eu", "https://commission.europa.eu/a"), self.policy, fetch=lambda u: (body, "text/plain", u), threshold=1)
        b = ingest(Candidate("eu", "https://commission.europa.eu/b"), self.policy, fetch=lambda u: (body, "text/plain", u), threshold=1)
        self.assertEqual(len(deduplicate([a, b])), 1)

    def test_html_filter_handles_malformed_script_end_tags(self):
        text = extract_text(
            b'<p>visible</p><script foo="bar">alert(1)</script foo><p>after</p>',
            "text/html",
        )
        self.assertIn("visible", text)
        self.assertNotIn("alert", text)

    def test_bad_feed_does_not_abort_other_sources(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "sources.json"
            output = Path(td) / "out.json"
            config.write_text(json.dumps({"sources": [{"source_id": "bad", "feed_url": "https://commission.europa.eu/not-feed", "allowed_domains": ["commission.europa.eu"]}]}))
            with patch("heimel_research_intelligence.cli.default_fetch", return_value=(b"<html>", "text/html", "https://commission.europa.eu/not-feed")):
                self.assertEqual(run(config, output, 12), 0)
            records = json.loads(output.read_text())["records"]
            self.assertEqual(records[0]["disposition"], "SOURCE_ERROR")

    def test_rss_and_atom_are_supported(self):
        rss = b"<rss><channel><item><title>A</title><link>https://commission.europa.eu/a</link></item></channel></rss>"
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>B</title><link href="https://commission.europa.eu/b"/></entry></feed>'
        self.assertEqual(parse_feed(rss, "eu")[0].title, "A")
        self.assertEqual(parse_feed(atom, "eu")[0].title, "B")


if __name__ == "__main__":
    unittest.main()
