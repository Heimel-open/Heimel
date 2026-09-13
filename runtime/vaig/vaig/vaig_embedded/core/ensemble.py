"""
VAIG Embedded — Core Ensemble
Lightweight 5-instrument ensemble for on-device validation.
Stdlib only. No network. No external APIs.

STATUS: edge-oriented reference runtime. Python-only, not accelerator-backed;
see hardware_detect for a hardware probe. On-device WORM logging lives in
vaig.vaig_embedded.core.worm_sqlite (SQLiteWORM).
"""
import math
from typing import Dict, Tuple

class LiteEnsemble:
    """5-instrument ensemble using only stdlib. Runs in <1ms per token."""

    INSTRUMENTS = [
        'text_similarity',
        'semantic_entropy', 
        'perturbation',
        'calibration',
        'drift',
    ]

    def __init__(self, vu_callback=None):
        self.weights = {
            'text_similarity': 0.25,
            'semantic_entropy': 0.25,
            'perturbation': 0.20,
            'calibration': 0.15,
            'drift': 0.15,
        }
        self.vu_callback = vu_callback  # Optional VU meter callback

    def score_token(self, token: str, context: str, prev_token: str = "") -> Tuple[float, Dict]:
        """Score a single token. Returns (combined_score, breakdown)."""
        scores = {}

        # L0: Text similarity (Jaccard on character n-grams)
        scores['text_similarity'] = self._jaccard_similarity(token, prev_token)

        # L0: Semantic entropy (character distribution entropy)
        scores['semantic_entropy'] = self._char_entropy(token)

        # L1: Perturbation (character flip resilience)
        scores['perturbation'] = self._perturbation_resilience(token)

        # L1: Calibration (length-normalized confidence)
        scores['calibration'] = self._length_calibration(token, context)

        # L1: Drift (context continuity)
        scores['drift'] = self._context_drift(token, context)

        combined = sum(scores[k] * self.weights[k] for k in scores)

        if self.vu_callback:
            self.vu_callback(scores)

        return combined, scores

    # ── L0 Instruments (microsecond scale) ─────────────────────────────────

    def _jaccard_similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.5
        set_a = set(a[i:i+2] for i in range(len(a)-1))
        set_b = set(b[i:i+2] for i in range(len(b)-1))
        if not set_a or not set_b:
            return 0.5
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def _char_entropy(self, text: str) -> float:
        if not text:
            return 0.5
        freq = {}
        for c in text:
            freq[c] = freq.get(c, 0) + 1
        total = len(text)
        entropy = 0.0
        for count in freq.values():
            p = count / total
            entropy -= p * math.log2(p)
        max_ent = math.log2(len(freq)) if freq else 1
        return min(entropy / max_ent, 1.0) if max_ent > 0 else 0.5

    # ── L1 Instruments (sub-millisecond) ──────────────────────────────────

    def _perturbation_resilience(self, text: str) -> float:
        if len(text) < 2:
            return 0.5
        flips = 0
        for i in range(min(3, len(text)-1)):
            flipped = text[:i] + chr((ord(text[i]) + 1) % 128) + text[i+1:]
            sim = self._jaccard_similarity(text, flipped)
            flips += sim
        return flips / min(3, len(text)-1) if len(text) > 1 else 0.5

    def _length_calibration(self, token: str, context: str) -> float:
        expected = math.sqrt(len(context)) if context else 5.0
        ratio = len(token) / expected if expected > 0 else 1.0
        return 1.0 - min(abs(ratio - 1.0), 1.0)

    def _context_drift(self, token: str, context: str) -> float:
        if not context:
            return 0.5
        last_words = context.split()[-10:]
        context_str = ' '.join(last_words)
        return self._jaccard_similarity(token, context_str)
