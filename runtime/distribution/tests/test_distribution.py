#!/usr/bin/env python3
"""Distribution tests — structural verification without fetching component source.

The repository's current components.lock.yaml is intentionally NOT deployable while
it contains placeholder/stale pins. Tests use an explicit test-only valid-structure
manifest to exercise the positive validator/build path and separately prove that the
real lock fails closed.
"""
import json
import os
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATOR = os.path.join(ROOT, "scripts/validate-distribution")
GATES = os.path.join(ROOT, "validation/release-gates.yaml")
LOCK = os.path.join(ROOT, "components/components.lock.yaml")


def component(name, repo, sha_char, digest_char):
    return {
        "name": name,
        "repo": repo,
        "tag": "v9.9.9-test",
        "sha": sha_char * 40,
        "image": f"ghcr.io/nsolland/{name}:v9.9.9-test",
        "digest": "sha256:" + digest_char * 64,
        "required": True,
    }


def test_manifest():
    """Test-only non-placeholder pins; these are not release/artifact claims."""
    return {
        "apiVersion": "valo.distribution/v1",
        "kind": "DistributionManifest",
        "profile": "demo",
        "generated_at": "2026-08-20T00:00:00Z",
        "components": [
            component("reht", "nsolland/valo-reht", "1", "a"),
            component("vaig", "nsolland/VAIG", "2", "b"),
            component("veritas", "nsolland/Veritas", "3", "c"),
            component("gateway", "nsolland/valo-gateway", "4", "d"),
        ],
    }


def write_test_manifest():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.safe_dump(test_manifest(), f, sort_keys=False)
    f.close()
    return f.name


def test_manifest_schema():
    import jsonschema

    schema = json.load(open(os.path.join(ROOT, "schemas/distribution-manifest.schema.json")))
    jsonschema.validate(test_manifest(), schema)
    print("TEST manifest_schema: PASS")


def test_receipt_schema():
    import jsonschema

    schema = json.load(open(os.path.join(ROOT, "schemas/deployment-receipt.schema.json")))
    sample = {
        "schema": "valo.distribution/receipt/v1",
        "receipt_id": "00000000-0000-0000-0000-000000000000",
        "profile": "demo",
        "components": [
            {
                "name": "reht",
                "tag": "v9.9.9-test",
                "sha": "1" * 40,
                "digest": "sha256:" + "a" * 64,
            }
        ],
        "bundle": {"name": "b", "hash": "sha256:" + "c" * 64},
        "signer": "ci-test-only",
        "signature": "x",
        "timestamp": "2026-08-20T00:00:00Z",
    }
    jsonschema.validate(sample, schema)
    print("TEST receipt_schema: PASS")


def run_validator(manifest, profile="demo"):
    return subprocess.run(
        [
            sys.executable,
            VALIDATOR,
            "--manifest",
            manifest,
            "--bundle",
            "n/a",
            "--profile",
            profile,
            "--gates",
            GATES,
        ],
        capture_output=True,
        text=True,
    )


def test_valid_structure_fixture_passes_gates():
    path = write_test_manifest()
    try:
        r = run_validator(path)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "GATE no_placeholders: PASS" in r.stdout
        assert "GATE canonical_repo_refs: PASS" in r.stdout
    finally:
        os.unlink(path)
    print("TEST valid_structure_fixture_passes_gates: PASS")


def test_repository_lock_fails_closed_while_placeholder_or_stale():
    r = run_validator(LOCK, profile="research")
    assert r.returncode != 0, "components.lock.yaml must not validate while placeholder/stale"
    assert "GATE no_placeholders: FAIL" in r.stdout
    assert "GATE canonical_repo_refs: FAIL" in r.stdout
    print("TEST repository_lock_fails_closed_while_placeholder_or_stale: PASS")


def test_build_bundle_materializes_profile_components():
    manifest = write_test_manifest()
    with tempfile.TemporaryDirectory() as out:
        try:
            r = subprocess.run(
                [
                    sys.executable,
                    os.path.join(ROOT, "scripts/build-bundle"),
                    "--profile",
                    "demo",
                    "--out",
                    out,
                    "--manifest",
                    manifest,
                    "--validate",
                    VALIDATOR,
                    "--gates",
                    GATES,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert r.returncode == 0, r.stdout + r.stderr
            assert "BUNDLE_BUILT profile=demo components=4" in r.stdout

            bundle = os.path.join(out, "demo")
            compose = yaml.safe_load(open(os.path.join(bundle, "compose", "demo.yaml")))
            assert set(compose["services"]) == {"reht", "vaig", "veritas", "gateway"}
            for name, service in compose["services"].items():
                assert "@sha256:" in service["image"], name
                assert service["labels"]["valo.distribution.source_sha"]

            sbom = json.load(open(os.path.join(bundle, "sbom.json")))
            assert len(sbom["components"]) == 4
            assert all(c["source_sha"] for c in sbom["components"])

            provenance = json.load(open(os.path.join(bundle, "provenance.json")))
            assert provenance["signed"] is False
            assert provenance["manifest_hash"].startswith("sha256:")
            assert provenance["packaging"]
        finally:
            os.unlink(manifest)
    print("TEST build_bundle_materializes_profile_components: PASS")


def test_build_bundle_rejects_repository_lock():
    with tempfile.TemporaryDirectory() as out:
        r = subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "scripts/build-bundle"),
                "--profile",
                "research",
                "--out",
                out,
                "--manifest",
                LOCK,
                "--validate",
                VALIDATOR,
                "--gates",
                GATES,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode != 0, "build-bundle must reject current placeholder lock"
        assert "BUILD_ABORTED: validation failed" in r.stdout
    print("TEST build_bundle_rejects_repository_lock: PASS")


def test_build_bundle_rejects_profile_mismatch():
    manifest = write_test_manifest()
    with tempfile.TemporaryDirectory() as out:
        try:
            r = subprocess.run(
                [
                    sys.executable,
                    os.path.join(ROOT, "scripts/build-bundle"),
                    "--profile",
                    "research",
                    "--out",
                    out,
                    "--manifest",
                    manifest,
                    "--validate",
                    VALIDATOR,
                    "--gates",
                    GATES,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert r.returncode != 0
            assert "PROFILE_MISMATCH" in r.stdout
        finally:
            os.unlink(manifest)
    print("TEST build_bundle_rejects_profile_mismatch: PASS")


if __name__ == "__main__":
    test_manifest_schema()
    test_receipt_schema()
    test_valid_structure_fixture_passes_gates()
    test_repository_lock_fails_closed_while_placeholder_or_stale()
    test_build_bundle_materializes_profile_components()
    test_build_bundle_rejects_repository_lock()
    test_build_bundle_rejects_profile_mismatch()
    print("ALL_DISTRIBUTION_TESTS_PASS")
