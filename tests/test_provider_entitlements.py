import importlib.util
import pathlib
import sys
import unittest

MODULE = pathlib.Path(__file__).parents[1] / "lib" / "provider_entitlements.py"
spec = importlib.util.spec_from_file_location("provider_entitlements", MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class ProviderEntitlementTests(unittest.TestCase):
    def test_first_class_provider_catalog_is_complete(self):
        self.assertEqual(
            set(mod.provider_ids()),
            {
                "openai_codex",
                "anthropic_claude_code",
                "google_antigravity",
                "github_copilot",
            },
        )

    def test_subscription_source_wins_over_api_fallback(self):
        result = mod.select_entitlement(
            "openai_codex",
            [
                mod.AuthObservation(
                    "openai_api",
                    True,
                    entitlement_state="active",
                ),
                mod.AuthObservation(
                    "chatgpt_account",
                    True,
                    identity_ref="identity:chatgpt:test",
                    entitlement_state="active",
                    capabilities=("code", "patch", "code"),
                ),
            ],
        )
        self.assertEqual(result.auth_source, "chatgpt_account")
        self.assertFalse(result.fallback_used)
        self.assertEqual(result.entitlement_kind, "subscription")
        self.assertEqual(result.capabilities, ("code", "patch"))
        self.assertEqual(result.authority_effect, "none")

    def test_fallback_is_used_when_subscription_is_not_available(self):
        result = mod.select_entitlement(
            "anthropic_claude_code",
            [
                mod.AuthObservation("claude_account", False),
                mod.AuthObservation(
                    "anthropic_api",
                    True,
                    entitlement_state="active",
                    quota={"requests_remaining": 12},
                ),
            ],
        )
        self.assertEqual(result.auth_source, "anthropic_api")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.quota["requests_remaining"], 12)

    def test_unavailable_entitlement_is_skipped(self):
        result = mod.select_entitlement(
            "github_copilot",
            [
                mod.AuthObservation(
                    "github_account_copilot",
                    True,
                    entitlement_state="unavailable",
                ),
                mod.AuthObservation(
                    "github_enterprise",
                    True,
                    entitlement_state="active",
                ),
            ],
        )
        self.assertEqual(result.auth_source, "github_enterprise")
        self.assertTrue(result.fallback_used)

    def test_google_forbids_borrowed_or_reused_oauth(self):
        with self.assertRaises(mod.UnsupportedAuthSourceError):
            mod.select_entitlement(
                "google_antigravity",
                [
                    mod.AuthObservation(
                        "gemini_cli_oauth_reuse",
                        True,
                        entitlement_state="active",
                    )
                ],
            )

    def test_unknown_available_source_is_rejected(self):
        with self.assertRaises(mod.UnsupportedAuthSourceError):
            mod.select_entitlement(
                "openai_codex",
                [
                    mod.AuthObservation(
                        "unofficial_browser_cookie",
                        True,
                        entitlement_state="active",
                    )
                ],
            )

    def test_no_available_source_fails_closed(self):
        with self.assertRaises(mod.NoSupportedAuthError):
            mod.select_entitlement(
                "github_copilot",
                [
                    mod.AuthObservation("github_account_copilot", False),
                    mod.AuthObservation("github_enterprise", False),
                ],
            )

    def test_receipt_has_no_secret_fields(self):
        result = mod.select_entitlement(
            "google_antigravity",
            [
                mod.AuthObservation(
                    "google_account_antigravity",
                    True,
                    identity_ref="identity:google:test",
                    entitlement_state="unknown",
                    session_ref="session:opaque:test",
                )
            ],
        ).as_dict()
        serialized_keys = set(result)
        self.assertFalse(
            {"token", "access_token", "refresh_token", "api_key", "secret"}
            & serialized_keys
        )
        self.assertEqual(result["authority_effect"], "none")

    def test_duplicate_observation_is_rejected(self):
        with self.assertRaises(mod.ProviderEntitlementError):
            mod.select_entitlement(
                "openai_codex",
                [
                    mod.AuthObservation("chatgpt_account", True),
                    mod.AuthObservation("chatgpt_account", True),
                ],
            )

    def test_invalid_entitlement_state_is_rejected(self):
        with self.assertRaises(mod.ProviderEntitlementError):
            mod.AuthObservation(
                "chatgpt_account",
                True,
                entitlement_state="maybe",
            )


if __name__ == "__main__":
    unittest.main()
