import importlib.util
import pathlib
import sys
import unittest

MODULE = pathlib.Path(__file__).parents[1] / "lib" / "provider_agent_adapters.py"
spec = importlib.util.spec_from_file_location("provider_agent_adapters", MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class ProviderAgentAdapterTests(unittest.TestCase):
    def fake_which(self, name):
        return f"/usr/bin/{name}"

    def test_catalog_has_all_first_class_providers(self):
        self.assertEqual(
            set(mod.provider_ids()),
            {
                "openai_codex",
                "anthropic_claude_code",
                "google_antigravity",
                "github_copilot",
            },
        )

    def test_codex_subscription_status_is_sanitized(self):
        def runner(argv, **kwargs):
            if tuple(argv) == ("codex", "--version"):
                return mod.CommandResult(0, "codex-cli 0.145.0\n", "")
            if tuple(argv) == ("codex", "login", "status"):
                return mod.CommandResult(0, "", "Logged in using ChatGPT\n")
            raise AssertionError(argv)

        status = mod.status(
            "openai_codex",
            environ={},
            which=self.fake_which,
            runner=runner,
        )
        self.assertEqual(status.auth_source, "chatgpt_account")
        self.assertFalse(status.fallback_used)
        self.assertEqual(status.authority_effect, "none")

    def test_codex_headless_login_uses_device_auth(self):
        self.assertEqual(
            mod.login_command("openai_codex", headless=True),
            ("codex", "login", "--device-auth"),
        )

    def test_claude_api_env_is_fallback_and_secret_is_not_returned(self):
        secret = "sk-ant-test-secret"

        def runner(argv, **kwargs):
            return mod.CommandResult(0, "2.1.206\n", "")

        status = mod.status(
            "anthropic_claude_code",
            environ={"ANTHROPIC_API_KEY": secret},
            which=self.fake_which,
            runner=runner,
        )
        payload = str(status.as_dict())
        self.assertEqual(status.auth_source, "anthropic_api")
        self.assertTrue(status.fallback_used)
        self.assertNotIn(secret, payload)

    def test_claude_without_api_key_does_not_spend_model_call_to_probe(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(tuple(argv))
            return mod.CommandResult(0, "2.1.206\n", "")

        status = mod.status(
            "anthropic_claude_code",
            environ={},
            which=self.fake_which,
            runner=runner,
        )
        self.assertEqual(calls, [("claude", "--version")])
        self.assertEqual(status.auth_state, "unknown")
        self.assertEqual(status.auth_source, "claude_account")

    def test_google_probe_uses_models_and_does_not_claim_auth_source(self):
        def runner(argv, **kwargs):
            if tuple(argv) == ("agy", "--version"):
                return mod.CommandResult(0, "1.0.7\n", "")
            if tuple(argv) == ("agy", "models"):
                return mod.CommandResult(0, "models...\n", "")
            raise AssertionError(argv)

        status = mod.status(
            "google_antigravity",
            environ={},
            which=self.fake_which,
            runner=runner,
        )
        self.assertEqual(status.auth_state, "active")
        self.assertIsNone(status.auth_source)
        self.assertEqual(status.entitlement_state, "unknown")

    def test_copilot_status_never_exposes_env_token(self):
        secret = "github_pat_secret"

        def runner(argv, **kwargs):
            return mod.CommandResult(0, "copilot version\n", "")

        status = mod.status(
            "github_copilot",
            environ={"COPILOT_GITHUB_TOKEN": secret},
            which=self.fake_which,
            runner=runner,
        )
        self.assertTrue(status.fallback_used)
        self.assertNotIn(secret, str(status.as_dict()))

    def test_execution_surfaces_are_documented_and_no_dangerous_skip(self):
        codex = mod.plan_execution("openai_codex", "fix it")
        self.assertEqual(codex.prompt_transport, "stdin")
        self.assertIn("workspace-write", codex.command_surface)
        self.assertNotIn("fix it", codex.command_surface)

        claude = mod.plan_execution("anthropic_claude_code", "fix it")
        self.assertIn("--permission-mode", claude.command_surface)
        self.assertNotIn("--dangerously-skip-permissions", claude.command_surface)

        agy = mod.plan_execution("google_antigravity", "fix it")
        self.assertNotIn("--dangerously-skip-permissions", agy.command_surface)

        copilot = mod.plan_execution("github_copilot", "fix it")
        self.assertIn("--allow-tool=write,shell", copilot.command_surface)
        self.assertEqual(copilot.prompt_transport, "stdin")
        self.assertNotIn("fix it", copilot.command_surface)

    def test_read_only_profiles_are_explicit(self):
        codex = mod.plan_execution(
            "openai_codex", "review it", execution_mode="read_only"
        )
        self.assertIn("read-only", codex.command_surface)

        claude = mod.plan_execution(
            "anthropic_claude_code", "review it", execution_mode="read_only"
        )
        self.assertIn("plan", claude.command_surface)

        copilot = mod.plan_execution(
            "github_copilot", "review it", execution_mode="read_only"
        )
        self.assertIn("--deny-tool=write,shell", copilot.command_surface)

    def test_run_receipt_hashes_prompt_and_outputs_without_secrets(self):
        captured = {}

        def runner(argv, **kwargs):
            captured["argv"] = tuple(argv)
            captured["input"] = kwargs.get("input_text")
            return mod.CommandResult(0, '{"type":"turn.completed"}\n', "")

        prompt = "implement a very secret task description"
        receipt, result = mod.run(
            "openai_codex",
            prompt,
            runner=runner,
            environ={},
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(captured["input"], prompt)
        self.assertNotIn(prompt, receipt.command_surface)
        self.assertNotIn(prompt, str(receipt.as_dict()))
        self.assertTrue(receipt.prompt_digest.startswith("sha256:"))
        self.assertEqual(receipt.authority_effect, "none")

    def test_missing_binary_is_unavailable(self):
        status = mod.status(
            "openai_codex",
            environ={},
            which=lambda _: None,
            runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError()),
        )
        self.assertFalse(status.installed)
        self.assertEqual(status.auth_state, "unavailable")

    def test_invalid_execution_mode_fails_closed(self):
        with self.assertRaises(mod.UnsupportedExecutionModeError):
            mod.plan_execution("openai_codex", "x", execution_mode="yolo")


if __name__ == "__main__":
    unittest.main()
