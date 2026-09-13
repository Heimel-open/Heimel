"""
Dirigent (L5b) — dirigerer orkesteret.

Mottar TerrainReport fra Scout (inkl. formation og uncertainty).
Dess mer usikkerhet, dess mer Dirigenten griper inn og utvider formasjonen.

  uncertainty 0.0–0.3  → Scout's formasjon er definitiv. Dirigenten kjører den.
  uncertainty 0.3–0.6  → Dirigenten utvider med ekstra instrumenter.
  uncertainty 0.6–0.8  → Dirigenten aktiverer fullt orkester.
  uncertainty >0.8     → Fullt orkester, alle instrumenter.
"""

from dataclasses import dataclass, field
from typing import Optional

from vaig.scout.terrain import TerrainReport, Domain, Complexity


_ALL_INTERNAL = [
    "length_anomaly", "format_check", "hedge_detector",
    "logprob_scorer", "activation_probe",
    "text_similarity", "semantic_entropy", "cot_auditor",
]

# Dirigentens domenekart — hvilke instrumenter er relevante per terreng
_DOMAIN_INTERNAL: dict[Domain, list[str]] = {
    Domain.MEDICAL:    ["length_anomaly", "hedge_detector", "text_similarity",
                        "semantic_entropy", "cot_auditor"],
    Domain.LEGAL:      ["length_anomaly", "format_check", "hedge_detector",
                        "text_similarity", "semantic_entropy"],
    Domain.FINANCIAL:  ["length_anomaly", "hedge_detector", "text_similarity",
                        "semantic_entropy"],
    Domain.SECURITY:   ["length_anomaly", "format_check", "hedge_detector"],
    Domain.CODE:       ["length_anomaly", "format_check"],
    Domain.INDUSTRIAL: ["length_anomaly", "hedge_detector", "text_similarity",
                        "semantic_entropy"],
    Domain.GENERAL:    ["length_anomaly", "format_check", "hedge_detector"],
    Domain.UNKNOWN:    ["length_anomaly", "format_check", "hedge_detector", "text_similarity"],
}

_DOMAIN_EXTERNAL: dict[Domain, list[str]] = {
    Domain.MEDICAL:    ["langkit_hallucination"],
    Domain.LEGAL:      ["langkit_hallucination", "giskard_hallucination"],
    Domain.FINANCIAL:  ["langkit_hallucination"],
    Domain.SECURITY:   ["giskard_injection", "nemo_jailbreak"],
    Domain.CODE:       [],
    Domain.INDUSTRIAL: ["langkit_hallucination"],
    Domain.GENERAL:    ["langkit_hallucination", "langkit_toxicity"],
    Domain.UNKNOWN:    ["langkit_hallucination", "giskard_injection"],
}

_ALL_EXTERNAL = [
    "langkit_hallucination", "langkit_toxicity",
    "giskard_injection", "giskard_hallucination",
    "nemo_jailbreak",
]

# Utvidelse per usikkerhetsnivå — ekstra instrumenter Dirigenten legger til
_UNCERTAINTY_EXPANSION = {
    "medium": ["text_similarity", "semantic_entropy"],          # 0.3–0.6
    "high":   ["text_similarity", "semantic_entropy",
               "cot_auditor", "format_check"],                   # 0.6–0.8
    "max":    _ALL_INTERNAL,                                      # >0.8
}


# Maks iterasjoner før kontekst-degenerering per domene
_CONTEXT_ITER_LIMIT: dict[Domain, int] = {
    Domain.MEDICAL:    12,
    Domain.LEGAL:      12,
    Domain.FINANCIAL:  15,
    Domain.SECURITY:   10,
    Domain.CODE:       20,
    Domain.INDUSTRIAL: 10,
    Domain.GENERAL:    20,
    Domain.UNKNOWN:    15,
}

# Domene-kalibrerte terskler — varierer etter hva Scout ser.
# Sensitive domener tightner HALT/DEGRADE; WARN/MONITOR holdes nær default.
# UNKNOWN bruker løftede terskler for å dempe instrument-støy.
# SECURITY-domenet ≠ injection-signal: domene bruker standardterskler.
_DOMAIN_THRESHOLDS: dict[Domain, dict[str, float]] = {
    Domain.MEDICAL:    {"HALT": 0.65, "DEGRADE": 0.50, "WARN": 0.35, "MONITOR": 0.15},
    Domain.LEGAL:      {"HALT": 0.65, "DEGRADE": 0.50, "WARN": 0.35, "MONITOR": 0.15},
    Domain.FINANCIAL:  {"HALT": 0.70, "DEGRADE": 0.52, "WARN": 0.35, "MONITOR": 0.15},
    Domain.SECURITY:   {"HALT": 0.75, "DEGRADE": 0.55, "WARN": 0.35, "MONITOR": 0.15},
    Domain.CODE:       {"HALT": 0.75, "DEGRADE": 0.55, "WARN": 0.35, "MONITOR": 0.15},
    Domain.INDUSTRIAL: {"HALT": 0.65, "DEGRADE": 0.48, "WARN": 0.35, "MONITOR": 0.15},
    Domain.GENERAL:    {"HALT": 0.75, "DEGRADE": 0.55, "WARN": 0.38, "MONITOR": 0.16},
    Domain.UNKNOWN:    {"HALT": 0.80, "DEGRADE": 0.65, "WARN": 0.50, "MONITOR": 0.35},
}

