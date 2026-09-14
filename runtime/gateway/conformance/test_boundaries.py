from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_la_identity_claim():
    assert "has no la identity" in (ROOT / "LAYER_IDENTITY.md").read_text().lower()

def test_migration_sources_are_recorded():
    text = (ROOT.parent / "MIGRATION_MANIFEST.yaml").read_text()
    for repo in [
        "valo-runtime-core",
        "valo-runtime-local",
        "valo-runtime-adapters",
        "valo-tool-adapters",
        "valo-validation",
    ]:
        assert repo in text
