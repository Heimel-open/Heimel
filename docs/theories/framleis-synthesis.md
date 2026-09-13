# Framleis: Syntese av korpuset

**Dato:** 2026-06-16
**Kilde:** Issue #24
**Status:** Arbeidsnotat — grunnlag for Bok 4

---

## 1. Hva trudde vi vi bygde?

Vi trudde vi bygde et AI-styringssystem.

VAIG. Admissibility-laget. Lovgiveren og Tolken. L1 Guardian. TLA+-verifikasjon. WORM-logging. Phi-loven med konstantene rho, alpha, C0.

Vi trudde spørsmålet var: Hvordan hindrer vi AI-systemer i å gjøre skade?

---

## 2. Hva bygde vi faktisk?

Vi bygde en teori om kontinuitet.

Korpuset — Bok 1, Bok 2, Bok 3, VAIG, ACS, EvidenceCondition, RRP, Receipt, Accountability Thread, Phi-loven, Framleis-aksiomene — kretser om ett spørsmål:

Hva må bevares for at noe skal forbli seg selv gjennom endring?

---

## 3. Mønsteret på tvers av korpuset

| Lag | Hva som bevares | Mekanisme |
|---|---|---|
| Bok 1 | Menneskelig tanke og tilstedeværelse | Sorg som presisjonsinstrument |
| Bok 2 | Integritet i beslutningssystemer | Admissibility-laget |
| Bok 3 | Det individuelle menneskelige valget | Den neste setningen |
| Phi-loven | Koherens (tau) i [tau_min, tau_max] | C0-attraktoren, alpha=0.42 |
| Framleis A0–A10 | Eksistens gjennom transformasjon | Seleksjon under friksjon |
| VAIG | Gyldige tilstandsoverganger | Admissible transitions |
| EvidenceCondition | Evidensiell kontinuitet | Bevis-kjeden brytes ikke |
| RRP | Ansvarlighets-kontinuitet | Sporbarhet bakover i tid |
| Receipt | Chain-of-custody | Kvitteringen er beviset |

Alle lagene svarer på det samme spørsmålet fra ulike vinkler.

---

## 4. Den utvidede governance-arkitekturen (Bok 2 er delvis utdatert)

Bok 2 beskriver:

```text
Intent → Authorization → Execution → Accountability
```

Den faktiske arkitekturen er nå:

```text
Reality → Evidence → EvidenceCondition → Intent → Authority →
Authorization → Execution/Refusal → RRP → Accountability Thread → Receipt
```

Dette er ikke en pipeline. Det er Framleis som arkitektur: hvert steg bevarer noe som neste steg er avhengig av. Uten EvidenceCondition er Intent ubegrunnet. Uten RRP er Accountability ubeviselig. Uten Receipt er chain-of-custody brutt.

Bok 2 bør oppdateres for å reflektere dette.

---

## 5. Bok 3 er ikke utdatert

Bok 3 sitt mønster — Er → Blir → Framleis — er ikke erstattet av governance-arkitekturen. Det er operasjonalisert av den.

Den utvidede pipeilnen er Framleis uttrykt som maskineri.

---

## 6. Det sentrale spørsmålet for Bok 4

Hva overlever endring?

Ikke bare i AI-systemer.
I mennesker.
I organisasjoner.
I minne.
I governance.
I identitet.
I mening.

Framleis er ikke et norsk ord for "fortsatt". Det er navnet på prinsippet.

---

## 7. Hva Bok 4 bør gjøre

1. Stille spørsmålet direkte: Hva er Framleis?
2. Vise at Er → Blir → Framleis er det underliggende mønsteret i alle fire bøkene.
3. Oppdatere forståelsen av Bok 2 (governance-pipeline).
4. Knytte Framleis-aksiomene (A0–A10) til Phi-lovens matematikk.
5. Peke ut mot det som ikke er ferdig: Canon F7, Roche Tidal Fixed-Point, consilience-testen.

---

## 8. Åpne spørsmål

- Er A2 (Framleis er meir grunnleggjande enn identitet) beviselig fra Phi-loven?
- Hva er forholdet mellom Framleis og tau_sum/C0_ytre = 0.23%?
- Er Canon F7 sin 39%-konstant et uttrykk for A9 (friksjon gjer forskjell verkeleg)?
- Consilience-testen fra Kimi Agent: Aurora/Lens vs Valo — er dette en test av Framleis-prinsippet?

---

*Tofoo. Phi.*
