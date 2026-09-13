"""Tests for LangkitToxicityAdapter and LangkitHallucinationAdapter.

Covers:
  - normal score passthrough
  - None result → 0.5 (unknown), not 0.0 (false-safe)
  - adapter exception does not propagate to caller

Run: pytest tests/test_langkit_adapter.py -v
"""

import sys
from unittest.mock import MagicMock

import pytest

from vaig.integrations.external import LangkitHallucinationAdapter, LangkitToxicityAdapter


def _with_langkit(toxicity_return_value):
    """Call _call() with a mocked langkit.toxicity module."""
    toxicity_mod = MagicMock()
    toxicity_mod.toxicity = MagicMock(return_value=toxicity_return_value)
    langkit_mod = MagicMock()

    patched = {
        "langkit": langkit_mod,
        "langkit.toxicity": toxicity_mod,
    }
    original = {k: sys.modules.pop(k, None) for k in patched}
    sys.modules.update(patched)
    try:
        return LangkitToxicityAdapter()._call("prompt", "response")
    finally:
        for k, v in original.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class TestLangkitToxicityAdapter:
    def test_normal_score_passthrough(self):
        """A real score from langkit is returned unchanged."""
        assert _with_langkit(0.73) == pytest.approx(0.73)

    def test_low_score_passthrough(self):
        """A genuine 0.0 toxicity score is preserved."""
        assert _with_langkit(0.0) == pytest.approx(0.0)

    def test_none_result_is_neutral_not_safe(self):
        """None from langkit must map to 0.5 (unknown), not 0.0 (false-safe).

        UNKNOWN != SAFE — an unavailable instrument must not silently pass.
        """
        score = _with_langkit(None)
        assert score == pytest.approx(0.5), (
            f"Expected 0.5 (unknown) for None result, got {score} (false-safe if 0.0)"
        )

    def test_exception_does_not_propagate(self):
        """If langkit raises, ExternalAdapter.score() catches it and returns 0.0.

        The adapter must not crash the caller; the base-class catch is existing
        behaviour and is not changed by this PR.
        """
        toxicity_mod = MagicMock()
        toxicity_mod.toxicity = MagicMock(side_effect=RuntimeError("model load failed"))
        langkit_mod = MagicMock()

        patched = {"langkit": langkit_mod, "langkit.toxicity": toxicity_mod}
        original = {k: sys.modules.pop(k, None) for k in patched}
        sys.modules.update(patched)
        try:
            score = LangkitToxicityAdapter().score("prompt", "response")
        finally:
            for k, v in original.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

        assert score == 0.0


# ── LangkitHallucinationAdapter ───────────────────────────────────────────────

def _with_langkit_hallucination(return_value):
    """Call LangkitHallucinationAdapter._call() with a mocked langkit.hallucination module."""
    hallucination_mod = MagicMock()
    hallucination_mod.hallucination = MagicMock(return_value=return_value)
    langkit_mod = MagicMock()

    patched = {
        "langkit": langkit_mod,
        "langkit.hallucination": hallucination_mod,
    }
    original = {k: sys.modules.pop(k, None) for k in patched}
    sys.modules.update(patched)
    try:
        return LangkitHallucinationAdapter()._call("What is the capital of France?", "Paris is the capital.")
    finally:
        for k, v in original.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class TestLangkitHallucinationAdapter:
    def test_normal_score_passthrough(self):
        """A real hallucination score from langkit is returned unchanged."""
        assert _with_langkit_hallucination(0.82) == pytest.approx(0.82)

    def test_genuine_zero_preserved(self):
        """A genuine 0.0 hallucination score (no hallucination) is preserved."""
        assert _with_langkit_hallucination(0.0) == pytest.approx(0.0)

    def test_none_result_is_neutral_not_safe(self):
        """None from langkit must map to 0.5 (unknown), not 0.0 (false-safe).

        UNKNOWN != SAFE — an unavailable instrument must not silently pass.
        """
        score = _with_langkit_hallucination(None)
        assert score == pytest.approx(0.5), (
            f"Expected 0.5 (unknown) for None result, got {score} (false-safe if 0.0)"
        )

    def test_exception_does_not_propagate(self):
        """If langkit raises, ExternalAdapter.score() catches it and returns 0.0."""
        hallucination_mod = MagicMock()
        hallucination_mod.hallucination = MagicMock(side_effect=RuntimeError("model load failed"))
        langkit_mod = MagicMock()

        patched = {"langkit": langkit_mod, "langkit.hallucination": hallucination_mod}
        original = {k: sys.modules.pop(k, None) for k in patched}
        sys.modules.update(patched)
        try:
            score = LangkitHallucinationAdapter().score("prompt", "response")
        finally:
            for k, v in original.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

        assert score == 0.0
