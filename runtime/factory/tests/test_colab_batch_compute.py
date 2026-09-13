from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lib.colab_batch_compute import (
    AUTHORITY_EFFECT,
    ColabBatchError,
    ColabBatchRequest,
    ColabBatchRunner,
    colab_execution_profile,
)


class ColabBatchComputeTests(unittest.TestCase):
    def _script(self, root: str, name: str = "pass.py", body: str = "print('ok')\n") -> Path:
        path = Path(root) / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_build_command_for_gpu_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = self._script(tmp)
            runner = ColabBatchRunner(executable="colab")
            cmd = runner.build_command(
                ColabBatchRequest(str(script), gpu="A100", timeout_seconds=7200)
            )

            self.assertEqual(cmd[:4], ("colab", "run", "--gpu", "A100"))
            self.assertIn("--timeout", cmd)
            self.assertIn("7200", cmd)
            self.assertEqual(cmd[-1], str(script.resolve()))

    @mock.patch("lib.colab_batch_compute.shutil.which", return_value="/usr/bin/colab")
    def test_run_captures_success(self, _which):
        with tempfile.TemporaryDirectory() as tmp:
            script = self._script(tmp, "tests.py", "print('tests')\n")

            def fake_run(cmd, **kwargs):
                self.assertEqual(cmd[0:2], ["colab", "run"])
                self.assertEqual(kwargs["timeout"], 3720)
                return subprocess.CompletedProcess(cmd, 0, stdout="123 passed\n", stderr="")

            result = ColabBatchRunner(run_process=fake_run).run(
                ColabBatchRequest(
                    str(script), gpu="T4", timeout_seconds=3600, task_class="test-suite"
                )
            )

            self.assertTrue(result.ok)
            self.assertEqual(result.stdout, "123 passed\n")
            self.assertEqual(result.task_class, "test-suite")
            self.assertEqual(result.authority_effect, AUTHORITY_EFFECT)
            self.assertEqual(AUTHORITY_EFFECT, "none")

    @mock.patch("lib.colab_batch_compute.shutil.which", return_value=None)
    def test_missing_cli_fails_closed(self, _which):
        with tempfile.TemporaryDirectory() as tmp:
            script = self._script(tmp)
            with self.assertRaisesRegex(ColabBatchError, "Colab CLI not found"):
                ColabBatchRunner().run(ColabBatchRequest(str(script)))

    @mock.patch("lib.colab_batch_compute.shutil.which", return_value="/usr/bin/colab")
    def test_nonzero_remote_execution_fails_closed(self, _which):
        with tempfile.TemporaryDirectory() as tmp:
            script = self._script(tmp, body="raise SystemExit(2)\n")

            def fake_run(cmd, **kwargs):
                return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="remote test failed")

            with self.assertRaisesRegex(ColabBatchError, "remote test failed"):
                ColabBatchRunner(run_process=fake_run).run(ColabBatchRequest(str(script)))

    def test_profile_is_non_authoritative_and_heavy_compute_only(self):
        profile = colab_execution_profile("L4")
        self.assertEqual(profile["provider_id"], "google-colab-cli")
        self.assertEqual(profile["harness_id"], "hermes")
        self.assertTrue(
            {"batch-test", "benchmark", "large-pass"}.issubset(profile["capabilities"])
        )
        self.assertEqual(profile["metadata"]["selection"], "explicit_or_heavy_compute")
        self.assertEqual(profile["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
