import json
import unittest
from pathlib import Path

from lib.harness_provider_adapters import (
    UnsupportedHarnessModeError,
    UnsupportedHarnessProviderMappingError,
    harness_ids,
    plan_harness_execution,
)
from lib.workflow_harness import (
    AUTHORITY_PATH,
    HeadlessWorkflowHarness,
    UnsupportedHarnessError,
    WorkflowPrimitive,
    WorkflowStep,
)


ROOT = Path(__file__).parent.parent


def primitive():
    return WorkflowPrimitive(
        primitive_id="factory.jcode",
        version=1,
        description="Bounded coding mission through a replaceable harness.",
        steps=(
            WorkflowStep("inspect", "repo.read"),
            WorkflowStep(
                "change",
                "repo.write",
                consequence_bearing=True,
                authority_path=AUTHORITY_PATH,
            ),
            WorkflowStep("review", "independent.review"),
        ),
        required_capabilities=("repo.read", "repo.write", "review"),
    )


class JcodeHarnessAdapterTests(unittest.TestCase):
    def test_registry_adopts_jcode_without_authority(self):
        registry = json.loads(
            (ROOT / "config" / "harness-providers.json").read_text(encoding="utf-8")
        )
        providers = {item["harness_id"]: item for item in registry["providers"]}
        self.assertEqual(set(providers), {"native", "jcode", "muse_code"})
        jcode = providers["jcode"]
        self.assertEqual(jcode["status"], "adopted_optional")
        self.assertEqual(jcode["authority_effect"], "none")
        self.assertFalse(jcode["self_development_allowed"])
        self.assertEqual(
            jcode["required_wrapper_flags"],
            ["--quiet", "--no-update", "--no-selfdev"],
        )
        self.assertIn(
            "REHT remains the sole final authorization boundary for consequence-bearing execution.",
            registry["global_invariants"],
        )

    def test_harness_selection_is_separate_from_provider_selection(self):
        self.assertEqual(set(harness_ids()), {"native", "jcode", "muse_code"})
        plan = plan_harness_execution(
            "jcode",
            "openai_codex",
            "implement the bounded change",
        )
        self.assertEqual(plan.harness_id, "jcode")
        self.assertEqual(plan.provider_id, "openai_codex")
        self.assertIn("--provider", plan.command_surface)
        self.assertIn("openai", plan.command_surface)
        self.assertIn("--no-selfdev", plan.command_surface)
        self.assertIn("--no-update", plan.command_surface)
        self.assertNotIn("implement the bounded change", plan.command_surface)
        self.assertEqual(plan.authority_effect, "none")
        self.assertFalse(plan.self_development_allowed)

    def test_all_existing_provider_identities_map_through_jcode(self):
        expected = {
            "openai_codex": "openai",
            "anthropic_claude_code": "claude",
            "google_antigravity": "antigravity",
            "github_copilot": "copilot",
        }
        for provider_id, upstream in expected.items():
            with self.subTest(provider_id=provider_id):
                plan = plan_harness_execution("jcode", provider_id, "x")
                self.assertEqual(plan.provider_id, provider_id)
                self.assertIn(upstream, plan.command_surface)

    def test_jcode_read_only_fails_closed(self):
        with self.assertRaises(UnsupportedHarnessModeError):
            plan_harness_execution(
                "jcode",
                "openai_codex",
                "review",
                execution_mode="read_only",
            )

    def test_unknown_provider_mapping_fails_closed(self):
        with self.assertRaises(UnsupportedHarnessProviderMappingError):
            plan_harness_execution("jcode", "unknown_provider", "x")

    def test_workflow_invocation_binds_harness_identity(self):
        harness = HeadlessWorkflowHarness((primitive(),))
        native = harness.invoke(
            "factory.jcode@1",
            run_id="run-1",
            surface_id="workbench",
            provider_id="openai_codex",
            harness_id="native",
            actor_ref="worker-1",
            inputs={"ticket": 73},
        )
        jcode = harness.invoke(
            "factory.jcode@1",
            run_id="run-1",
            surface_id="workbench",
            provider_id="openai_codex",
            harness_id="jcode",
            actor_ref="worker-1",
            inputs={"ticket": 73},
        )
        self.assertEqual(native.provider_id, jcode.provider_id)
        self.assertNotEqual(native.harness_id, jcode.harness_id)
        self.assertNotEqual(native.invocation_id, jcode.invocation_id)
        self.assertEqual(jcode.as_dict()["harness_id"], "jcode")
        self.assertEqual(jcode.authority_effect, "none")

    def test_unknown_harness_rejected(self):
        harness = HeadlessWorkflowHarness((primitive(),))
        with self.assertRaises(UnsupportedHarnessError):
            harness.invoke(
                "factory.jcode@1",
                run_id="run-1",
                surface_id="api",
                provider_id="openai_codex",
                harness_id="unknown",
                actor_ref="worker-1",
                inputs={},
            )


if __name__ == "__main__":
    unittest.main()
