"""
Instrument: hedge_detector
Slot 3 — lokal, ingen LLM-kall.

Detekterer linguistiske sikkerhetsbufre: "kanskje", "kan hende", "det er mulig",
"jeg er ikke sikker", osv. Høy tetthet = modellen vet ikke svaret.
"""

import re
from typing import Optional, Callable
from vaig.instruments.registry import register
from vaig.instruments.base import InstrumentBase

# Norsk + engelsk (Cegal-pilot er norsk, men LLM svarer ofte på begge)
_HEDGES = re.compile(
    r"\b("
    r"kanskje|kan hende|muligens|trolig|sannsynligvis|antagelig|antakelig"
    r"|jeg er ikke sikker|usikker|ikke helt sikker|ikke sikkert"
    r"|det er mulig|det kan hende|det kan være"
    r"|bør sjekkes|bør verifiseres|bør bekreftes"
    r"|ifølge|basert på|så vidt jeg vet|etter min kunnskap"
    r"|i de fleste tilfeller|vanligvis|normalt sett"
    r"|perhaps|maybe|possibly|likely|probably|uncertain"
    r"|i'm not sure|not certain|it's possible|may|might|could be"
    r"|to my knowledge|as far as i know|typically|generally|usually"
    r")\b",
    re.IGNORECASE,
)

_HARD_CAP = 8  # mer enn dette er nesten alltid problematisk


@register("hedge_detector", "default")
class RegexHedgeDetector(InstrumentBase):
    """
    Teller hedge-fraser og normaliserer mot respons-lengde.
    Score stiger raskere ved kortere svar (én hedge i én setning er verre enn i ti).
    """

    requires_generate_fn = False

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
    ) -> float:
        if not response:
            return 0.0

        hits = len(_HEDGES.findall(response))
        if hits == 0:
            return 0.0

        words = max(len(response.split()), 1)
        # Normalisert rate + straff for absolutt antall
        rate = hits / words
        absolute_penalty = min(hits / _HARD_CAP, 1.0)
        return min((rate * 20 + absolute_penalty) / 2, 1.0)
