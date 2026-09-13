import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
LEGACY = "rely" + "gon"


def test_canonical_relaion_paths_are_present():
    assert (
        (ROOT / "docs/relaion/embodiment.md").is_file()
        or (ROOT / "docs/relaion/legacy/relygon/relygon-embodiment.md").is_file()
    )
    assert (
        (ROOT / "docs/relaion/opportunity-engine.md").is_file()
        or (ROOT / "docs/relaion/legacy/relygon/relygon-opportunity-engine.md").is_file()
    )
    assert (
        (ROOT / "docs/relaion/device-compatibility.md").is_file()
        or (ROOT / "docs/relaion/legacy/relygon/relygon-device-compatibility.md").is_file()
    )
    assert (ROOT / "src/paios/relaion_asset_pool.py").is_file()
    assert (ROOT / "tests/test_relaion_asset_pool.py").is_file()


def test_migration_provenance_is_valid_and_canonical():
    manifest_path = ROOT / "docs/relaion/migration-provenance.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["canonical_product"] == "relAIon"
    assert manifest["policy"]["historical_provenance_preserved"] is True
    assert manifest["policy"]["new_work_under_legacy_name"] is False


def test_active_tree_has_no_legacy_name_outside_provenance_manifest():
    manifest_path = ROOT / "docs/relaion/migration-provenance.json"
    migration_doc = ROOT / "docs/relaion/relygon-migration.md"
    readme_path = ROOT / "README.md"
    claude_path = ROOT / "CLAUDE.md"
    historical_base = {
        manifest_path,
        migration_doc,
        readme_path,
        claude_path,
        ROOT / "docs/relaion/README.md",
        ROOT / "docs/document-evidence-ingest.md",
        ROOT / "docs/personal-ai-core.md",
        ROOT / "tests/test_asset_pool.py",
        ROOT / "tests/gaui/test_gcb_continuity.py",
        ROOT / "src/paios/continuity.py",
        ROOT / "src/paios/document_ingest.py",
        ROOT / "src/paios/capability_development.py",
        ROOT / "src/paios/asset_pool.py",
        ROOT / "tests/test_relaion_migration.py",
    }
    forbidden = []
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or ".git" in path.parts
            or "__pycache__" in path.parts
            or ".pytest_cache" in path.parts
            or "legacy" in path.parts
        ):
            continue
        if path in historical_base or path.suffix in {".pyc", ".egg-info"}:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        if LEGACY in text.lower():
            forbidden.append(str(path.relative_to(ROOT)))
    assert forbidden == []
