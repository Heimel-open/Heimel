"""
Instrument: text_similarity
Slot 6 — krever generate_fn for stokastisk sampling.

Kjør samme prompt N ganger, mål semantisk konsistens mellom svarene.
Inkonsistente svar = modellen er usikker på svaret.

Implementasjoner:
  "sampling"  — kosinus-likhet mellom embeddings (rask, ingen NLI-modell)
  "nli"       — NLI-entailment mellom svar-par (tyngre, mer presis)
"""

from typing import Optional, Callable, List
from vaig.instruments.registry import register
from vaig.instruments.base import InstrumentBase

_N_SAMPLES = 3  # antall re-kjøringer


def _simple_jaccard(a: str, b: str) -> float:
    """Token-Jaccard som fallback uten embedding-bibliotek."""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


@register("text_similarity", "sampling", priority=1)
class StochasticSamplingConsistency(InstrumentBase):
    """
    Generer N svar, mål gjennomsnittlig parvise Jaccard-likhet.
    Lav konsistens = høy risiko.

    Produksjon: bytt _simple_jaccard med sentence-transformers cosine similarity
    for bedre semantisk dekning.
    """

    requires_generate_fn = True

    def __init__(self, n_samples: int = _N_SAMPLES):
        self.n_samples = n_samples

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

        pairs = [
            _simple_jaccard(samples[i], samples[j])
            for i in range(len(samples))
            for j in range(i + 1, len(samples))
        ]
        avg_similarity = sum(pairs) / len(pairs)
        # Lav likhet = høy risiko
        return 1.0 - avg_similarity


@register("text_similarity", "nli", priority=2)
class NLIConsistencyChecker(InstrumentBase):
    """
    NLI-basert konsistenssjekk: bruker DeBERTa-modell for entailment-scoring.
    Aktiveres automatisk når transformers er installert.
    Referanse: RAG-Hallucination-Firewall, SelfCheckGPT NLI-variant.
    """

    requires_generate_fn = True

    @classmethod
    def is_available(cls) -> bool:
        try:
            import transformers
            return True
        except ImportError:
            return False

    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-small"):
        self._model_name = model_name
        self._pipeline = None

    def _get_pipeline(self):
        if self._pipeline is None:
            from transformers import pipeline
            self._pipeline = pipeline("text-classification", model=self._model_name)
        return self._pipeline

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
    ) -> float:
        if generate_fn is None:
            return 0.0

        try:
            pipe = self._get_pipeline()
        except ImportError:
            return 0.0  # transformers ikke installert → nøytral

        samples = [response]
        for _ in range(_N_SAMPLES - 1):
            try:
                samples.append(generate_fn(prompt))
            except Exception:
                pass

        if len(samples) < 2:
            return 0.0

        contradiction_scores = []
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                try:
                    result = pipe(f"{samples[i]} </s> {samples[j]}", truncation=True)
                    for r in result:
                        if r["label"].upper() == "CONTRADICTION":
                            contradiction_scores.append(r["score"])
                except Exception:
                    pass

        if not contradiction_scores:
            return 0.0
        return min(sum(contradiction_scores) / len(contradiction_scores), 1.0)
