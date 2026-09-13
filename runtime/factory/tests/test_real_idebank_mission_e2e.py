import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "valo-one-shot-scaffold"
EVIDENCE = ROOT / "evidence" / "portfolio-runs" / "2026-08-20-volunteer-shift-swap-board"
MISSION_PATH = EVIDENCE / "idebank-mission.json"
RUN_PATH = EVIDENCE / "run-contract.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def profile(mission_snapshot: dict, run: dict) -> dict:
    mission = mission_snapshot["mission"]
    source = run["source"]
    target = run["target_baseline"]
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
            "reason": "Use the reusable one-shot catalog default; do not create a new primitive.",
        }
        for name in categories
    }
    return {
        "schema_version": "portfolio-build-profile.v1",
        "profile_id": "real-idebank-volunteer-shift-swap-board-20260820",
        "source": {
            "idea_id": mission["id"],
            "concept_version": "0.1.0",
            "map_version": "2.1.0",
            "source_ref": f"{source['repo']}:{source['path']}#{mission['id']}",
            "source_sha": source["sha"],
            "decision_ref": "nsolland/Index#full-portfolio-productization",
            "mission_id": mission["id"],
        },
        "portfolio_class": "P4_APPLICATION",
        "product_family": "applications",
        "placement": "ONE_SHOT_OUTPUT",
        "target_capability": "thin-app",
        "target_repos": [target["repo"]],
        "desired_delivery_stage": "BUILD_READY",
        "primitive_gate": {
            "result": "NEW_APPLICATION",
            "evidence": [
                f"{source['repo']}@{source['sha']}:{source['path']}#{mission['id']}",
                f"{run['upstream_evidence']['repo']}@{run['upstream_evidence']['sha']}:{run['upstream_evidence']['mission_state']}",
            ],
            "new_primitive_owner": None,
            "migration_ref": None,
            "conformance_ref": None,
        },
        "reuse_plan": reuse,
        "objective": mission["objective"],
        "scope": {
            "paths": ["missions/volunteer-shift-swap-board/prototype/"],
            "exclude": ["core/", "governance/"],
            "out_of_scope": [
                "new agent runtime",
                "new governance layer",
                "worker surveillance",
                "automatic external publication",
            ],
        },
        "required_capabilities": ["thin-web-app"],
        "dependencies": [],
        "acceptance_criteria": mission["successSignals"],
        "evidence_refs": [
            f"{run['upstream_evidence']['repo']}@{run['upstream_evidence']['sha']}:{run['upstream_evidence']['verifier_report']}",
        ],
        "risk_class": "B",
        "release_target": {
            "contract_version": "1.0.0",
            "release_version": "0.1.0",
            "target_channel": "candidate",
        },
        "requires_independent_qc": True,
        "requires_receipt": True,
        "idempotency_key": "real-idebank-volunteer-shift-swap-board-20260820",
        "authority_effect": "none",
    }


def authority(run: dict) -> dict:
    now = datetime.now(timezone.utc)
    target = run["target_baseline"]
    return {
        "principal": "founder@valo",
        "issued_via": "portfolio-productization-run",
        "authority_basis": "nsolland/Index#full-portfolio-productization",
        "source_ref": "evidence/portfolio-runs/2026-08-20-volunteer-shift-swap-board/run-contract.json",
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "authority": "delegated-founder",
        "expires_at": (now + timedelta(hours=2)).isoformat(),
        "target_base_ref": "main",
        "canonical_base_shas": {target["repo"]: target["sha"]},
    }


class RealIdebankMissionE2ETests(unittest.TestCase):
    def test_real_current_idebank_record_traverses_bound_candidate_lane(self):
        mission_snapshot = load(MISSION_PATH)
        run = load(RUN_PATH)
        mission = mission_snapshot["mission"]

        self.assertEqual(mission_snapshot["provenance"]["source_repo"], "nsolland/idebank")
        self.assertEqual(mission_snapshot["provenance"]["source_path"], "missions/seed.json")
        self.assertEqual(mission_snapshot["provenance"]["source_sha"], run["source"]["sha"])
        self.assertEqual(mission["id"], "volunteer-shift-swap-board")
        self.assertEqual(mission["status"], "READY_FOR_DECISION")
        self.assertEqual(run["factory_lane"]["authority_effect"], "none")
        self.assertIn("independent QC", run["claim_boundary"]["does_not_prove"])
        self.assertIn("production deployment", run["claim_boundary"]["does_not_prove"])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "profile.json"
            authority_path = root / "authority.json"
            output = root / "candidate"
            profile_path.write_text(json.dumps(profile(mission_snapshot, run)), encoding="utf-8")
            authority_path.write_text(json.dumps(authority(run)), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    str(profile_path),
                    str(authority_path),
                    "--factory-profile",
                    run["factory_lane"]["profile"],
                    "--app-slug",
                    mission["id"],
                    "--output-dir",
                    str(output),
                    "--verify",
                    "--target-source-sha",
                    run["target_baseline"]["sha"],
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
            self.assertEqual(payload["release_binding"]["portfolio_source_sha"], run["source"]["sha"])
            self.assertEqual(payload["release_binding"]["target_source_sha"], run["target_baseline"]["sha"])

            binding = load(output / "release-binding.json")
            candidate = load(output / "release-candidate.json")
            self.assertEqual(binding["target_source_sha"], run["target_baseline"]["sha"])
            self.assertEqual(binding["portfolio_source_sha"], run["source"]["sha"])
            self.assertEqual(candidate["state"], "CANDIDATE_BOUND")
            self.assertEqual(candidate["artifact_digest"], binding["artifact_digest"])


if __name__ == "__main__":
    unittest.main()
