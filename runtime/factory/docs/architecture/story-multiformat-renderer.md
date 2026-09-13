# Story multiformat renderer

VALO Factory treats the story manifest as the canonical source and the delivery formats as projections.

`story_manifest.json -> standalone HTML + PDF + PPTX`

The renderer is intentionally provider-neutral and uses only the Python standard library. It does not call an LLM, browser, office suite or external service.

## Invariants

1. One canonical JSON object is normalized and SHA-256 hashed before rendering.
2. HTML, PDF and PPTX each carry the same `source_sha256` so recipients can prove that the three files came from the same story state.
3. HTML is self-contained: no remote scripts, fonts, stylesheets or image dependencies are required.
4. PDF and PPTX are deterministic for a given manifest.
5. Rendering is presentation work only. It does not mint authority, change REHT/RACS semantics or execute external effects.

## CLI

```bash
bin/valo-story-render tests/fixtures/story_manifest.json --output-dir dist/story --stem storybrief
```

The command writes `storybrief.html`, `storybrief.pdf` and `storybrief.pptx`, then prints the shared source digest and output paths as JSON.

## Delivery model

HTML is the primary live/browser artifact. PDF is the stable mail/archive snapshot. PPTX is the editable presentation fallback. The digest binding lets all three travel together without becoming separate narrative versions.
