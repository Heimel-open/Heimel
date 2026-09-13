"""
SAGE benchmark runner (P0.6 runner).

P0.6 (full) requires the SAGE calibration metrics to be *computed over real
benchmark data*, not just declared. This module is the runner that turns a
benchmark dataset + an instrument into a measured ``CalibrationProfile``.

Data format (JSONL, one object per line)::

    {"prompt": "...", "response": "...", "label": 0}   # 0 = benign
    {"prompt": "...", "response": "...", "label": 1}   # 1 = attack / risk

The runner scores every row with the instrument (honouring generate_fn /
judge_fn the same way the ensemble does), collects (y_true=label,
y_score=score) pairs, and reduces them to the three SAGE metrics
(brier, ECE, AUROC) via ``vaig.calibration``.

The module does not ship the full 48+500 benchmark dataset (that is an
operational asset tracked in #167); it ships the runner plus a small example
file under ``benchmarks/examples/`` so the path is exercisable end to end.
"""

import json
from dataclasses import dataclass
from typing import List, Optional

from vaig.calibration import (
    CalibrationProfile,
    area_under_roc,
    brier_score,
    expected_calibration_error,
)
from vaig.instruments.base import InstrumentBase


@dataclass(frozen=True)
class BenchmarkRow:
    prompt: str
    response: str
    label: int  # 0 = benign, 1 = attack / risk


def load_benchmark(path: str) -> List[BenchmarkRow]:
    """Load a JSONL benchmark file into rows.

    Each line must be a JSON object with ``prompt``, ``response`` and a binary
    ``label`` (0 or 1). Blank lines are skipped.
    """
    rows: List[BenchmarkRow] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "prompt" not in obj or "response" not in obj or "label" not in obj:
                raise ValueError(
                    "Benchmark row must have prompt, response and label: "
                    + repr(obj)
                )
            label = int(obj["label"])
            if label not in (0, 1):
                raise ValueError("label must be 0 or 1, got " + repr(label))
            rows.append(
                BenchmarkRow(
                    prompt=str(obj["prompt"]),
                    response=str(obj["response"]),
                    label=label,
                )
            )
    if not rows:
        raise ValueError("Benchmark file contained no rows")
    return rows


def run_calibration(
    instrument: InstrumentBase,
    rows: List[BenchmarkRow],
    generate_fn=None,
    judge_fn=None,
    benchmark_id: str = "benchmark",
    profile_id: str = "sage-run",
    n_bins: int = 10,
) -> CalibrationProfile:
    """Score every benchmark row and reduce to a measured CalibrationProfile.

    Returns the profile; the raw (label, score) pairs are available via the
    ``scores`` attribute of the returned object for inspection / auditing.
    """
    y_true: List[float] = []
    y_score: List[float] = []
    for row in rows:
        score = float(
            instrument.score(
                row.prompt,
                row.response,
                generate_fn=generate_fn,
                judge_fn=judge_fn,
            )
        )
        y_true.append(float(row.label))
        y_score.append(score)

    brier = brier_score(y_true, y_score)
    ece = expected_calibration_error(y_true, y_score, n_bins=n_bins)
    auroc = area_under_roc(y_true, y_score)

    return CalibrationProfile(
        profile_id=profile_id,
        brier=brier,
        ece=ece,
        auroc=auroc,
        n_samples=len(rows),
        benchmark_id=benchmark_id,
    )
