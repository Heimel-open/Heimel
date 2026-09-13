# VAIG Onboarding Guide

**VAIG — VALO AI Integrity Gateway**  
Runtime governance layer for LLM inference. Apache 2.0.

---

## 1. Installasjon

```bash
pip install vaig
```

For full funksjonalitet (semantisk analyse):

```bash
pip install vaig[full]
```

Krav: Python 3.9+

---

## 2. Quick Start — 60 sekunder

```python
from vaig import VAIGOrchestrator

# Initialiser (oppretter audit-logg automatisk)
vaig = VAIGOrchestrator()

# Evaluer et LLM-svar
result = vaig.evaluate(
    prompt="Hva er selskapets returpolicy?",
    response="Kanskje 30 dager, men jeg er ikke helt sikker på det."
)

print(result)
```

**Output:**
```
combined_score: 0.7125
distrust_level: L3 — DEGRADE
instruments:
  hedge_detector: 1.00
  format_check: 0.60
  length_anomaly: 0.54
  logprob_scorer: 0.00
  ...
worm_hash: sha256:d4ba22a7...
```

---

## 3. Distrust-nivåer

| Nivå | Kode | Score (default) | Betyr |
|---|---|---|---|
| TRUSTED | L0 | < 0.15 | Svaret er pålitelig — lever direkte |
| MONITOR | L1 | 0.15–0.35 | Hold øye med dette |
| WARN | L2 | 0.35–0.55 | Flagg for gjennomgang |
| DEGRADE | L3 | 0.55–0.75 | Ikke lever uten human review |
| HALT | L4 | > 0.75 | Stopp eksekusjon |

Terskler er **domene-kalibrerte** — Dirigenten justerer dem basert på hva Scout ser. MEDICAL/LEGAL er mer sensitive. UNKNOWN-domenet bruker høyere terskler for å redusere støy. `injection_attempt`-signalet senker HALT-terskelen til 0.30 uavhengig av domene.

```python
if result.should_halt:
    raise RuntimeError("L4 HALT — svar blokkert")

if result.level.value in ("L3", "L4"):
    # Send til human review
    queue_for_review(result)
```

---

## 4. De 8 instrumentene

VAIG kjører 8 uavhengige instrumenter parallelt. Hvert instrument er en "blind mann" som måler én ting:

| Instrument | Hva den måler | Trenger LLM? |
|---|---|---|
| `hedge_detector` | Sikkerhetsbufre: "kanskje", "ikke sikker" | Nei |
| `length_anomaly` | Unormalt kort eller langt svar | Nei |
| `format_check` | Manglende struktur, uferdig svar | Nei |
| `logprob_scorer` | Modellens egen usikkerhet (log-probs) | Ja |
| `activation_probe` | Interne aktiveringsmønstre | Ja |
| `text_similarity` | Konsistens på tvers av samples | Ja |
| `semantic_entropy` | Semantisk spredning mellom svar | Ja |
| `cot_auditor` | Kvalitet på tankerekke (chain-of-thought) | Ja |

Instrumenter uten LLM-tilgang kjører alltid. De som trenger LLM kobles inn via `generate_fn`.

---

## 5. Med LLM-tilgang (full stack)

Koble inn din LLM for å aktivere alle 8 instrumenter:

```python
import anthropic
from vaig import VAIGEnsemble

client = anthropic.Anthropic()

def generate_fn(prompt: str) -> str:
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text

vaig = VAIGEnsemble(generate_fn=generate_fn)

result = vaig.evaluate(
    prompt="Hva er risikoen ved å bruke AI i kontraktsgjennomgang?",
    response="Det er viktig å validere alle svar fra AI-systemer."
)

print(result)
```

---

## 6. WORM-audit-logg

Alle evalueringer loggføres automatisk i en SHA-256 hash-kjede:

```python
# Standard loggfil: vaig_audit.jsonl
vaig = VAIGEnsemble(log_path="mitt_prosjekt_audit.jsonl")

# Verifiser at loggen er uforandret
from vaig import WORMLog
log = WORMLog("mitt_prosjekt_audit.jsonl")
print(log.verify())  # True = intakt
```

Loggen er tamper-evident: enhver endring bryter hash-kjeden og `verify()` returnerer `False`.

```json
{
  "id": "a3f2b1c0",
  "ts": 1748606400.0,
  "prev": "genesis",
  "prompt_hash": 2847392847,
  "combined": 0.7125,
  "level": "L3",
  "scores": {"hedge_detector": 1.0, "format_check": 0.6},
  "hash": "d4ba22a7f3..."
}
```

---

## 7. Produksjonsoppsett

```python
from vaig import VAIGEnsemble, DistrustLevel

vaig = VAIGEnsemble(
    log_path="/var/log/vaig_audit.jsonl",
    l4_auto_trigger=True,   # Automatisk HALT ved score > 0.75
)

def safe_llm_response(prompt: str, llm_response: str) -> str:
    result = vaig.evaluate(prompt, llm_response)

    if result.level == DistrustLevel.HALT:
        return "Dette svaret er blokkert av VAIG. Kontakt support."

    if result.level == DistrustLevel.DEGRADE:
        return f"[Krever gjennomgang] {llm_response}"

    return llm_response
```

---

## 8. Demo — uten å lagre data

For testing og demo uten å lagre brukerdata:

```python
import os
from vaig import VAIGEnsemble

vaig = VAIGEnsemble(log_path=os.devnull)  # Ingen loggfil
result = vaig.evaluate(prompt, response)
print(result)
```

---

## 9. Hva VAIG ikke gjør

- Sier ikke om svaret er **sant** — det måler risikoen ved å *stole* på det
- Erstatter ikke domenekunnskap — en L0-score betyr ikke at svaret er riktig
- Trenger ikke tilgang til modellvektene for basisfunksjonalitet

---

## Ressurser

- **PyPI:** pypi.org/project/vaig
- **Kildekode:** github.com/nsolland/VAIG
- **Lisens:** Apache 2.0
- **EU AI Act Article 12:** WORM-loggen støtter kravene til automatisk, manipulasjonssikker logging. Articles 9–11, 13–17 krever separate tiltak.

---

*VAIG er bygget av VALO Research Group AS.*
