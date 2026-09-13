import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.one_shot_scaffold import (
    bind_release,
    build_scaffold_plan,
    load_catalog,
    materialize,
)
from lib.portfolio_intake import AuthorityContext


SOURCE_SHA = "a" * 40
BASE_SHA = "b" * 40
TARGET_SHA = "c" * 40


def profile(**overrides):
    categories = (
        "model_inference",
        "rendering_media",
        "auth_identity_transport",
        "scheduling_queues",
        "storage_database",
        "connectors_api_clients",
        "ui_framework",
        "deployment_runtime",
        "observability",
    )
    reuse = {
        name: {
            "decision": "REUSE",
            "provider_or_component": None,
            "reason": "Use the reusable one-shot catalog default.",
        }
        for name in categories
    }
    data = {
        "schema_version": "portfolio-build-profile.v1",
        "profile_id": "one-shot-community-001",
        "source": {
            "idea_id": "volunteer-shift-swap-board",
            "concept_version": "0.1.0",
            "map_version": "2.1.0",
            "source_ref": "nsolland/idebank#volunteer-shift-swap-board",
            "source_sha": SOURCE_SHA,
            "decision_ref": "nsolland/Index#product-surface-v1",
            "mission_id": "volunteer-shift-swap-board",
        },
        "portfolio_class": "P4_APPLICATION",
        "product_family": "applications",
        "placement": "ONE_SHOT_OUTPUT",
        "target_capability": "thin-app",
        "target_repos": ["nsolland/one-shot-workspace"],
        "desired_delivery_stage": "BUILD_READY",
        "primitive_gate": {
            "result": "NEW_APPLICATION",
            "evidence": ["portfolio-routing:one-shot"],
            "new_primitive_owner": None,
            "migration_ref": None,
            "conformance_ref": None,
        },
        "reuse_plan": reuse,
        "objective": "Let volunteers post a bounded shift-swap request and see available claims.",
        "scope": {
            "paths": ["app/"],
            "exclude": ["core/"],
            "out_of_scope": ["new agent runtime", "new governance layer"],
        },
        "required_capabilities": ["thin-web-app"],
        "dependencies": [],
        "acceptance_criteria": [
            "user can see the bounded task surface",
            "generated product contract preserves source lineage",
        ],
        "evidence_refs": ["nsolland/Index#product-surface-v1"],
        "risk_class": "B",
        "release_target": {
            "contract_version": "1.0.0",
            "release_version": "0.1.0",
            "target_channel": "candidate",
        },
        "requires_independent_qc": True,
        "requires_receipt": True,
        "idempotency_key": "one-shot-community-001",
        "authority_effect": "none",
    }
    data.update(overrides)
    return data


def authority(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "principal": "founder@valo",
        "issued_via": "portfolio-command",
        "authority_basis": "nsolland/nsolland-valo-control#portfolio-build",
        "source_ref": "authenticated-command:f1-test",
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "authority": "delegated-founder",
        "expires_at": (now + timedelta(hours=2)).isoformat(),
        "target_base_ref": "main",
        "canonical_base_shas": {"nsolland/one-shot-workspace": BASE_SHA},
    }
    data.update(overrides)
    return AuthorityContext(**data)


