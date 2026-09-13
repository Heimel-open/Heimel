import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import unsloth_factory as uf


D = {
    "workspace": "1" * 64,
    "authority": "2" * 64,
    "state": "3" * 64,
    "admission": "4" * 64,
    "prov1": "5" * 64,
    "prov2": "6" * 64,
    "runtime": "7" * 64,
    "attestation": "8" * 64,
    "vaig": "9" * 64,
    "reht": "a" * 64,
    "racs": "b" * 64,
    "pep": "c" * 64,
    "dataset": "d" * 64,
    "adapter": "e" * 64,
    "base_model": "f" * 64,
    "trajectory1": "0" * 64,
    "trajectory2": "1" * 64,
    "trajectory3": "2" * 64,
    "trajectory_provenance": "3" * 64,
    "trajectory_admission": "4" * 64,
    "teacher_reliability": "5" * 64,
    "shift": "6" * 64,
    "model": "7" * 64,
    "execution": "8" * 64,
}


def base_request():
    return {
        "workspace": {
            "workspace_id": "workspace-42",
            "workspace_digest": D["workspace"],
            "purpose_id": "purpose:model-specialization",
            "authority_ref": "delegation:factory-42",
            "authority_receipt_digest": D["authority"],
        },
        "state_admission": {
            "status": "ADMITTED",
            "state_digest": D["state"],
            "admission_receipt_digest": D["admission"],
            "provenance": [D["prov1"], D["prov2"]],
        },
        "engine": {
            "engine_id": "unsloth",
            "repo": uf.UNSLOTH_REPO,
            "commit": uf.UNSLOTH_COMMIT,
            "runtime_digest": D["runtime"],
            "attestor": "runtime-attestor:test",
            "attestation_receipt_digest": D["attestation"],
        },
        "governance": [
            {"stage": "VAIG", "decision": "ALLOW", "receipt_digest": D["vaig"]},
            {"stage": "reht", "decision": "ALLOW", "receipt_digest": D["reht"]},
            {"stage": "RACS", "decision": "ALLOW", "receipt_digest": D["racs"]},
            {"stage": "PEP", "decision": "ALLOW", "receipt_digest": D["pep"]},
        ],
        "training_spec": {
            "base_model": "meta-llama/example",
            "dataset_digest": D["dataset"],
            "objective": "bounded function specialization",
            "output_name": "candidate-v1",
            "parameters": {"epochs": 1, "learning_rate": 0.0002},
        },
        "attempt": 1,
        "auto_promote": False,
        "authority_sources": ["workspace_authority"],
    }


def reopd_recipe():
    return {
        "name": "reopd",
        "base_model_digest": D["base_model"],
        "teacher": {
            "version": "teacher-v3.2",
            "reliability": 0.97,
            "minimum_reliability": 0.90,
            "reliability_receipt_digest": D["teacher_reliability"],
        },
        "trajectories": [
            {
                "trajectory_digest": D["trajectory1"],
                "provenance_receipt_digest": D["trajectory_provenance"],
                "admission_receipt_digest": D["trajectory_admission"],
                "admission_status": "ADMITTED",
                "authorized_for_training": True,
            }
        ],
        "prefix_sampling": {
            "schedule": "step_decay",
            "initial_probability": 1.0,
            "decay_factor": 0.5,
            "decay_steps": 100,
            "minimum_probability": 0.1,
        },
        "distribution_shift_measurements": [
            {
                "metric": "state_occupancy_js_divergence",
                "value": 0.12,
                "measurement_receipt_digest": D["shift"],
            }
        ],
        "environment_mode": "offline_replay",
        "live_environment_calls": False,
        "consequence_bearing_tool_calls": False,
    }


def reopd_request():
    request = base_request()
    request["training_spec"]["recipe"] = reopd_recipe()
    return request


