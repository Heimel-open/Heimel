from inspect_ai import eval

from tofoo_relational_eval.task import (
    central_iterative,
    isolated,
    pooled_raw,
    relational_adaptive,
    structured_raw,
)


def _assert_success(logs):
    assert len(logs) == 1
    log = logs[0]
    assert log.status == "success", log.error
    assert log.samples is not None
    assert len(log.samples) == 1
    assert log.results is not None
    assert log.results.completed_samples == 1


def test_isolated_e2e_with_mockllm(tmp_path, monkeypatch):
    monkeypatch.setenv("INSPECT_DISABLE_MODEL_API", "1")
    logs = eval(
        isolated(worlds=1, participants=2, operators=2),
        model="mockllm/model",
        limit=1,
        display="none",
        log_dir=str(tmp_path / "isolated"),
    )
    _assert_success(logs)


def test_pooled_raw_e2e_with_mockllm(tmp_path, monkeypatch):
    monkeypatch.setenv("INSPECT_DISABLE_MODEL_API", "1")
    logs = eval(
        pooled_raw(worlds=1, operators=2),
        model="mockllm/model",
        limit=1,
        display="none",
        log_dir=str(tmp_path / "pooled"),
    )
    _assert_success(logs)


def test_structured_raw_e2e_with_mockllm(tmp_path, monkeypatch):
    monkeypatch.setenv("INSPECT_DISABLE_MODEL_API", "1")
    logs = eval(
        structured_raw(worlds=1, operators=2),
        model="mockllm/model",
        limit=1,
        display="none",
        log_dir=str(tmp_path / "structured"),
    )
    _assert_success(logs)


def test_central_iterative_e2e_with_mockllm(tmp_path, monkeypatch):
    monkeypatch.setenv("INSPECT_DISABLE_MODEL_API", "1")
    logs = eval(
        central_iterative(worlds=1, participants=2, operators=2, rounds=1),
        model="mockllm/model",
        limit=1,
        display="none",
        log_dir=str(tmp_path / "central"),
    )
    _assert_success(logs)


def test_relational_adaptive_e2e_with_mockllm(tmp_path, monkeypatch):
    monkeypatch.setenv("INSPECT_DISABLE_MODEL_API", "1")
    logs = eval(
        relational_adaptive(worlds=1, participants=2, operators=2, rounds=1),
        model="mockllm/model",
        limit=1,
        display="none",
        log_dir=str(tmp_path / "relational"),
    )
    _assert_success(logs)