# injection_attempt SIGNAL overstyrer domene — mye lavere terskler
_INJECTION_THRESHOLDS: dict[str, float] = {
    "HALT": 0.30, "DEGRADE": 0.18, "WARN": 0.08, "MONITOR": 0.04,
}

# Maks total ordmengde (alle meldinger) — uavhengig av iterasjoner
# Høyere presisjonskrav = lavere grense
_CONTEXT_WORD_LIMIT: dict[Domain, int] = {
    Domain.MEDICAL:    4_000,
    Domain.LEGAL:      4_000,
    Domain.FINANCIAL:  5_000,
    Domain.SECURITY:   3_000,
    Domain.CODE:       8_000,
    Domain.INDUSTRIAL: 3_500,
    Domain.GENERAL:    7_000,
    Domain.UNKNOWN:    5_000,
}


@dataclass
class DispatchPlan:
    internal: list[str]
    external: list[str]
    bench: list[str]
    uncertainty_level: str       # "low" | "medium" | "high" | "max"
    expanded: bool               # True hvis Dirigenten la til instrumenter
    thresholds: dict[str, float] = field(default_factory=lambda: {
        "HALT": 0.75, "DEGRADE": 0.55, "WARN": 0.35, "MONITOR": 0.15,
    })
    context_health: float = 1.0                    # 0.0–1.0 — Dirigentens vurdering
    context_warning: Optional[str] = None         # kort, autoritativt — vis én gang
    context_warning_detail: Optional[str] = None  # full diagnostikk — kun på forespørsel


def _compute_thresholds(domain: Domain, signals: list[str]) -> dict[str, float]:
    """Domene- og signal-kalibrerte terskler for ensemble scoring."""
    if "injection_attempt" in signals:
        return dict(_INJECTION_THRESHOLDS)
    return dict(_DOMAIN_THRESHOLDS.get(domain, _DOMAIN_THRESHOLDS[Domain.GENERAL]))


class Dirigent:
    """
    L5b — Dirigent.

    Mottar TerrainReport. Leser usikkerhetsindeksen.
    Dess høyere usikkerhet, dess større formasjon aktiveres.
    """

    def conduct(self, terrain: TerrainReport) -> DispatchPlan:
        u = terrain.uncertainty

        # Dirigenten velger basisformasjon basert på terreng
        base_internal = _DOMAIN_INTERNAL.get(terrain.domain, _DOMAIN_INTERNAL[Domain.UNKNOWN])
        base_external = _DOMAIN_EXTERNAL.get(terrain.domain, [])

        # Usikkerhet bestemmer utvidelse
        if u <= 0.3:
            level = "low"
            internal = list(base_internal)
            external = list(base_external)
            expanded = False
        elif u <= 0.6:
            level = "medium"
            internal = _merge(base_internal, _UNCERTAINTY_EXPANSION["medium"])
            external = list(base_external)
            expanded = True
        elif u <= 0.8:
            level = "high"
            internal = _merge(base_internal, _UNCERTAINTY_EXPANSION["high"])
            external = _ALL_EXTERNAL
            expanded = True
        else:
            level = "max"
            internal = _ALL_INTERNAL
            external = _ALL_EXTERNAL
            expanded = True

        active_external = list(external)
        bench = [i for i in _ALL_INTERNAL if i not in internal]

        # Gult lys: kontekst-degenerering detektert via tre uavhengige signaler
        context_warning = None
        context_warning_detail = None
        iter_limit = _CONTEXT_ITER_LIMIT.get(terrain.domain, 15)
        word_limit = _CONTEXT_WORD_LIMIT.get(terrain.domain, 5_000)
        sycophancy  = "sycophancy" in terrain.signals
        self_aware  = "self_aware_degradation" in terrain.signals

        iter_over  = terrain.iteration_count >= iter_limit
        words_over = terrain.conversation_length >= word_limit

        # context_health: Dirigentens vurdering (0.0 = brukt opp, 1.0 = frisk)
        iter_ratio  = min(1.0, terrain.iteration_count / iter_limit)
        words_ratio = min(1.0, terrain.conversation_length / word_limit) if word_limit else 0.0
        penalty = max(iter_ratio, words_ratio)
        if sycophancy:
            penalty = min(1.0, penalty + 0.2)
        if self_aware:
            penalty = 1.0  # hard bevis — full degradering
        context_health = round(1.0 - penalty, 3)

        if iter_over or words_over or sycophancy or self_aware:
            context_warning = "Samtalen er for lang — start ny samtale for best resultat."
            details = []
            if self_aware:
                details.append("LLM signaliserte selv tapt kontekst")
            if iter_over:
                details.append(f"{terrain.iteration_count} iterasjoner (grense {iter_limit} for {terrain.domain.value})")
            if words_over:
                details.append(f"{terrain.conversation_length} ord (grense {word_limit})")
            if sycophancy:
                details.append("smiger-signal detektert i svar")
            context_warning_detail = " | ".join(details)

        thresholds = _compute_thresholds(terrain.domain, terrain.signals)

        return DispatchPlan(
            internal=internal,
            external=active_external,
            bench=bench,
            uncertainty_level=level,
            expanded=expanded,
            thresholds=thresholds,
            context_health=context_health,
            context_warning=context_warning,
            context_warning_detail=context_warning_detail,
        )


def _merge(base: list[str], extra: list[str]) -> list[str]:
    seen = set(base)
    return base + [x for x in extra if x not in seen]
