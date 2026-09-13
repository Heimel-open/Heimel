"""
Scout (L5a) — leser terreng. Ingenting annet.

Scout svarer på ETT spørsmål: Hva slags terreng er dette?
Scout velger INGEN instrumenter. Det er Dirigentens jobb.

Usikkerhetsindeks (0.0–1.0):
  Dess høyere usikkerhet, dess mer Dirigenten griper inn.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from vaig.scout.terrain_constants import (
    Domain, _DOMAIN_SIGNALS, _HEDGE_WORDS, _SYCOPHANCY_SIGNALS,
    _SELF_AWARE_DEGRADATION, _FACTUAL_MARKERS, _OWASP_MAPPING,
    _NO_WORDS, _EN_WORDS, _LANG_MIN_RATIO, _LANG_MIX_RATIO,
)


class Complexity(str, Enum):
    LOW       = "LOW"
    MEDIUM    = "MEDIUM"
    HIGH      = "HIGH"
    AMBIGUOUS = "AMBIGUOUS"


class Language(str, Enum):
    NO = "NO"   # norsk
    EN = "EN"   # engelsk
    MIX = "MIX" # blanding
    UNK = "UNK" # ukjent


@dataclass
class TerrainReport:
    """
    Scout sin rapport om terrenget.
    Ingen instrumentvalg — bare beskrivelse av hva Scout ser.
    Alt detektert uten LLM, under 5ms.
    """
    domain: Domain
    complexity: Complexity
    language: Language
    confidence: float           # 0.0–1.0
    uncertainty: float          # = 1 - confidence
    signals: list[str]          # ["hedge", "factual_claim", "injection_attempt", ...]
    risk_type: str
    is_structured: bool         # svar har tydelig struktur (lister, avsnitt, overskrifter)
    roughness: float            # 0.0–1.0 — ulendt terreng (motstridende signaler)
    iteration_count: int        # antall iterasjoner i konversasjonen
    iteration_risk: bool        # True hvis iterasjoner > 10 (DELEGATE-52 entropi)
    conversation_length: int    # estimert total lengde i tokens/ord
    owasp_code: str             # OWASP Agentic Top 10 2026 — ASI01–ASI10


def _detect_language(text: str) -> Language:
    words = text.lower().split()
    if not words:
        return Language.UNK
    no_hits = sum(1 for w in words if w in _NO_WORDS)
    en_hits = sum(1 for w in words if w in _EN_WORDS)
    total = max(1, len(words))
    no_ratio = no_hits / total
    en_ratio = en_hits / total
    if no_ratio < _LANG_MIN_RATIO and en_ratio < _LANG_MIN_RATIO:
        return Language.UNK
    if no_ratio > _LANG_MIX_RATIO and en_ratio > _LANG_MIX_RATIO:
        return Language.MIX
    return Language.NO if no_ratio >= en_ratio else Language.EN


def _detect_structure(response: str) -> bool:
    lines = response.splitlines()
    has_header = any(l.startswith("#") for l in lines)
    has_bullet = any(l.lstrip().startswith(("-", "*", "•")) for l in lines)
    has_numbered = any(l.lstrip()[:2].rstrip(".").isdigit() for l in lines if l.strip())
    has_blank_separator = sum(1 for l in lines if l.strip() == "") >= 2
    return sum([has_header, has_bullet, has_numbered, has_blank_separator]) >= 2


def _detect_roughness(signals: list[str], domain: Domain, complexity: Complexity) -> float:
    score = 0.0
    if "hedge" in signals and "factual_claim" in signals:
        score += 0.4
    if "injection_attempt" in signals and domain not in (Domain.SECURITY,):
        score += 0.3
    if complexity == Complexity.AMBIGUOUS:
        score += 0.3
    if "short_response" in signals and domain in (Domain.MEDICAL, Domain.LEGAL, Domain.FINANCIAL, Domain.INDUSTRIAL):
        score += 0.2
    return round(min(1.0, score), 3)


def _detect_domain(text: str) -> tuple[Domain, float]:
    text_lower = text.lower()
    scores: dict[Domain, int] = {d: 0 for d in Domain}
    for domain, keywords in _DOMAIN_SIGNALS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[domain] += 1
    best = max(scores, key=lambda d: scores[d])
    best_score = scores[best]
    if best_score == 0:
        return Domain.UNKNOWN, 0.25
    if best_score == 1:
        return best, 0.55
    if best_score >= 3:
        return best, 0.90
    return best, 0.70


def _detect_signals(prompt: str, response: str) -> list[str]:
    combined = (prompt + " " + response).lower()
    response_lower = response.lower()
    signals = []
    if any(w in combined for w in _HEDGE_WORDS):
        signals.append("hedge")
    if any(m in combined for m in _FACTUAL_MARKERS):
        signals.append("factual_claim")
    if any(kw in combined for kw in _DOMAIN_SIGNALS[Domain.SECURITY]):
        signals.append("injection_attempt")
    if any(s in response_lower for s in _SYCOPHANCY_SIGNALS):
        signals.append("sycophancy")
    if any(s in response_lower for s in _SELF_AWARE_DEGRADATION):
        signals.append("self_aware_degradation")
    if "?" in prompt:
        signals.append("question")
    word_count_response = len(response.split())
    if word_count_response < 10:
        signals.append("short_response")
    if word_count_response > 400:
        signals.append("long_response")
    return signals


def _detect_risk_type(domain: Domain, signals: list[str]) -> str:
    if "injection_attempt" in signals or domain == Domain.SECURITY:
        return "injection"
    if "hedge" in signals and domain in (Domain.MEDICAL, Domain.LEGAL, Domain.FINANCIAL):
        return "hallucination"
    if domain == Domain.CODE:
        return "structure"
    if domain == Domain.INDUSTRIAL:
        return "safety_critical"
    if "factual_claim" in signals:
        return "hallucination"
    return "unknown"


def _detect_complexity(prompt: str, response: str, signals: list[str]) -> Complexity:
    word_count = len(prompt.split()) + len(response.split())
    if "injection_attempt" in signals:
        return Complexity.HIGH
    if word_count > 300:
        return Complexity.HIGH
    if word_count > 100:
        return Complexity.MEDIUM
    if "short_response" in signals and "factual_claim" in signals:
        return Complexity.AMBIGUOUS
    return Complexity.LOW


class Scout:
    """
    L5a — Scout. Leser terreng. Ingenting annet.
    Returnerer TerrainReport — ingen instrumentvalg.
    """

    def read_terrain(
        self,
        prompt: str,
        response: str,
        iteration_count: int = 0,
        conversation_length: int = 0,
    ) -> TerrainReport:
        domain, confidence = _detect_domain(prompt + " " + response)
        uncertainty = round(1.0 - confidence, 3)
        signals = _detect_signals(prompt, response)
        complexity = _detect_complexity(prompt, response, signals)
        risk_type = _detect_risk_type(domain, signals)
        language = _detect_language(prompt + " " + response)
        is_structured = _detect_structure(response)
        roughness = _detect_roughness(signals, domain, complexity)
        iteration_risk = iteration_count > 10

        owasp_code = _OWASP_MAPPING.get(risk_type, "ASI09")

        return TerrainReport(
            domain=domain,
            complexity=complexity,
            language=language,
            confidence=confidence,
            uncertainty=uncertainty,
            signals=signals,
            risk_type=risk_type,
            is_structured=is_structured,
            roughness=roughness,
            iteration_count=iteration_count,
            iteration_risk=iteration_risk,
            conversation_length=conversation_length,
            owasp_code=owasp_code,
        )
