import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parent.parent
PROFILE = ROOT / "config" / "muse-glimmer-local-model.json"
PROVIDER = ROOT / "bin" / "valo-model-provider"


class MuseGlimmerLocalModelTests(unittest.TestCase):
    def test_profile_preserves_execution_authority_boundary(self):
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(profile["schema"], "valo.local-model-profile.v1")
        self.assertEqual(profile["status"], "adopted")
        self.assertEqual(profile["governance"]["authority_effect"], "none")
        self.assertFalse(profile["governance"]["model_is_authority_source"])
        self.assertFalse(profile["governance"]["harness_is_authority_source"])
        self.assertEqual(
            profile["governance"]["required_execution_path"],
            ["VAIG", "reht", "gateway", "Veritas"],
        )

    def test_profile_uses_existing_openai_compatible_provider_contract(self):
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        runtime = profile["runtime"]
        self.assertTrue(runtime["openai_compatible"])
        self.assertEqual(runtime["preferred"], "llama.cpp")
        self.assertEqual(
            runtime["valo_environment"]["VALO_MODEL_ID"],
            profile["model"]["model_id"],
        )

        request = {"messages": [{"role": "user", "content": "ping"}], "max_tokens": 8}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(request, handle)
            request_path = handle.name
        try:
            env = os.environ.copy()
            env.update(runtime["valo_environment"])
            result = subprocess.run(
                [sys.executable, str(PROVIDER), "--request", request_path, "--check"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            checked = json.loads(result.stdout)
            self.assertEqual(checked["contract"], "valo.openai-compatible.chat.v1")
            self.assertEqual(checked["payload"]["model"], profile["model"]["model_id"])
        finally:
            os.unlink(request_path)

    def test_multimodal_messages_are_not_stripped_by_provider_adapter(self):
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        request = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe the image"},
                        {"type": "image_url", "image_url": {"url": "https://example.invalid/image.png"}},
                    ],
                }
            ]
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(request, handle)
            request_path = handle.name
        try:
            env = os.environ.copy()
            env.update(profile["runtime"]["valo_environment"])
            result = subprocess.run(
                [sys.executable, str(PROVIDER), "--request", request_path, "--check"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            checked = json.loads(result.stdout)
            self.assertEqual(checked["payload"]["messages"], request["messages"])
        finally:
            os.unlink(request_path)


if __name__ == "__main__":
    unittest.main()
