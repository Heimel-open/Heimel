"""Semantic drift detection — Instrument 4 of the DistrustEngine.

Embeds prompt and response in a shared vector space and measures cosine
distance. Low cosine similarity = response has drifted from query intent.

Model: sentence-transformers/all-MiniLM-L6-v2 (~80MB, CPU, ~50ms/pair)
Loaded lazily on first call. Falls back gracefully if not installed.

Usage:
    from proxy.semantic import evaluate_drift
    result = evaluate_drift(prompt, response)
    # {"cosine": 0.82, "drift": 0.18, "regime": "FLUID", "available": True}
"""
import functools
import os
import threading

_model = None
_available = None
_lock = threading.Lock()
_THRESHOLD_GASEOUS = float(os.environ.get("VALO_SEMANTIC_GASEOUS", "0.55"))
_THRESHOLD_PLASMA  = float(os.environ.get("VALO_SEMANTIC_PLASMA",  "0.35"))


def _load_model():
    global _model, _available
    if _available is not None:
        return _available
    with _lock:
        if _available is not None:
            return _available
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            _available = True
        except ImportError:
            _available = False
    return _available


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _drift_regime(cosine: float) -> str:
    """Map cosine similarity to TAV-style regime (higher cosine = more stable)."""
    if cosine >= _THRESHOLD_GASEOUS:
        return "FLUID"
    if cosine >= _THRESHOLD_PLASMA:
        return "GASEOUS"
    return "PLASMA"


@functools.lru_cache(maxsize=256)
def _encode_text(text: str) -> tuple:
    """Encode a single text to an embedding vector. Cached per unique text."""
    return tuple(_model.encode([text])[0].tolist())


def warm_prompt(text: str) -> None:
    """Pre-compute and cache the prompt embedding. No-op if model unavailable."""
    if text and _load_model():
        _encode_text(text)


def evaluate_drift(prompt: str, response: str) -> dict:
    """Compute semantic drift between prompt and response.

    Returns:
        cosine:    float [0,1] — similarity (1 = identical meaning)
        drift:     float [0,1] — distance (0 = no drift)
        regime:    FLUID | GASEOUS | PLASMA
        available: bool — False if sentence-transformers not installed
    """
    if not prompt or not response:
        return {"cosine": 1.0, "drift": 0.0, "regime": "FLUID", "available": False,
                "note": "empty input"}

    if not _load_model():
        return {"cosine": None, "drift": None, "regime": "FLUID", "available": False,
                "note": "sentence-transformers not installed; pip install sentence-transformers"}

    emb_p = _encode_text(prompt)
    emb_r = _encode_text(response)
    cosine = float(_cosine(emb_p, emb_r))
    drift = 1.0 - cosine

    return {
        "cosine": round(cosine, 4),
        "drift": round(drift, 4),
        "regime": _drift_regime(cosine),
        "available": True,
    }


def evaluate_intent_alignment(prompt: str, response: str) -> dict:
    """Instrument 6 — does the response satisfy the prompt's intent?

    Uses a lightweight heuristic: classify intent from prompt keywords,
    then check if response type matches. Returns alignment score [0,1].
    """
    if not prompt or not response:
        return {"aligned": True, "intent": "unknown", "score": 1.0}

    prompt_lower = prompt.lower()
    response_lower = response.lower()

    intents = {
        "summarize":  ["summarize", "summary", "tldr", "brief", "oppsummer", "sammendrag"],
        "list":       ["list", "enumerate", "bullet", "items", "liste", "punkt"],
        "explain":    ["explain", "what is", "how does", "why", "forklar", "hva er"],
        "create":     ["write", "create", "generate", "draft", "skriv", "lag"],
        "retrieve":   ["find", "search", "look up", "hent", "finn", "søk"],
        "analyze":    ["analyze", "analyse", "compare", "evaluate", "vurder"],
    }

    detected_intent = "general"
    for intent, keywords in intents.items():
        if any(kw in prompt_lower for kw in keywords):
            detected_intent = intent
            break

    score = 1.0
    if detected_intent == "summarize":
        if len(response) > len(prompt) * 2:
            score = 0.5
    elif detected_intent == "list":
        has_list = any(marker in response for marker in ["\n-", "\n•", "\n*", "1.", "2."])
        score = 1.0 if has_list else 0.6
    elif detected_intent == "retrieve":
        score = 0.7 if "not found" in response_lower or "i don't" in response_lower else 1.0

    return {
        "aligned": score >= 0.7,
        "intent": detected_intent,
        "score": round(score, 2),
    }
