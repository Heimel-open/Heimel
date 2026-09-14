from subprocess import CompletedProcess

import pytest

from research.replayable_benchmark import (
    BenchmarkBoundaryError,
    ReplayCase,
    ReplayStep,
    run_case,
)


def test_replay_preserves_order_env_and_expected_exit(tmp_path):
    calls = []

    def runner(argv, **kwargs):
        calls.append((tuple(argv), kwargs))
        return CompletedProcess(argv, 0, stdout="ok", stderr="")

    case = ReplayCase(
        name="ordered",
        steps=(
            ReplayStep(("tool-a", "one"), env={"CASE_ID": "A"}),
            ReplayStep(("tool-b", "two")),
        ),
    )

    result = run_case(tmp_path, case, runner=runner, base_env={"PATH": "/bin"})

    assert result.ok
    assert [call[0] for call in calls] == [
        ("tool-a", "one"),
        ("tool-b", "two"),
    ]
    assert calls[0][1]["env"] == {"PATH": "/bin", "CASE_ID": "A"}
    assert calls[1][1]["env"] == {"PATH": "/bin"}
    assert calls[0][1]["check"] is False
    assert calls[0][1]["capture_output"] is True


def test_replay_fails_closed_on_unexpected_exit(tmp_path):
    calls = []

    def runner(argv, **kwargs):
        calls.append(tuple(argv))
        return CompletedProcess(argv, 7, stdout="", stderr="failed")

    case = ReplayCase(
        name="fail-closed",
        steps=(
            ReplayStep(("first",)),
            ReplayStep(("must-not-run",)),
        ),
    )

    result = run_case(tmp_path, case, runner=runner)

    assert not result.ok
    assert calls == [("first",)]
    assert result.steps[0].returncode == 7
    assert result.steps[0].expected_exit == 0


def test_replay_accepts_declared_nonzero_exit(tmp_path):
    def runner(argv, **kwargs):
        return CompletedProcess(argv, 3, stdout="", stderr="expected")

    case = ReplayCase(
        name="negative-control",
        steps=(ReplayStep(("probe",), expected_exit=3),),
    )

    result = run_case(tmp_path, case, runner=runner)

    assert result.ok


def test_replay_rejects_cwd_escape_before_execution(tmp_path):
    calls = []

    def runner(argv, **kwargs):
        calls.append(tuple(argv))
        return CompletedProcess(argv, 0, stdout="", stderr="")

    case = ReplayCase(
        name="escape",
        steps=(ReplayStep(("tool",), cwd=".."),),
    )

    with pytest.raises(BenchmarkBoundaryError, match="escapes benchmark workspace"):
        run_case(tmp_path, case, runner=runner)

    assert calls == []


def test_replay_rejects_missing_cwd_before_execution(tmp_path):
    case = ReplayCase(
        name="missing",
        steps=(ReplayStep(("tool",), cwd="does-not-exist"),),
    )

    with pytest.raises(BenchmarkBoundaryError, match="not a directory"):
        run_case(tmp_path, case, runner=lambda *args, **kwargs: None)


def test_replay_step_requires_command():
    with pytest.raises(ValueError, match="argv"):
        ReplayStep(())
