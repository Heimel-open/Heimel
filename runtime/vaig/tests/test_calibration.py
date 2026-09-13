"""Tests for the SAGE calibration interface (P0.6)."""

import math

import pytest

from vaig.calibration import (
    CalibrationProfile,
    area_under_roc,
    brier_score,
    expected_calibration_error,
)


def test_brier_perfect_is_zero():
    assert brier_score([0, 1, 0, 1], [0.0, 1.0, 0.0, 1.0]) == pytest.approx(0.0)


def test_brier_worst_case_is_one():
    # all inverted: 0 predicted as 1, 1 predicted as 0
    assert brier_score([0, 1], [1.0, 0.0]) == pytest.approx(1.0)


def test_brier_midpoint():
    # one sample: true 0, score 0.5 -> (0.5)^2 = 0.25
    assert brier_score([0], [0.5]) == pytest.approx(0.25)


def test_brier_rejects_mismatch_and_empty():
    with pytest.raises(ValueError):
        brier_score([0, 1], [0.0])
    with pytest.raises(ValueError):
        brier_score([], [])
    with pytest.raises(ValueError):
        brier_score([0, 1], [0.0, 1.5])


def test_ece_zero_when_perfectly_calibrated():
    # predicted confidence equals the label in every bin -> ECE 0
    y_true = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    y_score = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    assert expected_calibration_error(y_true, y_score) == pytest.approx(0.0, abs=1e-9)


def test_ece_positive_when_miscalibrated():
    # all confident-1.0 but half wrong -> high ECE
    y_true = [1, 0, 1, 0]
    y_score = [1.0, 1.0, 1.0, 1.0]
    ece = expected_calibration_error(y_true, y_score)
    assert ece > 0.0


def test_ece_rejects_bad_input():
    with pytest.raises(ValueError):
        expected_calibration_error([0, 1], [0.0])
    with pytest.raises(ValueError):
        expected_calibration_error([], [])
    with pytest.raises(ValueError):
        expected_calibration_error([0, 1], [0.0, 2.0])


def test_auroc_perfect_and_inverted():
    # perfect: positives score higher than negatives
    assert area_under_roc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == pytest.approx(1.0)
    # inverted: positives score lower
    assert area_under_roc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == pytest.approx(0.0)


def test_auroc_random_with_ties_is_half():
    # overlapping scores -> ~0.5
    auroc = area_under_roc([0, 0, 1, 1], [0.5, 0.5, 0.5, 0.5])
    assert auroc == pytest.approx(0.5, abs=1e-9)


def test_auroc_rejects_missing_classes_and_bad_range():
    with pytest.raises(ValueError):
        area_under_roc([1, 1], [0.1, 0.9])  # no negatives
    with pytest.raises(ValueError):
        area_under_roc([0, 1], [0.0])  # mismatch
    with pytest.raises(ValueError):
        area_under_roc([0, 1], [0.0, 1.5])


def test_calibration_profile_valid_and_invalid():
    prof = CalibrationProfile(
        profile_id="sage-v1@2026-08-01",
        brier=0.12,
        ece=0.05,
        auroc=0.93,
        n_samples=548,
        benchmark_id="vaig-bench-48x500",
    )
    assert prof.as_dict()["profile_id"] == "sage-v1@2026-08-01"
    assert prof.auroc == 0.93

    with pytest.raises(ValueError):
        CalibrationProfile(
            profile_id="", brier=0.1, ece=0.1, auroc=0.9, n_samples=10, benchmark_id="b"
        )
    with pytest.raises(ValueError):
        CalibrationProfile(
            profile_id="x", brier=1.5, ece=0.1, auroc=0.9, n_samples=10, benchmark_id="b"
        )
    with pytest.raises(ValueError):
        CalibrationProfile(
            profile_id="x", brier=0.1, ece=0.1, auroc=2.0, n_samples=10, benchmark_id="b"
        )
    with pytest.raises(ValueError):
        CalibrationProfile(
            profile_id="x", brier=0.1, ece=0.1, auroc=0.9, n_samples=0, benchmark_id="b"
        )
