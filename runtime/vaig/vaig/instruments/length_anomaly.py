"""
Instrument: length_anomaly
Slot 1 — raskeste lokale sjekk, ingen LLM-kall.

Ekstremt korte svar = modellen har kapitulert.
Ekstremt lange svar = modellen fyller hull med støy.
Begge er faresignaler. Z-score mot en referansedistribusjon.
"""

import math
from typing import Optional, Callable
from vaig.instruments.registry import register
from vaig.instruments.base import InstrumentBase

# Referanseverdier for juridisk/kontrakt-domene (tokens, ikke tegn)
# Kalibreres mot Cegal-pilot data
_REF_MEAN = 180.0
_REF_STD  = 80.0
_Z_THRESHOLD = 2.0  # utover dette = klart avvik


@register("length_anomaly", "default")
class ZScoreLengthAnomalyDetector(InstrumentBase):
    """
    Z-score på respons-lengde (ord som proxy for tokens).
    Symmetrisk: for kort og for langt scorer likt.
    """

    requires_generate_fn = False

    def __init__(self, mean: float = _REF_MEAN, std: float = _REF_STD):
        self.mean = mean
        self.std = std

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
    ) -> float:
        if not response:
            return 1.0  # tom respons er alltid kritisk

        length = len(response.split())
        z = abs(length - self.mean) / self.std
        # Sigmoid-normalisering: z=2 → ~0.5, z=4 → ~0.88
        return 1.0 / (1.0 + math.exp(-(z - _Z_THRESHOLD)))
