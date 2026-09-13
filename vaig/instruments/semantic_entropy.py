"""
Instrument: semantic_entropy
Slot 7 — krever generate_fn, tyngste LLM-instrument.

Semantisk entropi (Farquhar et al., Nature 2024):
Generer N svar, klynge dem semantisk, mål entropien i fordelingen.
Høy entropi = modellen er genuint usikker på svaret.

Implementasjoner:
  "farquhar"  — original NLI-klynging (Nature 2024)
  "kernel"    — finkornet kernel-basert UQ (NeurIPS'24, AlexanderVNikitin)
  "jaccard"   — rask approksimering uten NLI-modell (pilot-default)
"""

import math
from typing import Optional, Callable, List, Dict
from collections import defaultdict
from vaig.instruments.registry import register
from vaig.instruments.base import InstrumentBase

_N_SAMPLES = 5


def _shannon_entropy(counts: List[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    return -sum(p * math.log(p) for p in probs)


def _normalize_entropy(h: float, n_clusters: int) -> float:
    """Normaliser mot maksimal entropi (jevn fordeling)."""
    max_h = math.log(n_clusters) if n_clusters > 1 else 1.0
    return h / max_h if max_h > 0 else 0.0


@register("semantic_entropy", "jaccard", priority=1)
class JaccardSemanticEntropy(InstrumentBase):
    """
    Rask approksimering: klynger svar basert på token-Jaccard-likhet.
    Ingen NLI-modell nødvendig — fungerer offline.
    Brukes som pilot-default til NLI-modell er kalibrert.
    """

    requires_generate_fn = True

    def __init__(self, n_samples: int = _N_SAMPLES, similarity_threshold: float = 0.4):
        self.n_samples = n_samples
        self.threshold = similarity_threshold

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
    ) -> float:
        if generate_fn is None:
            return 0.0

        samples = [response]
        for _ in range(self.n_samples - 1):
            try:
                samples.append(generate_fn(prompt))
            except Exception:
                pass

        if len(samples) < 2:
            return 0.0

        # Greedy klynging
        clusters: List[List[str]] = []
        for s in samples:
            placed = False
            tokens_s = set(s.lower().split())
            for cluster in clusters:
                rep_tokens = set(cluster[0].lower().split())
                union = tokens_s | rep_tokens
                inter = tokens_s & rep_tokens
                if union and (len(inter) / len(union)) >= self.threshold:
                    cluster.append(s)
                    placed = True
                    break
            if not placed:
                clusters.append([s])

        counts = [len(c) for c in clusters]
        h = _shannon_entropy(counts)
        return _normalize_entropy(h, len(clusters))


@register("semantic_entropy", "farquhar", priority=2)
class FarquharSemanticEntropy(InstrumentBase):
    """
    Original semantisk entropi (Farquhar et al., Nature 2024).
    Aktiveres automatisk når transformers er installert.
    """

    requires_generate_fn = True

    @classmethod
    def is_available(cls) -> bool:
        try:
            import transformers
            return True
        except ImportError:
            return False

    def __init__(self, n_samples: int = _N_SAMPLES, model_name: str = "cross-encoder/nli-deberta-v3-small"):
        self.n_samples = n_samples
        self._model_name = model_name
        self._pipeline = None

    def _entails(self, a: str, b: str) -> bool:
        """Bi-directional entailment: a ↔ b."""
        if self._pipeline is None:
            from transformers import pipeline
            self._pipeline = pipeline("text-classification", model=self._model_name)
        try:
            for premise, hyp in [(a, b), (b, a)]:
                result = self._pipeline(f"{premise} </s> {hyp}", truncation=True)
                labels = {r["label"].upper(): r["score"] for r in result}
                if labels.get("ENTAILMENT", 0) < 0.5:
                    return False
            return True
        except Exception:
            return False

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
    ) -> float:
        if generate_fn is None:
            return 0.0

        try:
            _ = self._pipeline  # trigger import check
            from transformers import pipeline
        except ImportError:
            return 0.0

        samples = [response]
        for _ in range(self.n_samples - 1):
            try:
                samples.append(generate_fn(prompt))
            except Exception:
                pass

        if len(samples) < 2:
            return 0.0

        clusters: List[List[str]] = []
        for s in samples:
            placed = False
            for cluster in clusters:
                if self._entails(cluster[0], s):
                    cluster.append(s)
                    placed = True
                    break
            if not placed:
                clusters.append([s])

        counts = [len(c) for c in clusters]
        h = _shannon_entropy(counts)
        return _normalize_entropy(h, len(clusters))
