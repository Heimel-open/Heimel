"""Tests for vaig.vaig_embedded — on-device runtime.

The embedded package is a stdlib-only reference runtime. These tests pin its
observable behaviour so the module is covered rather than dead code.
"""
import hashlib
import json
import time

import pytest

from vaig.vaig_embedded import (
    LiteEnsemble,
    SQLiteWORM,
    VUMeter,
    HWAccel,
    get_optimal_threads,
)


class TestLiteEnsemble:
    """5-instrument stdlib-only scoring."""

    def test_score_token_shape(self):
        e = LiteEnsemble()
        score, breakdown = e.score_token("token", "context", prev_token="prev")
        assert 0.0 <= score <= 1.0
        assert set(breakdown.keys()) == {
            "text_similarity", "semantic_entropy", "perturbation",
            "calibration", "drift",
        }

    def test_weights_sum_to_one(self):
        e = LiteEnsemble()
        assert abs(sum(e.weights.values()) - 1.0) < 1e-9

    def test_similar_inputs_score_similarly(self):
        e = LiteEnsemble()
        s1, _ = e.score_token("same", "same context")
        s2, _ = e.score_token("same", "same context")
        assert s1 == s2

    def test_vu_callback_invoked(self):
        calls = []
        e = LiteEnsemble(vu_callback=lambda scores: calls.append(scores))
        e.score_token("token", "context")
        assert len(calls) == 1

    def test_per_token_under_1ms(self):
        """Edge requirement: scoring a token must stay under 1ms."""
        e = LiteEnsemble()
        start = time.perf_counter()
        n = 200
        for i in range(n):
            e.score_token(f"tok{i}", "a short local context window")
        elapsed = (time.perf_counter() - start) / n
        assert elapsed < 1e-3, f"per-token scoring took {elapsed * 1e3:.3f}ms"


class TestSQLiteWORM:
    """Canonical on-device WORM log."""

    def test_append_and_verify(self, tmp_path):
        w = SQLiteWORM(str(tmp_path / "worm.db"))
        h1 = w.append(source_id="edge", distrust_level=0, action="PASS", score=0.1)
        h2 = w.append(source_id="edge", distrust_level=3, action="HALT", score=0.9)
        assert h1 != h2
        assert w.count() == 2
        assert w.verify()
        w.close()

    def test_verify_detects_tamper(self, tmp_path):
        w = SQLiteWORM(str(tmp_path / "worm.db"))
        w.append(source_id="edge", distrust_level=0, action="PASS", score=0.1)
        # Direct tamper of a stored entry must break the chain.
        w._conn.execute(
            "UPDATE worm_log SET score = ? WHERE id = 1", (0.99,)
        )
        w._conn.commit()
        assert not w.verify()
        w.close()

    def test_in_memory(self):
        w = SQLiteWORM(":memory:")
        w.append(source_id="edge", action="PASS")
        assert w.count() == 1
        assert w.verify()
        w.close()


class TestVUMeter:
    """3-channel coherence display."""

    def test_status_after_update(self):
        v = VUMeter()
        v.update({"text_similarity": 0.9, "semantic_entropy": 0.9, "perturbation": 0.9})
        assert v.status() in ("GREEN", "YELLOW", "RED")

    def test_channels_default_zero(self):
        v = VUMeter()
        assert v.channels() == {"coherence": 0.0, "stability": 0.0, "integrity": 0.0}

    def test_update_appends_history(self):
        v = VUMeter()
        v.update({"text_similarity": 0.1})
        v.update({"text_similarity": 0.2})
        assert len(v.history) == 2


class TestHardwareDetect:
    """Hardware detection is best-effort and never crashes."""

    def test_detect_returns_enum(self):
        from vaig.vaig_embedded.core.hardware_detect import detect_hardware
        hw = detect_hardware()
        assert isinstance(hw, HWAccel)

    def test_optimal_threads_positive(self):
        for hw in HWAccel:
            assert get_optimal_threads(hw) >= 1

