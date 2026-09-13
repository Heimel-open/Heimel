from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import p12_runner as p12
import p12_payload_ablation as ablation


class PayloadAblationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p12.MOCK_MODE = True
        cls.root = Path(__file__).resolve().parent
        cls.tasks = p12.load_tasks(cls.root / "tasks.json")
        cls.task = next(
            task for task in cls.tasks
            if task["family"] in {"T1", "T2", "T4"} and not task.get("late_evidence")
        )

    def test_payload_variants_are_deterministic_and_structurally_distinct(self) -> None:
        records = [
            {
                "role": "hypothesis",
                "raw": "raw hypothesis",
                "packet": {
                    "observation": "obs",
                    "relevance_context": "ctx",
                    "uncertainty": "unc",
                    "state_delta": "delta",
                    "provenance": "K1",
                },
            },
            {
                "role": "evidence",
                "raw": "raw evidence",
                "packet": {
                    "observation": "obs2",
                    "relevance_context": "ctx2",
                    "uncertainty": "unc2",
                    "state_delta": "delta2",
                    "provenance": "K2",
                },
            },
            {
                "role": "counter",
                "raw": "raw counter",
                "packet": {
                    "observation": "obs3",
                    "relevance_context": "ctx3",
                    "uncertainty": "unc3",
                    "state_delta": "delta3",
                    "provenance": "K3",
                },
            },
        ]
        payloads = {
            variant: ablation.build_payload(variant, records, "T1-TEST")
            for variant in ablation.PAYLOAD_VARIANTS
        }
        self.assertLess(len(payloads["P2"]), len(payloads["P1"]))
        self.assertNotIn('"provenance"', payloads["P3"])
        self.assertNotIn('"uncertainty"', payloads["P4"])
        self.assertNotIn('"relevance_context"', payloads["P5"])
        self.assertNotEqual(payloads["P6"], payloads["P1"])
        self.assertEqual(
            payloads["P6"],
            ablation.build_payload("P6", records, "T1-TEST"),
        )

    def test_mock_task_shares_upstream_calls_across_all_variants(self) -> None:
        self.assertTrue(p12.MOCK_MODE, "test suite must run with P12_MOCK_MODE=true")
        outputs = ablation.run_payload_ablation_task(self.task)
        self.assertEqual(7, len(outputs))
        self.assertEqual(set(ablation.PAYLOAD_VARIANTS), {x["payload_variant"] for x in outputs})
        self.assertEqual(1, len({x["shared_source_fingerprint"] for x in outputs}))
        self.assertEqual(7, len({x["payload_sha256"] for x in outputs}))
        self.assertTrue(all(x["shared_upstream"] for x in outputs))
        self.assertTrue(all(x["synthesis_budget"] > 0 for x in outputs))

    def test_mock_experiment_writes_preregistration_and_report(self) -> None:
        self.assertTrue(p12.MOCK_MODE, "test suite must run with P12_MOCK_MODE=true")
        with tempfile.TemporaryDirectory() as tmp:
            old_root = p12.RUN_ROOT
            p12.RUN_ROOT = Path(tmp)
            try:
                run_dir = ablation.run_payload_ablation_experiment(
                    self.tasks,
                    task_limit=1,
                    variants=ablation.PAYLOAD_VARIANTS,
                    label="unit",
                )
            finally:
                p12.RUN_ROOT = old_root

            prereg = run_dir / "payload_ablation_preregistration.json"
            report_path = run_dir / "payload_ablation_report.json"
            self.assertTrue(prereg.exists())
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIn("summary", report)
            self.assertEqual(set(ablation.PAYLOAD_VARIANTS), set(report["summary"]))
            self.assertFalse(report["preliminary_h_mesh_7_pass"])

    def test_late_evidence_is_explicitly_excluded_from_v1(self) -> None:
        late_task = next(task for task in self.tasks if task.get("late_evidence"))
        with self.assertRaisesRegex(ValueError, "excludes late-evidence"):
            ablation.run_payload_ablation_task(late_task)


if __name__ == "__main__":
    unittest.main()
