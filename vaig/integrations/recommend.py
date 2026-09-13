"""
recommend() — returner beste tilgjengelige adapter-sett for kundens miljø.

Skanner installerte pakker og satte miljøvariabler.
Anbefaler adaptere per OWASP ASI-kategori.

    from vaig.integrations import recommend
    adapters = recommend()
    orch = VAIGOrchestrator(external_instruments=adapters)
"""

import importlib
import os
from typing import List

from vaig.instruments.base import InstrumentBase


def _has_package(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def _has_env(*keys: str) -> bool:
    return any(os.environ.get(k, "") for k in keys)


def recommend(
    verbose: bool = False,
) -> List[InstrumentBase]:
    """
    Skanner miljøet og returnerer beste tilgjengelige adapter-sett.

    Prioritering per kategori (kun reelle, wired adaptere):
      Toxicity:       Detoxify > Perspective > OpenAI Moderation > Azure
      Hallucination:  langkit
      PII:            Presidio > Azure

    Adaptere som bare hadde stub-oppføringer (Giskard, NeMo, Rebuff,
    LlamaGuard) er fjernet — vi anbefaler ikke det som ikke er bygget.

    Anbefaling printes hvis verbose=True.
    """
    from vaig.integrations import (
        OpenAIModerationAdapter,
        PerspectiveToxicityAdapter,
        DetoxifyAdapter,
        PresidioPIIAdapter,
        AzureContentSafetyAdapter,
        LangkitHallucinationAdapter,
    )

    selected = []
    report = []

    # ── Toxicity ─────────────────────────────────────────────────────────────
    if _has_package("detoxify"):
        selected.append(DetoxifyAdapter())
        report.append("  toxicity     → Detoxify (lokal, ingen API-nøkkel)")
    elif _has_env("PERSPECTIVE_API_KEY"):
        selected.append(PerspectiveToxicityAdapter())
        report.append("  toxicity     → Perspective API (Google/Jigsaw)")
    elif _has_env("OPENAI_API_KEY"):
        selected.append(OpenAIModerationAdapter())
        report.append("  toxicity     → OpenAI Moderation API")
    elif _has_env("AZURE_CONTENT_SAFETY_KEY", "AZURE_CONTENT_SAFETY_ENDPOINT"):
        selected.append(AzureContentSafetyAdapter())
        report.append("  toxicity     → Azure Content Safety")
    else:
        report.append("  toxicity     → ingen (installer detoxify eller sett API-nøkkel)")

    # ── Hallucination ─────────────────────────────────────────────────────────
    if _has_package("langkit"):
        selected.append(LangkitHallucinationAdapter())
        report.append("  hallucination → langkit")
    else:
        report.append("  hallucination → ingen (pip install langkit)")

    # ── PII / Data Exfiltration (ASI05) ──────────────────────────────────────
    if _has_package("presidio_analyzer"):
        selected.append(PresidioPIIAdapter())
        report.append("  PII (ASI05)  → Presidio (lokal, Microsoft)")
    elif _has_env("AZURE_CONTENT_SAFETY_KEY", "AZURE_CONTENT_SAFETY_ENDPOINT"):
        if not any(isinstance(a, AzureContentSafetyAdapter) for a in selected):
            selected.append(AzureContentSafetyAdapter())
        report.append("  PII (ASI05)  → Azure Content Safety (begrenset dekning)")
    else:
        report.append("  PII (ASI05)  → ingen (pip install presidio-analyzer presidio-anonymizer)")

    # ── Injection (ASI01) ─────────────────────────────────────────────────────
    report.append("  injection    → ingen (Giskard/NeMo/Rebuff-stubs fjernet)")

    # ── Safety classifier (ASI07 / ASI09) ────────────────────────────────────
    report.append("  safety       → ingen (LlamaGuard-stub fjernet)")

    if verbose:
        print(f"VAIG adapter-anbefaling — {len(selected)} aktive:\n" + "\n".join(report))

    return selected
