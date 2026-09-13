"""
Instrument: format_check
Slot 2 — lokal, ingen LLM-kall.

Verifiserer at responsen overholder forventet struktur:
- JSON-validitet (hvis JSON forventes)
- Obligatoriske seksjoner / nøkkelord
- Avslutnings-integritet (ikke avkuttet midt i setning)
"""

import json
from typing import Optional, Callable, List
from vaig.instruments.registry import register
from vaig.instruments.base import InstrumentBase


@register("format_check", "default")
class StructuralFormatChecker(InstrumentBase):
    """
    Generell struktursjekk. Tre signal kombinert til én score:
    1. Avkuttings-detektor (respons slutter brått)
    2. Manglende obligatoriske felt
    3. JSON-validitet (valgfritt, aktiveres via requires_json=True)
    """

    requires_generate_fn = False

    def __init__(
        self,
        required_sections: Optional[List[str]] = None,
        requires_json: bool = False,
    ):
        self.required_sections = required_sections or []
        self.requires_json = requires_json

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
    ) -> float:
        if not response:
            return 1.0

        penalties = []

        # 1. Avkuttings-sjekk
        stripped = response.strip()
        if stripped and stripped[-1] not in ".!?\"'»)]":
            penalties.append(0.6)

        # 2. Manglende obligatoriske seksjoner
        if self.required_sections:
            missing = [s for s in self.required_sections if s.lower() not in response.lower()]
            if missing:
                penalties.append(len(missing) / len(self.required_sections))

        # 3. JSON-validitet
        if self.requires_json:
            try:
                json.loads(response)
            except json.JSONDecodeError:
                penalties.append(0.9)

        return max(penalties, default=0.0)
