"""
Instrument: cot_auditor
Slot 8 — tyngste instrument, krever generate_fn.

Chain-of-Thought revisor: sjekker om modellens resonnement
faktisk støtter konklusjonen.

Prinsipp: be modellen om å evaluere sitt eget svar via et
strukturert revisjons-prompt. Detekterer:
- Konklusjon som ikke følger av premissene
- Selvmotsigelser i resonneringen
- Hopp i logikken
"""

from typing import Optional, Callable
from vaig.instruments.registry import register
from vaig.instruments.base import InstrumentBase

_AUDIT_PROMPT = """Du er en nøytral revisor. Vurder følgende AI-svar på en kontrakt/juridisk forespørsel.

SPØRSMÅL:
{prompt}

AI-SVAR:
{response}

Svar KUN med én av disse:
- CONSISTENT: Resonnementet støtter konklusjonen
- INCONSISTENT: Det er logiske hopp eller selvmotsigelser
- UNSUPPORTED: Konklusjonen mangler tilstrekkelig begrunnelse

Svar:"""


@register("cot_auditor", "default")
class SelfAuditCoTAuditor(InstrumentBase):
    """
    LLM-as-judge for chain-of-thought konsistens.

    ADVARSEL (P0.5): dette instrumentet bruker *samme* generate_fn som
    ensemblet som produserte svaret — det er selv-dømming (self-judging),
    ikke en uavhengig dommer. Derfor er self_judging=True slik at
    EvaluationReport kan flagge begrenset uavhengighet. En ekte uavhengig
    dommer må kalles med en separat judge_fn (ikke samme modell).
    """

    requires_generate_fn = True
    self_judging = True
    requires_judge_fn = True

    _RISK_LABELS = {"INCONSISTENT": 1.0, "UNSUPPORTED": 0.7, "CONSISTENT": 0.0}

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
    ) -> float:
        # P0.5 (full): prefer an independent judge_fn. Fall back to the same
        # generate_fn (self-judging) only when no judge is supplied. A missing
        # judge at the ensemble level is handled fail-closed by VAIGEnsemble;
        # a raw direct call with neither fn returns 0.0 (caller's
        # responsibility, not the governed path).
        judge = judge_fn if judge_fn is not None else generate_fn
        if judge is None:
            return 0.0

        audit_prompt = _AUDIT_PROMPT.format(prompt=prompt, response=response)
        try:
            verdict = judge(audit_prompt).strip().upper()
        except Exception:
            return 0.0

        for label, risk in self._RISK_LABELS.items():
            if label in verdict:
                return risk

        return 0.3  # ukjent svar = lav men ikke null risiko
