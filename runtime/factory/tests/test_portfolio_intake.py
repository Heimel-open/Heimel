import unittest
from datetime import datetime, timedelta, timezone

from lib.portfolio_intake import (
    AuthorityContext,
    compile_profile,
    profile_digest,
    validate_profile,
)


SOURCE_SHA = "a" * 40
BASE_SHA = "b" * 40


def valid_profile(**overrides):
    reuse = {}
    for name in (
        "model_inference",
        "rendering_media",
        "auth_identity_transport",
        "scheduling_queues",
        "storage_database",
        "connectors_api_clients",
        "ui_framework",
        "deployment_runtime",
        "observability",
    ):
        reuse[name] = {
            "decision": "REUSE",
            "provider_or_component": f"commodity:{name}",
            "reason": "Existing replaceable component is sufficient.",
        }

    data = {
        "schema_version": "portfolio-build-profile.v1",
        "profile_id": "profile-roomit-001",
        "source": {
            "idea_id": "roomit-beta",
            "concept_version": "1.0.0",
            "map_version": "2.1.0",
            "source_ref": "nsolland/idebank#roomit-beta",
            "source_sha": SOURCE_SHA,
            "decision_ref": "nsolland/Index#product-surface-v1",
            "mission_id": None,
        },
        "portfolio_class": "P4_APPLICATION",
        "product_family": "applications",
        "placement": "EXISTING_P4",
        "target_capability": "thin-app-release",
        "target_repos": ["nsolland/roomit"],
        "desired_delivery_stage": "BUILD_READY",
        "primitive_gate": {
            "result": "REUSE_EXISTING",
            "evidence": ["nsolland/Index#PORTFOLIO-CORE-1"],
            "new_primitive_owner": None,
            "migration_ref": None,
            "conformance_ref": None,
        },
        "reuse_plan": reuse,
        "objective": "Prepare the existing Roomit/Phase Shift application for a bounded beta release.",
        "scope": {
            "paths": ["app/", "docs/", ".github/workflows/"],
            "exclude": ["core/"],
            "out_of_scope": ["new governance runtime", "new model router"],
        },
        "required_capabilities": ["static-pwa", "release-receipt"],
        "dependencies": [],
        "acceptance_criteria": [
            "existing product tests pass",
            "deployment candidate is reproducible",
        ],
        "evidence_refs": ["nsolland/roomit@main"],
        "risk_class": "B",
        "release_target": {
            "contract_version": "1.0.0",
            "release_version": "0.1.0",
            "target_channel": "beta",
        },
        "requires_independent_qc": True,
        "requires_receipt": True,
        "idempotency_key": "roomit-beta-v1",
        "authority_effect": "none",
    }
    data.update(overrides)
    return data


def authority_context(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "principal": "founder@valo",
        "issued_via": "portfolio-command",
        "authority": "delegated-founder",
        "authority_basis": "nsolland/nsolland-valo-control#portfolio-build",
        "source_ref": "authenticated-command:2026-08-18:roomit-beta",
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(hours=2)).isoformat(),
        "target_base_ref": "main",
        "canonical_base_shas": {"nsolland/roomit": BASE_SHA},
    }
    data.update(overrides)
    return AuthorityContext(**data)


