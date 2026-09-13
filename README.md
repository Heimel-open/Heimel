# VALO Pilot

Valideringslag for LLM-pipelines. Hver inferanse logges til en tamper-evident WORM-logg.
Kryptografisk audit trail fra dag én — EU AI Act Article 12 compliant.

---

## Hva dette gjør

```
Din kode → validated_call() → LLM-svar + VAIG-vurdering + logg
```

Hver gang du kaller LLM-en din:
- VAIG evaluerer svaret med 8 parallelle instrumenter
- Tildeler DistrustLevel L0–L4 (TRUSTED → HALT)
- Logger inferansen til tamper-evident WORM-fil (SHA-256 hash-kjede)
- Rapporten etter piloten er kryptografisk bevis på at AI-en har fungert som påkrevd

---

## Oppsett

```bash
git clone https://github.com/nsolland/Valo-Pilot.git
cd Valo-Pilot
pip install -r requirements.txt
cp .env.example .env
```

Åpne `.env` og fyll inn:

```env
LLM_API_URL=https://api.openai.com/v1/chat/completions   # eller din endpoint
LLM_MODEL=gpt-4o
LLM_API_KEY=din-api-nøkkel
```

---

## Bruk

### Enkel drop-in

```python
from vaig_pilot import validated_call

response, result = validated_call("Oppsummer denne kontrakten: ...")

print(response)               # LLM-svaret som vanlig
print(result.distrust_level)  # 0=TRUSTED, 1=MONITOR, 2=WARN, 3=DEGRADE, 4=HALT
print(result.action)          # PROCEED / REVIEW / WARN / DEGRADE / HALT
```

### Integrer i eksisterende pipeline

```python
# Før: response = openai_client.chat(prompt)
# Etter:
from vaig_pilot import validated_call
response, result = validated_call(prompt)

if result.distrust_level >= 3:
    # Send til menneskelig gjennomgang
    queue_for_review(prompt, response, result)
else:
    deliver(response)
```

### DistrustLevel — hva betyr hva?

| | Nivå | Label | Anbefalt handling |
|---|---|---|---|
| 🟢 | L0 | TRUSTED | Lever direkte |
| 🟡 | L1 | MONITOR | Lever, logg for gjennomgang |
| 🟠 | L2 | WARN | Varsle bruker, vurder gjennomgang |
| 🔴 | L3 | DEGRADE | Send til menneskelig validering |
| ⛔ | L4 | HALT | Stopp eksekusjon, eskalér |

---

## Audit-rapport (leveranse etter pilot)

```bash
python report.py
```

Genererer `valo_pilot_report.md` med:
- Totalt antall inferanser
- PLASMA-rate (andel flagget)
- Distrust-fordeling L0–L4
- Kjedestatus (tamper-evident verifikasjon)
- Juridisk grunnlag for EU AI Act Article 12

---

## Konfigurasjon

Alle innstillinger via `.env`:

| Variabel | Standard | Beskrivelse |
|---|---|---|
| `LLM_API_URL` | localhost:11434 | Din LLM-endpoint |
| `LLM_MODEL` | llama3 | Modellnavn |
| `LLM_API_KEY` | (tom) | API-nøkkel hvis påkrevd |
| `AUDIT_LOG_PATH` | vaig_audit.jsonl | Plassering for WORM-logg |

`L4_AUTO_TRIGGER` i `config.py` er satt til `False` og skal ikke endres uten eksplisitt gjennomgang.

---

## Tilpasning — bytt ut LLM-kallet

`llm_call()` i `vaig_pilot.py` er en standard OpenAI-kompatibel klient.
Hvis dere bruker en annen klient, erstatt funksjonen:

```python
def llm_call(prompt: str, temperature: float = 0.3) -> str:
    # Bytt inn deres egen API-klient her
    return their_client.generate(prompt)
```

VAIG og WORM-loggen er uavhengig av hvilken klient som brukes.

---

## Support

Njål Solland — njaal.solland@gmail.com
