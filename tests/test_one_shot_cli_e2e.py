import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "valo-one-shot-scaffold"
SOURCE_SHA = "a" * 40
BASE_SHA = "b" * 40
TARGET_SHA = "c" * 40


def profile():
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
    return {
        "schema_version": "portfolio-build-profile.v1",
        "profile_id": "cli-e2e-community-001",
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
        "idempotency_key": "cli-e2e-community-001",
        "authority_effect": "none",
    }


def authority():
    now = datetime.now(timezone.utc)
    return {
        "principal": "founder@valo",
        "issued_via": "portfolio-command",
        "authority_basis": "nsolland/nsolland-valo-control#portfolio-build",
        "source_ref": "authenticated-command:f1-cli-e2e",
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "authority": "delegated-founder",
        "expires_at": (now + timedelta(hours=2)).isoformat(),
        "target_base_ref": "main",
        "canonical_base_shas": {"nsolland/one-shot-workspace": BASE_SHA},
    }


class OneShotCliE2ETests(unittest.TestCase):
    def test_cli_compiles_scaffolds_smokes_and_binds_exact_release_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "profile.json"
            authority_path = root / "authority.json"
            output = root / "candidate"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8")
            authority_path.write_text(json.dumps(authority()), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    str(profile_path),
                    str(authority_path),
                    "--factory-profile",
                    "community-utility",
                    "--app-slug",
                    "shift-swap",
                    "--output-dir",
                    str(output),
                    "--verify",
                    "--target-source-sha",
                    TARGET_SHA,
                    "--release-version",
                    "0.1.0",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "GENERATED_BOUND_RELEASE_CANDIDATE")
            self.assertTrue(payload["verified"])
            self.assertEqual(payload["authority_effect"], "none")
            self.assertEqual(payload["release_binding"]["target_source_sha"], TARGET_SHA)
            self.assertEqual(payload["release_binding"]["portfolio_source_sha"], SOURCE_SHA)

            binding = json.loads((output / "release-binding.json").read_text(encoding="utf-8"))
            candidate = json.loads((output / "release-candidate.json").read_text(encoding="utf-8"))
            self.assertEqual(binding["target_source_sha"], TARGET_SHA)
            self.assertEqual(candidate["state"], "CANDIDATE_BOUND")
            self.assertEqual(candidate["target_source_sha"], TARGET_SHA)
            self.assertEqual(candidate["artifact_digest"], binding["artifact_digest"])
            rebound = subprocess.run(
                [sys.executable, str(output / "smoke_test.py")],
                cwd=output,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rebound.returncode, 0, rebound.stderr)

    def test_cli_refuses_partial_release_binding_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "profile.json"
            authority_path = root / "authority.json"
            output = root / "candidate"
            profile_path.write_text(json.dumps(profile()), encoding="utf-8")
            authority_path.write_text(json.dumps(authority()), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    str(profile_path),
                    str(authority_path),
                    "--factory-profile",
                    "community-utility",
                    "--app-slug",
                    "shift-swap",
                    "--output-dir",
                    str(output),
                    "--target-source-sha",
                    TARGET_SHA,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 2)
            self.assertFalse(output.exists())
            payload = json.loads(proc.stderr)
            self.assertEqual(payload["status"], "NOT_GENERATED")
            self.assertIn("must be supplied together", payload["problem"])


if __name__ == "__main__":
    unittest.main()
