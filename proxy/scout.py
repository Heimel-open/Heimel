"""Scout — ingress gate. Evaluates the prompt before it reaches the model.

Two input modes:
  1. Operator pre-computed: X-Valo-Scout-L-Scalar header (TAV_ONE output)
  2. Heuristic: scans prompt text for injection patterns + anomalies

Returns same gate dict as gate.evaluate(), with source='header'|'heuristic'.
"""
import functools
import math
import re

from proxy.gate import _tav_regime, _combined_status, _COHERENCE_THRESHOLD

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"you\s+are\s+now\s+",
    r"pretend\s+(you\s+are|to\s+be)",
    r"DAN\s+mode",
    r"jailbreak",
    r"disregard\s+(your|all)\s+(previous\s+)?(instructions?|rules?|guidelines?)",
    r"act\s+as\s+(if\s+you\s+(are|were)|an?\s+)",
    r"do\s+anything\s+now",
    r"new\s+instructions?:",
    r"\[SYSTEM\]|\[INST\]|\[\/INST\]",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


@functools.lru_cache(maxsize=256)
def _heuristic_l_scalar(text: str) -> float:
    """Estimate TAV L-scalar from prompt text. Lower = more stable."""
    if not text:
        return 0.0
    if _INJECTION_RE.search(text):
        return 1.0
    freq = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(text)
    entropy = -sum((c / n) * math.log2(c / n) for c in freq.values())
    max_entropy = math.log2(max(len(freq), 1))
    normalised = (entropy / max_entropy) if max_entropy > 0 else 0.0
    length_penalty = min(0.1, (n / 10000) * 0.1)
    return min(1.0, normalised * 0.35 + length_penalty)


def evaluate_ingress(text: str, l_scalar_override: float = None,
                     confidence_override: float = None) -> dict:
    """Run Scout gate on incoming prompt text."""
    if l_scalar_override is not None:
        l_scalar = l_scalar_override
        source = "header"
    else:
        l_scalar = _heuristic_l_scalar(text)
        source = "heuristic"

    tav_regime = _tav_regime(l_scalar)
    confidence = confidence_override if confidence_override is not None else 0.9
    coherence = confidence * 10000.0

    if coherence >= _COHERENCE_THRESHOLD:
        status = "PASS"
    elif coherence > 0.0:
        status = "DEGRADE"
    else:
        status = "HALT"

    combined = _combined_status(tav_regime, status)

    return {
        "status": status,
        "tav_regime": tav_regime,
        "combined_status": combined,
        "coherence": coherence,
        "l_scalar": l_scalar,
        "source": source,
        "metrics_logged": True,
    }
