from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess


class BenchmarkBoundaryError(ValueError):
    """Raised when a replay step leaves the declared benchmark workspace."""


@dataclass(frozen=True)
class ReplayStep:
    argv: tuple[str, ...]
    cwd: str = "."
    env: Mapping[str, str] = field(default_factory=dict)
    expected_exit: int = 0
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.argv:
            raise ValueError("argv must contain at least one element")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True)
class ReplayCase:
    name: str
    steps: tuple[ReplayStep, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("case name must not be empty")
        if not self.steps:
            raise ValueError("case must contain at least one replay step")


@dataclass(frozen=True)
class StepResult:
    argv: tuple[str, ...]
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    expected_exit: int

    @property
    def ok(self) -> bool:
        return self.returncode == self.expected_exit


@dataclass(frozen=True)
class ReplayResult:
    name: str
    steps: tuple[StepResult, ...]

    @property
    def ok(self) -> bool:
        return bool(self.steps) and all(step.ok for step in self.steps)


Runner = Callable[..., CompletedProcess[str]]


def _resolve_workspace_cwd(workspace: Path, cwd: str) -> Path:
    root = workspace.resolve()
    candidate = (root / cwd).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise BenchmarkBoundaryError(f"cwd escapes benchmark workspace: {cwd!r}") from exc
    if not candidate.is_dir():
        raise BenchmarkBoundaryError(f"cwd is not a directory: {cwd!r}")
    return candidate


def _base_env() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
    }


def run_case(
    workspace: str | Path,
    case: ReplayCase,
    *,
    runner: Runner = subprocess.run,
    base_env: Mapping[str, str] | None = None,
) -> ReplayResult:
    """Replay a bounded command sequence, failing closed on the first mismatch.

    Benchmark utility only: it does not authorize effects and remains separate
    from Heimel's governed execution path.
    """
    root = Path(workspace).resolve()
    if not root.is_dir():
        raise BenchmarkBoundaryError("benchmark workspace must be a directory")

    results: list[StepResult] = []
    environment = dict(_base_env() if base_env is None else base_env)

    for step in case.steps:
        cwd = _resolve_workspace_cwd(root, step.cwd)
        env = environment.copy()
        env.update({str(key): str(value) for key, value in step.env.items()})

        completed = runner(
            list(step.argv),
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
            check=False,
        )
        result = StepResult(
            argv=step.argv,
            cwd=str(cwd),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            expected_exit=step.expected_exit,
        )
        results.append(result)

        if not result.ok:
            break

    return ReplayResult(name=case.name, steps=tuple(results))
