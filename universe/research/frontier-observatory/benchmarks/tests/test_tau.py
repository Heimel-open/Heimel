"""
test_tau.py — Test vectors for τ coherence metric.

Spec: tau/spec/tau_specification_v1.md (Section 5)

Tests run without HuggingFace models — they use synthetic hidden states
to verify the mathematical implementation only.
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
from tau import compute_tau_from_hidden, TauResult

TOLERANCE = 0.002


class TestTauRange:
    """τ must always be in [0, 1]."""

    def test_random_matrix(self):
        rng = np.random.default_rng(42)
        h = rng.standard_normal((20, 64))
        result = compute_tau_from_hidden(h)
        assert 0.0 <= result.tau <= 1.0

    def test_identity_like(self):
        """Near-identity matrix has few active directions → high τ."""
        h = np.zeros((10, 64))
        h[:, 0] = 1.0  # single dominant direction
        result = compute_tau_from_hidden(h)
        assert result.tau > 0.8, f"Expected high τ, got {result.tau}"

    def test_uniform_matrix(self):
        """All-ones matrix has rank 1 → τ near 1."""
        h = np.ones((10, 64))
        result = compute_tau_from_hidden(h)
        assert result.tau > 0.95

    def test_zero_matrix(self):
        """Zero matrix is degenerate → τ = 0."""
        h = np.zeros((10, 64))
        result = compute_tau_from_hidden(h)
        assert result.tau == 0.0

    def test_random_small(self):
        """Random small matrix — distributed spectrum → low τ."""
        rng = np.random.default_rng(7)
        h = rng.standard_normal((8, 8))
        result = compute_tau_from_hidden(h)
        # Random matrix should have moderately distributed spectrum
        assert result.tau < 0.5


class TestTauDeterminism:
    """Same input → same output."""

    def test_deterministic(self):
        rng = np.random.default_rng(0)
        h = rng.standard_normal((15, 32))
        r1 = compute_tau_from_hidden(h)
        r2 = compute_tau_from_hidden(h)
        assert abs(r1.tau - r2.tau) < 1e-9

    def test_deterministic_different_call(self):
        rng = np.random.default_rng(0)
        h = rng.standard_normal((15, 32))
        results = [compute_tau_from_hidden(h.copy()) for _ in range(5)]
        taus = [r.tau for r in results]
        assert max(taus) - min(taus) < 1e-9


class TestTauFormula:
    """Verify the mathematical formula components."""

    def test_rank_one_matrix(self):
        """Rank-1 matrix: all variance in one singular value → τ = 1."""
        u = np.ones((10, 1)) / np.sqrt(10)
        v = np.ones((1, 64)) / np.sqrt(64)
        h = u @ v  # outer product, rank 1
        result = compute_tau_from_hidden(h)
        assert abs(result.tau - 1.0) < TOLERANCE, f"Expected τ≈1 for rank-1, got {result.tau}"

    def test_output_fields(self):
        rng = np.random.default_rng(1)
        h = rng.standard_normal((12, 48))
        result = compute_tau_from_hidden(h, model_id="test_model", layer_index=5)
        assert result.model_id == "test_model"
        assert result.layer_index == 5
        assert result.seq_len == 12
        assert result.hidden_dim == 48
        assert result.n_singular_values == 12  # min(12, 48)
        assert 0.0 <= result.H_norm <= 1.0
        assert result.H >= 0.0

    def test_h_norm_bounds(self):
        """H_norm must be in [0, 1] — it is entropy / log(n)."""
        rng = np.random.default_rng(99)
        for _ in range(20):
            h = rng.standard_normal((rng.integers(5, 30), rng.integers(8, 64)))
            result = compute_tau_from_hidden(h)
            assert 0.0 <= result.H_norm <= 1.0 + 1e-9

    def test_tau_plus_h_norm_equals_one(self):
        """By definition: τ + H_norm = 1."""
        rng = np.random.default_rng(55)
        h = rng.standard_normal((20, 40))
        result = compute_tau_from_hidden(h)
        assert abs(result.tau + result.H_norm - 1.0) < 1e-9


class TestTauToDict:
    def test_serialization(self):
        rng = np.random.default_rng(2)
        h = rng.standard_normal((10, 32))
        result = compute_tau_from_hidden(h)
        d = result.to_dict()
        assert "tau" in d
        assert "H" in d
        assert "H_norm" in d
        assert isinstance(d["tau"], float)
        assert 0.0 <= d["tau"] <= 1.0
