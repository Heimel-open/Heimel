from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from story_multiformat_renderer import (  # noqa: E402
    SCHEMA_ID,
    StoryRenderError,
    load_manifest,
    parse_manifest,
    render_all,
    render_html,
    render_pdf,
    render_pptx,
)

FIXTURE = ROOT / "tests" / "fixtures" / "story_manifest.json"


class StoryMultiformatRendererTests(unittest.TestCase):
    def test_rejects_wrong_schema(self) -> None:
        with self.assertRaises(StoryRenderError):
            parse_manifest({"schema": "wrong", "title": "x", "slides": [{"title": "y"}]})

    def test_same_source_digest_is_bound_into_all_formats(self) -> None:
        manifest = load_manifest(FIXTURE)
        html = render_html(manifest)
        pdf = render_pdf(manifest)
        pptx = render_pptx(manifest)
        digest = manifest.source_sha256.encode()
        self.assertIn(manifest.source_sha256, html)
        self.assertIn(digest, pdf)
        with zipfile.ZipFile(io.BytesIO(pptx)) as archive:
            core = archive.read("docProps/core.xml")
        self.assertIn(digest, core)

    def test_outputs_are_real_file_formats_and_deterministic(self) -> None:
        manifest = load_manifest(FIXTURE)
        self.assertTrue(render_pdf(manifest).startswith(b"%PDF-1.4"))
        pptx1 = render_pptx(manifest)
        pptx2 = render_pptx(manifest)
        self.assertEqual(pptx1, pptx2)
        with zipfile.ZipFile(io.BytesIO(pptx1)) as archive:
            names = set(archive.namelist())
            self.assertIn("ppt/presentation.xml", names)
            self.assertIn("ppt/slides/slide1.xml", names)
            self.assertIn("ppt/slides/slide2.xml", names)

    def test_render_all_writes_three_outputs(self) -> None:
        manifest = load_manifest(FIXTURE)
        with tempfile.TemporaryDirectory() as tmp:
            outputs = render_all(manifest, tmp, "brief")
            self.assertEqual(set(outputs), {"html", "pdf", "pptx"})
            self.assertTrue(all(path.exists() and path.stat().st_size > 100 for path in outputs.values()))

    def test_fixture_uses_current_schema(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema"], SCHEMA_ID)


if __name__ == "__main__":
    unittest.main()
