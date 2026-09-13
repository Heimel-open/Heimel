"""SAGE calibration interface (P0.6).

P0.6 requires VAIG instruments to carry a *calibration profile* whose quality
is measurable: a calibrated instrument's risk scores should be probabilistically
reliable (calibration) and discriminative (ranking). SAGE (Self-Aligning
Governance Evaluator) is the calibration harness; this module is the
measurement surface it reports against.

The functions here are pure (numpy only) and operate on (y_true, y_score)
pairs, so they are fully testable without a live model or benchmark dataset.
Binding a real `CalibrationProfile` to an instrument is the caller's job
(the ensemble / SAGE runner); this module does not invent benchmark data.

Metrics:
- brier_score: mean squared error of probabilistic forecasts in [0, 1].
- expected_calibration_error (ECE): weighted average of |confidence - accuracy|
  over equal-width confidence bins.
- area_under_roc (AUROC): probability a positive ranks above a negative.

All three are fail-closed: empty / mismatched inputs raise ValueError rather
than silently returning a meaningless 0.0.
"""

from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np


def brier_score(y_true: Sequence[float], y_score: Sequence[float]) -> float:
    """Mean squared error of probabilistic forecasts in [0, 1].

    Lower is better. 0.0 == perfect. Ranges up to 1.0 for binary labels.
    """
    yt = np.asarray(y_true, dtype=float)
    ys = np.asarray(y_score, dtype=float)
    if yt.shape != ys.shape:
        raise ValueError("y_true and y_score must have equal shape")
    if yt.size == 0:
        raise ValueError("brier_score requires at least one sample")
    if ys.min() < 0.0 or ys.max() > 1.0:
        raise ValueError("y_score must lie in [0, 1]")
    return float(np.mean((ys - yt) ** 2))


def expected_calibration_error(
    y_true: Sequence[float],
    y_score: Sequence[float],
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error over equal-width confidence bins.

    Lower is better. 0.0 == perfectly calibrated. Measures the gap between
    predicted confidence and empirical accuracy.
    """
    yt = np.asarray(y_true, dtype=float)
    ys = np.asarray(y_score, dtype=float)
    if yt.shape != ys.shape:
        raise ValueError("y_true and y_score must have equal shape")
    if yt.size == 0:
        raise ValueError("expected_calibration_error requires at least one sample")
    if ys.min() < 0.0 or ys.max() > 1.0:
        raise ValueError("y_score must lie in [0, 1]")
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total = float(yt.size)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        # right-edge inclusive on the top bin to capture score == 1.0
        mask = (ys >= lo) & (ys < hi) if i < n_bins - 1 else (ys >= lo) & (ys <= hi)
        if not mask.any():
            continue
        bin_conf = float(ys[mask].mean())
        bin_acc = float(yt[mask].mean())
        weight = float(mask.sum()) / total
        ece += weight * abs(bin_conf - bin_acc)
    return ece


def area_under_roc(y_true: Sequence[float], y_score: Sequence[float]) -> float:
    """Area under the ROC curve (AUROC).

    Higher is better. 1.0 == perfect ranking, 0.5 == random. AUROC of 0.0 means
    *inverted* ranking (worse than random) and is valid (not clamped).
    """
    yt = np.asarray(y_true, dtype=float)
    ys = np.asarray(y_score, dtype=float)
    if yt.shape != ys.shape:
        raise ValueError("y_true and y_score must have equal shape")
    if yt.size == 0:
        raise ValueError("area_under_roc requires at least one sample")
    if ys.min() < 0.0 or ys.max() > 1.0:
        raise ValueError("y_score must lie in [0, 1]")

    positives = ys[yt >= 0.5]
    negatives = ys[yt < 0.5]
    if positives.size == 0 or negatives.size == 0:
        raise ValueError("area_under_roc requires both classes present")

    # Rank-based AUROC (Mann-Whitney U), ties split evenly.
    order = np.argsort(ys, kind="mergesort")
    ranks = np.empty(ys.size, dtype=float)
    sorted_scores = ys[order]
    i = 0
    while i < sorted_scores.size:
        j = i
        while j + 1 < sorted_scores.size and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-based average rank for the tie group
        ranks[order[i : j + 1]] = avg_rank
        i = j + 1
    sum_ranks_pos = float(ranks[yt >= 0.5].sum())
    n_pos = float(positives.size)
    n_neg = float(negatives.size)
    u = sum_ranks_pos - n_pos * (n_pos + 1.0) / 2.0
    return u / (n_pos * n_neg)


@dataclass(frozen=True)
class CalibrationProfile:
    """A versioned, measured calibration artifact for one instrument.

    Attaching this to an ``InstrumentResult.calibration_profile`` lets REHT see
    not just *that* an instrument is calibrated, but *how well*.

    ``profile_id`` should be a version-pinned identifier (e.g.
    ``"sage-v1@2026-08-01"``) so the report is reproducible.
    """

    profile_id: str
    brier: float
    ece: float
    auroc: float
    n_samples: int
    benchmark_id: str

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id must be non-empty")
        if not self.benchmark_id:
            raise ValueError("benchmark_id must be non-empty")
        if self.n_samples <= 0:
            raise ValueError("n_samples must be positive")
        if not (0.0 <= self.brier <= 1.0):
            raise ValueError("brier must lie in [0, 1]")
        if not (0.0 <= self.ece <= 1.0):
            raise ValueError("ece must lie in [0, 1]")
        if not (-0.0001 <= self.auroc <= 1.0001):
            raise ValueError("auroc must lie in [-0, 1] in practice")

    def as_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "brier": self.brier,
            "ece": self.ece,
            "auroc": self.auroc,
            "n_samples": self.n_samples,
            "benchmark_id": self.benchmark_id,
        }