class UnslothFactoryTests(unittest.TestCase):
    def test_01_canonical_json_is_stable(self):
        self.assertEqual(uf.canonical_json({"b": 2, "a": 1}), uf.canonical_json({"a": 1, "b": 2}))

    def test_02_valid_request_emits_pep_handoff(self):
        handoff = uf.build_pep_handoff(base_request())
        self.assertTrue(handoff["pep_handoff"]["may_execute"])
        self.assertEqual(handoff["pep_handoff"]["max_attempts"], 1)

    def test_03_state_must_be_admitted(self):
        req = base_request(); req["state_admission"]["status"] = "CANDIDATE"
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_04_provenance_is_required(self):
        req = base_request(); req["state_admission"]["provenance"] = []
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_05_workspace_digest_is_required(self):
        req = base_request(); req["workspace"]["workspace_digest"] = ""
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_06_runtime_digest_is_attested(self):
        req = base_request(); req["engine"]["runtime_digest"] = "not-a-digest"
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_07_governance_order_is_fixed(self):
        req = base_request(); req["governance"][0], req["governance"][1] = req["governance"][1], req["governance"][0]
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_08_reht_non_allow_fails_closed(self):
        req = base_request(); req["governance"][1]["decision"] = "DEFER"
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_09_racs_step_up_fails_closed(self):
        req = base_request(); req["governance"][2]["decision"] = "STEP_UP"
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_10_pep_must_explicitly_allow(self):
        req = base_request(); req["governance"][3]["decision"] = "DENY"
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_11_hidden_retries_are_forbidden(self):
        req = base_request(); req["attempt"] = 2
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_12_training_retry_controls_are_forbidden(self):
        req = base_request(); req["training_spec"]["parameters"]["max_retries"] = 3
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_13_automatic_promotion_is_forbidden(self):
        req = base_request(); req["auto_promote"] = True
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_14_tokens_cannot_grant_authority(self):
        req = base_request(); req["authority_sources"] = ["oauth_token"]
        with self.assertRaises(uf.GovernanceError): uf.build_pep_handoff(req)

    def test_15_external_media_adapter_is_optional_and_non_authoritative(self):
        req = base_request(); req["external_adapter"] = {"name": "njal-hansen-media-pipeline", "digest": D["adapter"], "grants_authority": False}
        handoff = uf.build_pep_handoff(req)
        self.assertEqual(handoff["external_adapter"]["role"], "optional_external_adapter")
        self.assertFalse(handoff["external_adapter"]["grants_authority"])

    def test_16_engine_is_replaceable_without_changing_governed_state(self):
        first = uf.build_pep_handoff(base_request())
        req = base_request()
        req["engine"].update({"engine_id": "other-engine", "repo": "example/engine", "commit": "f" * 40})
        second = uf.build_pep_handoff(req)
        self.assertEqual(first["workspace"], second["workspace"])
        self.assertEqual(first["state_admission"], second["state_admission"])
        self.assertEqual(first["governance"], second["governance"])
        self.assertNotEqual(first["engine"], second["engine"])

    def test_17_cli_dry_run_is_json_and_non_executing(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(base_request(), handle)
            path = handle.name
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "bin" / "valo-unsloth"), "--request", path, "--dry-run"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertTrue(output["ok"])
            self.assertTrue(output["dry_run"])
            self.assertEqual(output["handoff"]["retry_policy"], "none")
            self.assertEqual(output["handoff"]["promotion"]["mode"], "candidate_only")
        finally:
            pathlib.Path(path).unlink(missing_ok=True)

    def test_18_reopd_missing_trajectory_provenance_fails_closed(self):
        request = reopd_request()
        request["training_spec"]["recipe"]["trajectories"][0].pop(
            "provenance_receipt_digest"
        )

        with self.assertRaisesRegex(uf.GovernanceError, "provenance_receipt_digest"):
            uf.build_pep_handoff(request)

    def test_19_reopd_excludes_unauthorized_and_unadmitted_trajectories(self):
        request = reopd_request()
        trajectories = request["training_spec"]["recipe"]["trajectories"]
        trajectories.extend(
            [
                {
                    **trajectories[0],
                    "trajectory_digest": D["trajectory2"],
                    "authorized_for_training": False,
                },
                {
                    **trajectories[0],
                    "trajectory_digest": D["trajectory3"],
                    "admission_status": "CANDIDATE",
                },
            ]
        )

        recipe = uf.build_pep_handoff(request)["training_spec"]["recipe"]

        self.assertEqual(
            [item["trajectory_digest"] for item in recipe["accepted_trajectories"]],
            [D["trajectory1"]],
        )
        self.assertEqual(
            recipe["excluded_trajectory_digests"],
            sorted((D["trajectory2"], D["trajectory3"])),
        )

    def test_20_reopd_teacher_reliability_below_policy_blocks_run(self):
        request = reopd_request()
        request["training_spec"]["recipe"]["teacher"]["reliability"] = 0.70

        with self.assertRaisesRegex(uf.GovernanceError, "below the policy threshold"):
            uf.build_pep_handoff(request)

    def test_21_reopd_forbids_live_or_consequence_bearing_training_calls(self):
        for field in ("live_environment_calls", "consequence_bearing_tool_calls"):
            with self.subTest(field=field):
                request = reopd_request()
                request["training_spec"]["recipe"][field] = True
                with self.assertRaises(uf.GovernanceError):
                    uf.build_pep_handoff(request)

    def test_22_reopd_training_receipt_binds_model_dataset_and_trajectory_hashes(self):
        handoff = uf.build_pep_handoff(reopd_request())

        receipt = uf.build_candidate_training_receipt(
            handoff,
            model_digest=D["model"],
            execution_receipt_digest=D["execution"],
        )

        self.assertEqual(receipt["model_digest"], D["model"])
        self.assertEqual(receipt["dataset_digest"], D["dataset"])
        self.assertEqual(receipt["base_model_digest"], D["base_model"])
        self.assertEqual(receipt["trajectory_digests"], [D["trajectory1"]])
        self.assertEqual(len(receipt["training_receipt_digest"]), 64)

    def test_23_reopd_output_remains_candidate_only_without_authority_transfer(self):
        handoff = uf.build_pep_handoff(reopd_request())
        receipt = uf.build_candidate_training_receipt(
            handoff,
            model_digest=D["model"],
            execution_receipt_digest=D["execution"],
        )

        self.assertEqual(receipt["output"]["standing"], "CANDIDATE_ONLY")
        self.assertFalse(receipt["output"]["runtime_authority"])
        self.assertEqual(receipt["output"]["runtime_capabilities"], [])
        self.assertFalse(receipt["output"]["inherits_teacher_authority"])
        self.assertFalse(receipt["output"]["inherits_teacher_capability"])

    def test_24_successful_reopd_training_cannot_auto_promote(self):
        handoff = uf.build_pep_handoff(reopd_request())
        receipt = uf.build_candidate_training_receipt(
            handoff,
            model_digest=D["model"],
            execution_receipt_digest=D["execution"],
        )

        self.assertFalse(receipt["promotion"]["automatic"])
        self.assertTrue(receipt["promotion"]["requires_new_admission"])
        self.assertEqual(
            receipt["promotion"]["required_gates"],
            ["EVALUATION", "NEGATIVE_TESTING", "MAL_ADMISSION"],
        )


if __name__ == "__main__":
    unittest.main()
