import importlib.machinery
import importlib.util
import json
import os
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader("valo_model_provider", str(ROOT / "bin" / "valo-model-provider"))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
provider = importlib.util.module_from_spec(SPEC)
sys.modules[LOADER.name] = provider
LOADER.exec_module(provider)


class ProviderContractTests(unittest.TestCase):
    def setUp(self):
        self.workflow_request = {
            "messages": [
                {"role": "system", "content": "Return a deterministic decision."},
                {"role": "user", "content": "Evaluate action A."},
            ],
            "temperature": 0,
            "seed": 42,
        }

    def test_provider_swap_changes_only_transport_configuration(self):
        providers = [
            provider.ProviderConfig("https://api.openai.com/v1", "commercial-model", "a"),
            provider.ProviderConfig("https://hosted.example/v1", "open-model", "b"),
            provider.ProviderConfig("http://127.0.0.1:8000/v1", "local-model", ""),
        ]
        payloads = [provider.request_payload(config, self.workflow_request) for config in providers]
        for payload in payloads:
            self.assertEqual(payload["messages"], self.workflow_request["messages"])
            self.assertEqual(payload["temperature"], 0)
            self.assertEqual(payload["seed"], 42)
        self.assertEqual([p["model"] for p in payloads], [c.model for c in providers])

    def test_canonical_request_digest_is_stable(self):
        config = provider.ProviderConfig("https://provider.example/v1", "model-a", "secret")
        first = provider.canonical_json(provider.request_payload(config, self.workflow_request))
        reordered = {"seed": 42, "temperature": 0, "messages": self.workflow_request["messages"]}
        second = provider.canonical_json(provider.request_payload(config, reordered))
        self.assertEqual(first, second)

    def test_response_normalization_removes_provider_specific_fields(self):
        response = {
            "id": "response-1",
            "provider_extension": {"internal": True},
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "ALLOW"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
        }
        normalized = provider.normalize_response(response)
        self.assertEqual(normalized["content"], "ALLOW")
        self.assertNotIn("provider_extension", normalized)
        self.assertEqual(normalized["usage"]["total_tokens"], 11)

    def test_config_is_environment_only(self):
        env = {
            "VALO_MODEL_ENDPOINT": "https://compatible.example/v1/",
            "VALO_MODEL_ID": "qwen-example",
            "VALO_MODEL_BEARER_TOKEN": "token",
            "VALO_MODEL_TIMEOUT_SECONDS": "30",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            config = provider.ProviderConfig.from_env()
        self.assertEqual(config.endpoint, "https://compatible.example/v1")
        self.assertEqual(config.chat_completions_url, "https://compatible.example/v1/chat/completions")
        self.assertEqual(config.model, "qwen-example")
        self.assertEqual(config.timeout_seconds, 30)

    def test_token_never_enters_receipt_identity(self):
        config = provider.ProviderConfig("https://provider.example/v1", "model-a", "top-secret")
        self.assertEqual(config.endpoint_identity, "https://provider.example")
        self.assertNotIn("top-secret", json.dumps({"endpoint_identity": config.endpoint_identity, "model_id": config.model}))

    def test_invalid_endpoint_rejected(self):
        with mock.patch.dict(os.environ, {"VALO_MODEL_ENDPOINT": "file:///tmp/model", "VALO_MODEL_ID": "x"}, clear=True):
            with self.assertRaises(ValueError):
                provider.ProviderConfig.from_env()


if __name__ == "__main__":
    unittest.main()
