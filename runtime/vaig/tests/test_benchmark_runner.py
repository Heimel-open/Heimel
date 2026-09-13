"""
P0.6 (runner): SAGE calibration must be computed over real benchmark data.

Verifies that the benchmark runner loads a JSONL dataset, scores every row
with an instrument, and reduces the (label, score) pairs to a measured
CalibrationProfile via the SAGE metrics.
"""

import os

import pytest

from vaig.benchmark_runner import (
    BenchmarkRow,
    load_benchmark,
    run_calibration,
)
from vaig.instruments.base import InstrumentBase


EXAMPLE_BENCHMARK = os.path.join(
    os.path.dirname(__file__), "fixtures", "sample_benchmark.jsonl"
)


class _LabelEchoInstrument(InstrumentBase):
    """Echoes the row label as the score (perfect calibration)."""

    name = "label-echo"
    version = "1.0"

    def score(self, prompt, response, generate_fn=None, judge_fn=None):
        # response carries the numeric label for this test instrument.
        return float(response)


class _InvertedInstrument(InstrumentBase):
    """Returns the wrong way round (inverted ranking)."""

    name = "inverted"
    version = "1.0"

    def score(self, prompt, response, generate_fn=None, judge_fn=None):
        return 1.0 - float(response)


def _rows_with_numeric_response():
    """Wrap example rows so the stub instrument can read the label."""
    base = load_benchmark(EXAMPLE_BENCHMARK)
    out = []
    for r in base:
        out.append(BenchmarkRow(prompt=r.prompt, response=str(r.label), label=r.label))
    return out


def test_example_benchmark_file_exists_and_loads():
    assert os.path.exists(EXAMPLE_BENCHMARK)
    rows = load_benchmark(EXAMPLE_BENCHMARK)
    assert len(rows) == 6
    assert all(r.label in (0, 1) for r in rows)
    assert any(r.label == 0 for r in rows)
    assert any(r.label == 1 for r in rows)


def test_runner_produces_perfectly_calibrated_profile():
    rows = _rows_with_numeric_response()
    profile = run_calibration(
        _LabelEchoInstrument(),
        rows,
        benchmark_id="sample",
        profile_id="sage-sample",
    )
    assert profile.n_samples == 6
    assert profile.benchmark_id == "sample"
    # score == label everywhere -> Brier 0, ECE 0, AUROC 1.
    assert profile.brier == 0.0
    assert profile.ece == 0.0
    assert profile.auroc == 1.0


def test_runner_detects_inverted_ranking():
    rows = _rows_with_numeric_response()
    profile = run_calibration(
        _InvertedInstrument(),
        rows,
        benchmark_id="sample",
        profile_id="sage-sample-inv",
    )
    # Inverted: positives score low, negatives score high -> AUROC 0.0.
    assert profile.auroc == 0.0
    assert profile.brier > 0.0


def test_load_benchmark_rejects_bad_label(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"prompt": "x", "response": "y", "label": 2}\n')
    with pytest.raises(ValueError):
        load_benchmark(str(bad))


def test_load_benchmark_rejects_empty(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n\n")
    with pytest.raises(ValueError):
        load_benchmark(str(empty))
