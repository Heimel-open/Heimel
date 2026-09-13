"""Colab CLI batch compute for tests, benchmarks and larger passes.

This module is transport only. It grants no authority and does not bypass the
normal Factory/Hermes command, policy or verification path.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

AUTHORITY_EFFECT = "none"


class ColabBatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class ColabBatchRequest:
    script_path: str
    gpu: str | None = None
    timeout_seconds: int = 3600
    keep: bool = False
    task_class: str = "large-pass"


@dataclass(frozen=True)
class ColabBatchResult:
    returncode: int
    stdout: str
    stderr: str
    command: tuple[str, ...]
    task_class: str
    authority_effect: str = AUTHORITY_EFFECT

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class ColabBatchRunner:
    """Run one local Python file remotely with ``colab run``.

    ``colab run`` owns provisioning and teardown, making it the default for
    isolated test suites, benchmarks and heavy analysis passes. Persistent
    sessions are deliberately not used here.
    """

    def __init__(
        self,
        executable: str | None = None,
        run_process: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.executable = executable or os.environ.get("COLAB_CLI_BIN") or "colab"
        self._run_process = run_process

    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def build_command(self, request: ColabBatchRequest) -> tuple[str, ...]:
        script = Path(request.script_path).expanduser().resolve()
        if not script.is_file():
            raise ColabBatchError(f"script not found: {script}")
        if request.timeout_seconds <= 0:
            raise ColabBatchError("timeout_seconds must be positive")

        cmd: list[str] = [self.executable, "run"]
        if request.gpu:
            cmd.extend(["--gpu", request.gpu])
        if request.keep:
            cmd.append("--keep")
        cmd.extend(["--timeout", str(request.timeout_seconds), str(script)])
        return tuple(cmd)

    def run(self, request: ColabBatchRequest) -> ColabBatchResult:
        if not self.available():
            raise ColabBatchError(f"Colab CLI not found: {self.executable}")
        cmd = self.build_command(request)
        try:
            completed = self._run_process(
                list(cmd),
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds + 120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ColabBatchError(
                f"Colab batch exceeded local watchdog ({request.timeout_seconds + 120}s)"
            ) from exc

        result = ColabBatchResult(
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            command=cmd,
            task_class=request.task_class,
        )
        if not result.ok:
            detail = (result.stderr or result.stdout or "unknown error").strip()[-1200:]
            raise ColabBatchError(f"Colab batch failed ({result.returncode}): {detail}")
        return result


def colab_execution_profile(gpu: str = "T4") -> dict:
    """Factory routing metadata for explicit heavy-compute selection."""
    return {
        "profile_id": f"colab-cli-{gpu.lower()}-batch",
        "handler": "lib.colab_batch_compute:ColabBatchRunner",
        "provider_id": "google-colab-cli",
        "harness_id": "hermes",
        "runtime_id": "colab-ephemeral",
        "model_id": "none",
        "sandbox_id": "colab-vm",
        "capabilities": ["batch-test", "benchmark", "large-pass", "gpu-compute"],
        "metadata": {
            "accelerator": gpu,
            "lifecycle": "ephemeral",
            "selection": "explicit_or_heavy_compute",
        },
        "authority_effect": AUTHORITY_EFFECT,
    }