class OneShotScaffoldTests(unittest.TestCase):
    def test_catalog_contains_exactly_eight_current_profiles(self):
        catalog = load_catalog()
        self.assertEqual(
            set(catalog["profiles"]),
            {
                "accessibility-utility",
                "ageing-utility",
                "care-utility",
                "community-utility",
                "general-utility",
                "preservation-utility",
                "public-service-utility",
                "worker-utility",
            },
        )
        self.assertEqual(sum(p["mapped_records"] for p in catalog["profiles"].values()), 77)

    def test_build_plan_uses_catalog_defaults_and_has_no_direct_effect_path(self):
        plan = build_scaffold_plan(
            profile(),
            authority(),
            factory_profile="community-utility",
            app_slug="shift-swap",
        )
        self.assertEqual(plan.target_repo, "nsolland/one-shot-workspace")
        self.assertEqual(plan.authority_effect, "none")
        self.assertEqual(plan.components["deployment_runtime"], "replaceable:serverless-or-static-host")
        self.assertEqual(plan.components["storage_database"], "replaceable:managed-relational-store")
        config = json.loads(plan.files["app.config.json"])
        self.assertFalse(config["governance"]["direct_effect_path"])
        self.assertEqual(config["governance"]["authority_effect"], "none")

    def test_explicit_reuse_component_overrides_catalog_default(self):
        p = profile()
        p["reuse_plan"]["deployment_runtime"]["provider_or_component"] = "commodity:test-static-host"
        plan = build_scaffold_plan(
            p, authority(), factory_profile="community-utility", app_slug="shift-swap"
        )
        self.assertEqual(plan.components["deployment_runtime"], "commodity:test-static-host")

    def test_not_needed_stays_not_needed(self):
        p = profile()
        p["reuse_plan"]["model_inference"] = {
            "decision": "NOT_NEEDED",
            "provider_or_component": None,
            "reason": "No model is needed for this utility.",
        }
        plan = build_scaffold_plan(
            p, authority(), factory_profile="community-utility", app_slug="shift-swap"
        )
        self.assertEqual(plan.components["model_inference"], "not-needed")

    def test_custom_component_requires_upstream_evidence(self):
        p = profile()
        p["reuse_plan"]["storage_database"] = {
            "decision": "CUSTOM_REQUIRED",
            "provider_or_component": "custom:purpose-built-store",
            "reason": "Claimed gap.",
        }
        with self.assertRaisesRegex(ValueError, "not build-ready"):
            build_scaffold_plan(
                p, authority(), factory_profile="community-utility", app_slug="shift-swap"
            )

    def test_one_shot_scaffold_rejects_new_core_primitive(self):
        p = profile()
        p["primitive_gate"] = {
            "result": "NEW_PRIMITIVE_ESTABLISHED",
            "evidence": ["formal-gap-proof:x"],
            "new_primitive_owner": "nsolland/valo-kernel",
            "migration_ref": "migration:x",
            "conformance_ref": "conformance:x",
        }
        with self.assertRaisesRegex(ValueError, "cannot introduce a new core primitive"):
            build_scaffold_plan(
                p, authority(), factory_profile="community-utility", app_slug="shift-swap"
            )

    def test_one_shot_scaffold_requires_single_target_repo(self):
        p = profile(target_repos=["nsolland/one-shot-workspace", "nsolland/valo-distribution"])
        ctx = authority(
            canonical_base_shas={
                "nsolland/one-shot-workspace": BASE_SHA,
                "nsolland/valo-distribution": TARGET_SHA,
            }
        )
        with self.assertRaisesRegex(ValueError, "exactly one target"):
            build_scaffold_plan(
                p, ctx, factory_profile="community-utility", app_slug="shift-swap"
            )

    def test_materialized_candidate_passes_generated_smoke_test(self):
        plan = build_scaffold_plan(
            profile(), authority(), factory_profile="community-utility", app_slug="shift-swap"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = materialize(plan, Path(tmp) / "candidate")
            proc = subprocess.run(
                [sys.executable, str(root / "smoke_test.py")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("thin-app smoke: OK", proc.stdout)
            self.assertTrue((root / "scaffold-manifest.json").is_file())

    def test_materialize_refuses_non_empty_output(self):
        plan = build_scaffold_plan(
            profile(), authority(), factory_profile="community-utility", app_slug="shift-swap"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "candidate"
            root.mkdir()
            (root / "existing.txt").write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                materialize(plan, root)

    def test_release_binding_requires_exact_target_sha_and_binds_lineage(self):
        plan = build_scaffold_plan(
            profile(), authority(), factory_profile="community-utility", app_slug="shift-swap"
        )
        binding = bind_release(plan, target_source_sha=TARGET_SHA, release_version="0.1.0")
        self.assertEqual(binding.target_source_sha, TARGET_SHA)
        self.assertEqual(binding.portfolio_source_sha, SOURCE_SHA)
        self.assertEqual(binding.profile_digest, plan.profile_digest)
        self.assertEqual(binding.authority_effect, "none")
        self.assertEqual(len(binding.artifact_digest), 64)

        with self.assertRaisesRegex(ValueError, "exact lowercase 40-hex"):
            bind_release(plan, target_source_sha="main", release_version="0.1.0")

    def test_invalid_slug_and_unknown_profile_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "kebab-case"):
            build_scaffold_plan(
                profile(), authority(), factory_profile="community-utility", app_slug="Shift Swap"
            )
        with self.assertRaisesRegex(ValueError, "unknown one-shot"):
            build_scaffold_plan(
                profile(), authority(), factory_profile="new-platform", app_slug="shift-swap"
            )


if __name__ == "__main__":
    unittest.main()
