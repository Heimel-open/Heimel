import unittest

from lib.workflow_harness import (
    AUTHORITY_PATH,
    DuplicatePrimitiveError,
    HeadlessWorkflowHarness,
    UnsupportedProviderError,
    WorkflowHarnessError,
    WorkflowPrimitive,
    WorkflowStep,
)


def primitive():
    return WorkflowPrimitive(
        primitive_id="factory.change",
        version=1,
        description="Discover, implement and independently review a bounded change.",
        steps=(
            WorkflowStep("discover", "repository.discovery"),
            WorkflowStep(
                "implement",
                "repository.change",
                consequence_bearing=True,
                authority_path=AUTHORITY_PATH,
            ),
            WorkflowStep("judge", "independent.review"),
        ),
        required_capabilities=("repo.read", "repo.write", "review"),
    )


class WorkflowHarnessTest(unittest.TestCase):
    def test_primitive_is_provider_neutral(self):
        p = primitive()
        self.assertNotIn("provider", p.as_dict())
        self.assertNotIn("model", p.as_dict())
        self.assertEqual(p.authority_effect, "none")

    def test_consequence_step_requires_governance_path(self):
        with self.assertRaises(WorkflowHarnessError):
            WorkflowStep("write", "repo.write", consequence_bearing=True)
        with self.assertRaises(WorkflowHarnessError):
            WorkflowStep("read", "repo.read", authority_path=AUTHORITY_PATH)

    def test_register_and_resolve(self):
        p = primitive()
        h = HeadlessWorkflowHarness((p,))
        self.assertEqual(h.resolve("factory.change@1"), p)
        self.assertEqual(h.primitive_refs(), ("factory.change@1",))

    def test_duplicate_registration_rejected(self):
        p = primitive()
        h = HeadlessWorkflowHarness((p,))
        with self.assertRaises(DuplicatePrimitiveError):
            h.register(p)

    def test_same_primitive_is_callable_from_multiple_surfaces(self):
        h = HeadlessWorkflowHarness((primitive(),))
        cli = h.invoke(
            "factory.change@1",
            run_id="r1",
            surface_id="cli",
            provider_id="openai_codex",
            actor_ref="worker-1",
            inputs={"ticket": 42},
        )
        voice = h.invoke(
            "factory.change@1",
            run_id="r2",
            surface_id="voice",
            provider_id="anthropic_claude_code",
            actor_ref="worker-2",
            inputs={"ticket": 42},
        )
        self.assertEqual(cli.primitive_ref, voice.primitive_ref)
        self.assertEqual(cli.primitive_digest, voice.primitive_digest)
        self.assertNotEqual(cli.invocation_id, voice.invocation_id)

    def test_provider_selected_per_invocation_not_definition(self):
        h = HeadlessWorkflowHarness((primitive(),))
        a = h.invoke(
            "factory.change@1",
            run_id="r1",
            surface_id="mcp",
            provider_id="openai_codex",
            actor_ref="worker",
            inputs={"x": 1},
        )
        b = h.invoke(
            "factory.change@1",
            run_id="r1",
            surface_id="mcp",
            provider_id="github_copilot",
            actor_ref="worker",
            inputs={"x": 1},
        )
        self.assertEqual(a.primitive_digest, b.primitive_digest)
        self.assertNotEqual(a.provider_id, b.provider_id)

    def test_unknown_provider_rejected(self):
        h = HeadlessWorkflowHarness((primitive(),))
        with self.assertRaises(UnsupportedProviderError):
            h.invoke(
                "factory.change@1",
                run_id="r",
                surface_id="api",
                provider_id="unknown",
                actor_ref="worker",
                inputs={},
            )

    def test_input_digest_is_deterministic(self):
        h = HeadlessWorkflowHarness((primitive(),))
        a = h.invoke(
            "factory.change@1",
            run_id="r",
            surface_id="api",
            provider_id="openai_codex",
            actor_ref="worker",
            inputs={"b": 2, "a": 1},
        )
        b = h.invoke(
            "factory.change@1",
            run_id="r",
            surface_id="api",
            provider_id="openai_codex",
            actor_ref="worker",
            inputs={"a": 1, "b": 2},
        )
        self.assertEqual(a.input_digest, b.input_digest)
        self.assertEqual(a.invocation_id, b.invocation_id)

    def test_never_grants_or_executes(self):
        h = HeadlessWorkflowHarness((primitive(),))
        self.assertFalse(h.has_authority_surface)
        self.assertFalse(h.has_execution_surface)
        for name in ("authorize", "clear", "permit", "execute", "merge"):
            self.assertFalse(hasattr(h, name), name)


if __name__ == "__main__":
    unittest.main()
