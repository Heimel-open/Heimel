import unittest
from datetime import datetime, timedelta, timezone

from lib.build_order_intake import (
    ACCEPTED,
    ALREADY_PROCESSED,
    NEEDS_HUMAN,
    AUTHORITY_METADATA_FIELDS,
    BuildOrderV1,
    MemoryIntakeRegistry,
    intake,
    mission_id,
    normalize,
    validate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_order(**overrides):
    now = _now()
    data = {
        "build_order_id": "BO-2026-001",
        "issued_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
        "principal": "founder@valo",
        "issued_via": "github-issue",
        "authority": "delegated-founder",
        "authority_basis": "nsolland/nsolland-valo-control#policy/2026-08-01",
        "source_ref": "nsolland/Index#build-order-bo-2026-001",
        "target_repo": "nsolland/valo-factory",
        "target_base_ref": "main",
        "objective": "Implement the BuildOrderV1 intake validator.",
        "owned_files": ["lib/build_order_intake.py"],
        "dependencies": [],
        "acceptance_criteria": [
            "intake validates schema",
            "idempotency key deduplicates",
        ],
        "risk_hints": [],
        "requires_independent_qc": True,
        "requires_receipt": True,
        "idempotency_key": "intake-validator-2026-08-08-1",
    }
    data.update(overrides)
    return data


class BuildOrderIntakeTests(unittest.TestCase):
    def test_valid_build_order_is_normalized_and_ready_for_repo_resolver(self):
        result = intake(build_order())
        self.assertEqual(result.status, ACCEPTED)
        self.assertEqual(result.problems, ())
        bo = result.build_order
        self.assertIsInstance(bo, BuildOrderV1)
        self.assertEqual(bo.schema_version, "build-order-v1")
        self.assertEqual(bo.target_repo, "nsolland/valo-factory")
        self.assertEqual(bo.target_base_ref, "main")
        self.assertEqual(bo.owned_files, ("lib/build_order_intake.py",))
        self.assertTrue(bo.requires_independent_qc)
        self.assertTrue(bo.requires_receipt)
        self.assertTrue(bo.canonical_base_sha is None)
        self.assertTrue(result.mission_id.startswith("mission::BO-2026-001"))
        mission = bo.as_mission(result.mission_id)
        self.assertEqual(mission["build_order_id"], "BO-2026-001")
        self.assertEqual(mission["target_repo"], "nsolland/valo-factory")
        self.assertEqual(mission["authority_effect"], "none")

    def test_missing_authority_basis_is_needs_human(self):
        result = intake(build_order(authority_basis=""))
        self.assertEqual(result.status, NEEDS_HUMAN)
        self.assertIn(
            "NEEDS_HUMAN: missing authority_basis", result.problems
        )
        self.assertIsNone(result.mission_id)

    def test_missing_target_repo_is_needs_human(self):
        result = intake(build_order(target_repo=""))
        self.assertEqual(result.status, NEEDS_HUMAN)
        self.assertIn("NEEDS_HUMAN: missing target_repo", result.problems)
        self.assertIsNone(result.mission_id)

    def test_no_delimited_scope_is_needs_human(self):
        result = intake(
            build_order(owned_files=[], scope={"paths": [".", "*"]})
        )
        self.assertEqual(result.status, NEEDS_HUMAN)
        self.assertTrue(
            any("no delimited scope" in p for p in result.problems)
        )

    def test_scope_may_be_explicit_allowed_paths(self):
        result = intake(
            build_order(owned_files=[], scope={"paths": ["src/factory/"]})
        )
        self.assertEqual(result.status, ACCEPTED)
        self.assertEqual(result.build_order.scope.paths, ("src/factory/",))

    def test_repeated_intake_same_key_creates_no_new_mission(self):
        registry = MemoryIntakeRegistry()
        first = intake(build_order(), registry=registry)
        second = intake(build_order(), registry=registry)
        self.assertEqual(first.status, ACCEPTED)
        self.assertEqual(second.status, ALREADY_PROCESSED)
        self.assertEqual(second.prior_mission_id, first.mission_id)
        self.assertEqual(len(registry.missions), 1)

    def test_different_key_creates_separate_mission(self):
        registry = MemoryIntakeRegistry()
        first = intake(
            build_order(idempotency_key="key-a"), registry=registry
        )
        second = intake(
            build_order(idempotency_key="key-b"), registry=registry
        )
        self.assertEqual(first.status, ACCEPTED)
        self.assertEqual(second.status, ACCEPTED)
        self.assertNotEqual(first.mission_id, second.mission_id)
        self.assertEqual(len(registry.missions), 2)

    def test_authority_fields_are_data_not_executable_authority(self):
        bo = normalize(build_order())
        self.assertEqual(bo.authority_effect, "none")
        for field in AUTHORITY_METADATA_FIELDS:
            self.assertIn(field, bo.to_dict())

        claimed = build_order(
            authority="self-claim",
            issued_via="chat",
            authority_basis="",
        )
        result = intake(claimed)
        self.assertEqual(result.status, NEEDS_HUMAN)
        self.assertTrue(
            any("missing authority_basis" in p for p in result.problems)
        )
        self.assertEqual(result.build_order.authority, "self-claim")
        self.assertEqual(result.build_order.issued_via, "chat")
        self.assertEqual(result.build_order.authority_effect, "none")

    def test_expired_build_order_is_rejected(self):
        result = intake(build_order(expires_at="2020-01-01T00:00:00+00:00"))
        self.assertEqual(result.status, NEEDS_HUMAN)
        self.assertTrue(any("expired" in p for p in result.problems))

    def test_missing_idempotency_key_is_needs_human(self):
        result = intake(build_order(idempotency_key=""))
        self.assertEqual(result.status, NEEDS_HUMAN)
        self.assertTrue(
            any("idempotency_key" in p for p in result.problems)
        )

    def test_normalize_defaults_target_base_ref_and_booleans(self):
        bo = normalize(build_order(target_base_ref=None))
        self.assertEqual(bo.target_base_ref, "main")
        self.assertTrue(bo.requires_independent_qc)
        self.assertTrue(bo.requires_receipt)

    def test_mission_id_is_deterministic(self):
        a = mission_id(normalize(build_order()))
        b = mission_id(normalize(build_order()))
        self.assertEqual(a, b)

    def test_validate_returns_problems_without_raising(self):
        problems = validate(normalize({}))
        self.assertTrue(problems)
        self.assertTrue(any("target_repo" in p for p in problems))
        self.assertTrue(any("authority_basis" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
