from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "modules" / "governed-content-operations" / "manifest.ts"
MODULE_README = ROOT / "modules" / "governed-content-operations" / "README.md"
PRODUCT_DOC = ROOT / "docs" / "products" / "GOVERNED_CONTENT_OPERATIONS.md"
EXAMPLE = ROOT / "examples" / "governed_content_operations_shadow_demo.py"


def test_manifest_uses_canonical_valo_module_and_has_no_act_permission() -> None:
    content = MANIFEST.read_text(encoding="utf-8")

    assert "import type { ValoModule }" in content
    assert "governedContentOperationsModule: ValoModule" in content
    assert "id: 'governed-content-operations'" in content
    assert "version: '0.1.0-shadow'" in content
    assert "act: true" not in content
    assert content.count("act: false") == 3
    assert "content_action_cases" in content
    assert "content_policy_profile" in content
    assert "shadow_workflow_result" in content
    assert "content_evidence_chain" in content
    assert "propose_cleared_execution" in content
    assert "requiresApproval: true" in content


def test_module_readme_does_not_claim_registry_or_execution_authority() -> None:
    content = MODULE_README.read_text(encoding="utf-8")

    assert "not a new registry or runtime" in content
    assert "All declared permissions have `act: false`" in content
    assert "canonical REHT/RACS clearance and execution-gate path" in content


def test_product_document_separates_responsibility_and_states_current_maturity() -> None:
    content = PRODUCT_DOC.read_text(encoding="utf-8")

    assert "## Responsibility boundary" in content
    assert "### CMS responsibilities" in content
    assert "### VALO responsibilities" in content
    assert "### Connector responsibilities" in content
    assert "## Current maturity" in content
    assert "Production mutation code exists, but no default configuration can activate it." in content
    assert "Actual live Sanity deployment | Not activated" in content
    assert "Production operations maturity | Incomplete" in content
    assert "A shadow simulation emits evidence links, not a fake" in content
    assert "`ExecutionReceipt`." in content
    assert "live_enabled = false" in content
    assert "writes_enabled = false" in content
    assert "not by itself a production-ready Sanity integration" in content
    assert "not an unattended production" in content


def test_executable_example_uses_packaged_demo() -> None:
    content = EXAMPLE.read_text(encoding="utf-8")

    assert "build_governed_content_demo" in content
    assert "model_dump_json" in content
    assert "report.digest()" in content
    assert "requests" not in content
    assert "credentials" not in content