class PortfolioIntakeTests(unittest.TestCase):
    def test_valid_profile_compiles_one_bounded_order(self):
        profile = valid_profile()
        result = compile_profile(profile, authority_context())
        self.assertTrue(result.ok, result.problems)
        self.assertEqual(len(result.build_orders), 1)
        order = result.build_orders[0]
        self.assertEqual(order.target_repo, "nsolland/roomit")
        self.assertEqual(order.canonical_base_sha, BASE_SHA)
        self.assertEqual(order.scope.paths, ("app/", "docs/", ".github/workflows/"))
        self.assertEqual(order.principal, "founder@valo")
        self.assertEqual(order.source_ref, "authenticated-command:2026-08-18:roomit-beta")
        self.assertEqual(order.authority_effect, "none")
        self.assertTrue(order.requires_independent_qc)
        self.assertTrue(order.requires_receipt)
        self.assertEqual(result.receipt.portfolio_source_sha, SOURCE_SHA)
        self.assertEqual(result.receipt.profile_digest, profile_digest(profile))
        self.assertEqual(result.receipt.authority_effect, "none")

    def test_profile_cannot_self_populate_authority(self):
        profile = valid_profile()
        profile["principal"] = "self-claimed-admin"
        problems = validate_profile(profile)
        self.assertTrue(any("unknown field" in p and "principal" in p for p in problems))
        result = compile_profile(profile, authority_context())
        self.assertFalse(result.ok)
        self.assertEqual(result.build_orders, ())

    def test_custom_required_without_evidence_fails_closed(self):
        profile = valid_profile()
        profile["reuse_plan"]["model_inference"] = {
            "decision": "CUSTOM_REQUIRED",
            "reason": "Need custom model for a claimed capability gap.",
        }
        result = compile_profile(profile, authority_context())
        self.assertFalse(result.ok)
        self.assertTrue(any("model_inference.evidence_ref" in p for p in result.problems))

    def test_custom_required_with_evidence_can_compile(self):
        profile = valid_profile()
        profile["reuse_plan"]["model_inference"] = {
            "decision": "CUSTOM_REQUIRED",
            "reason": "Measured capability gap.",
            "evidence_ref": "eval:roomit-model-gap:v1",
        }
        result = compile_profile(profile, authority_context())
        self.assertTrue(result.ok, result.problems)
        self.assertTrue(any("CUSTOM_REQUIRED" in hint for hint in result.build_orders[0].risk_hints))

    def test_new_primitive_requires_positive_evidence_and_migration_conformance(self):
        profile = valid_profile()
        profile["primitive_gate"] = {
            "result": "NEW_PRIMITIVE_ESTABLISHED",
            "evidence": [],
            "new_primitive_owner": None,
            "migration_ref": None,
            "conformance_ref": None,
        }
        result = compile_profile(profile, authority_context())
        self.assertFalse(result.ok)
        joined = "\n".join(result.problems)
        self.assertIn("positive evidence", joined)
        self.assertIn("new_primitive_owner", joined)
        self.assertIn("migration_ref", joined)
        self.assertIn("conformance_ref", joined)

    def test_new_primitive_with_required_evidence_can_compile(self):
        profile = valid_profile()
        profile["primitive_gate"] = {
            "result": "NEW_PRIMITIVE_ESTABLISHED",
            "evidence": ["formal-gap-proof:primitive-x:v1"],
            "new_primitive_owner": "nsolland/valo-kernel",
            "migration_ref": "migration:primitive-x:v1",
            "conformance_ref": "conformance:primitive-x:v1",
        }
        result = compile_profile(profile, authority_context())
        self.assertTrue(result.ok, result.problems)

    def test_missing_exact_source_sha_fails_closed(self):
        profile = valid_profile()
        profile["source"]["source_sha"] = "main"
        result = compile_profile(profile, authority_context())
        self.assertFalse(result.ok)
        self.assertTrue(any("exact lowercase 40-hex SHA" in p for p in result.problems))

    def test_legacy_archive_class_is_rejected(self):
        profile = valid_profile(portfolio_class="P6_LEGACY_ARCHIVE")
        result = compile_profile(profile, authority_context())
        self.assertFalse(result.ok)
        self.assertTrue(any("legacy/archive" in p for p in result.problems))

    def test_missing_or_wildcard_only_scope_is_rejected(self):
        profile = valid_profile(scope={"paths": ["**/*"], "exclude": [], "out_of_scope": []})
        result = compile_profile(profile, authority_context())
        self.assertFalse(result.ok)
        self.assertTrue(any("delimited non-wildcard" in p for p in result.problems))

    def test_multiple_target_repos_compile_separate_orders(self):
        profile = valid_profile(target_repos=["nsolland/roomit", "nsolland/valo-distribution"])
        context = authority_context(
            canonical_base_shas={
                "nsolland/roomit": BASE_SHA,
                "nsolland/valo-distribution": "c" * 40,
            }
        )
        result = compile_profile(profile, context)
        self.assertTrue(result.ok, result.problems)
        self.assertEqual(len(result.build_orders), 2)
        self.assertEqual(
            {order.target_repo for order in result.build_orders},
            {"nsolland/roomit", "nsolland/valo-distribution"},
        )
        self.assertEqual(len({order.build_order_id for order in result.build_orders}), 2)
        self.assertEqual(len({order.idempotency_key for order in result.build_orders}), 2)

    def test_compile_ids_are_deterministic_for_same_profile(self):
        profile = valid_profile()
        context = authority_context()
        first = compile_profile(profile, context)
        second = compile_profile(profile, context)
        self.assertEqual(first.build_orders[0].build_order_id, second.build_orders[0].build_order_id)
        self.assertEqual(first.build_orders[0].idempotency_key, second.build_orders[0].idempotency_key)
        self.assertEqual(first.receipt.profile_digest, second.receipt.profile_digest)

    def test_missing_authority_context_fails_before_build_order(self):
        result = compile_profile(valid_profile(), authority_context(authority_basis=""))
        self.assertFalse(result.ok)
        self.assertEqual(result.build_orders, ())
        self.assertTrue(any("authority_context.authority_basis" in p for p in result.problems))

    def test_profile_cannot_disable_qc_or_receipt(self):
        result = compile_profile(valid_profile(requires_independent_qc=False), authority_context())
        self.assertFalse(result.ok)
        self.assertTrue(any("requires_independent_qc" in p for p in result.problems))

        result = compile_profile(valid_profile(requires_receipt=False), authority_context())
        self.assertFalse(result.ok)
        self.assertTrue(any("requires_receipt" in p for p in result.problems))


if __name__ == "__main__":
    unittest.main()
