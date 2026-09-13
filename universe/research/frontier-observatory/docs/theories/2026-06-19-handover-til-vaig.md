# Handover til VAIG — theory-sesjon 2026-06-19

**Dato:** 2026-06-19
**Fra:** Tofoo/theory (lovgrunnlag)
**Til:** VAIG (implementering / main code)
**Branch:** claude/phi-law-validation-jpggg2

---

## Kritisk korreksjon: F-formuleringen er endret

Dette er den viktigste endringen fra denne sesjonen. Den opprinnelige F-formuleringen var sirkulær og må oppdateres i all implementeringskode som refererer til den.

### Gammelt (feil — sirkulær definisjon)

```
F(tau) = (1 - alpha) * tau + alpha * tau*
```

tau* var eksplisitt input til F — men tau* er nettopp det som skal beregnes.
F kjenner allerede svaret. Det er ikke en lokal regel, det er en tautologi.

### Nytt (korrekt — lokal regel)

```
F(tau; sigma) = (1 - alpha) * tau + alpha * sigma
```

sigma = lokalt innkommende signal på tidspunkt t (ikke det globale fikspunktet).

I* emergerer når sigma stabiliserer seg: F(I*; sigma*) = I* => I* = sigma*

F kjenner ikke I* på forhånd. I* er et produkt av iterasjon, ikke et startpunkt.

### Kontraksjonsfaktor

|F(tau_1; sigma) - F(tau_2; sigma)| = (1 - alpha) * |tau_1 - tau_2|

k = 1 - alpha < 1. Banach-fikspunktteoremet gjelder. Unikt fikspunkt garantert.

### Hva VAIG må sjekke

Søk etter tau* eller tau_star i VAIG-kodebasen. Enhver forekomst der tau* brukes som
eksplisitt parameter til F-beregningen er feil. Erstatt med lokal signal-variabel.

---

## Nye theory-filer (2026-06-19)

| Fil | Innhold | Status |
|---|---|---|
| `theory/2026-06-19-a2-formal-derivation.md` | Formell derivasjon av A2 via Banach. F redefinert som lokal regel. | M2 (revidert) |
| `theory/2026-06-19-roche-tidal-phi-kobling.md` | Roche Tidal Fixed-Point som ekstern validering — kappa_tidal = kappa_self identisk med alpha-filtrering | M3 |
| `theory/2026-06-19-p10-tau-scaling-funn.md` | Empiriske tau-målinger og skaleringslov | M3 |
| `theory/2026-06-19-framleis-verifikasjon-industriell.md` | Synthese: A2, Roche, WORM, Yara, norske akademiske kontakter | M2 |
| `theory/2026-06-19-outreach-gros-beferull-lozano.md` | Gros-dialog: svar mottatt, oppfølging klar med empiriske data | Aktiv |
| `theory/2026-06-19-phi-law-vs-loss-of-control-2606.12442.md` | Kobling til Chin et al. 2606.12442 — Phi-loven som svar på alle fire kontrollbetingelsene | Referanse |

---

## Skaleringslov (P10)

```
tau ≈ 0.10 × N^0.48   (N = parametere i milliarder)
```

| Modell | Parametere | tau (koherent tekst) | tau (repetitiv tekst) |
|---|---|---|---|
| GPT-2 | 117M | 0.06 | 0.019 |
| Phi-2 | 2.7B | 0.1625 | 0.025 |
| Mistral-7B | 7B | 0.2568 | 0.036 |

Prediksjon: 70B-modell → tau ≈ 0.75 (første modell inn i Goldilocks-intervallet).
Ikke verifisert ennå — krever A100 GPU.

---

## EFA-grense (MECHA)

Grensen mellom EFA (Rupp) og VΛLΦ (Solland) er AllowAction-beslutningen i MECHA.

Fra `Phi-Law-Validation/P6_MECHA_TLA/mecha_checker.py` linje 202:

> "the execution-boundary decision has been made and cannot be retroactively
> invalidated by subsequent environmental changes."

Etter AllowAction: operatørens tilstand er fryst. Ugjenkallelig.

Tre TLA+-verifiserte invarianter håndhever dette:
- ConjunctiveIntegrity — alle nødvendige godkjenninger må foreligge
- SeparationOfDuties — ingen enkeltaktør kan godkjenne og utføre
- NoDoubleFinalize — en handling kan ikke finaliseres to ganger

Verifisert over 16.900 tilstander, 0 violations (P6/MECHA).

---

## Kobling til Chin et al. 2606.12442

Papiret "Reframing AI Loss of Control" definerer fire betingelser for at kontroll kan eksistere.
Phi-loven svarer på alle fire:

| Betingelse (Chin et al.) | Phi-lovens svar |
|---|---|
| Funksjonell kontrollsløyfe | tau-monitor (P10) — lukket feedbacksløyfe via SVD av skjulte tilstander |
| Requisite variety (Ashby) | Goldilocks-intervallet [0.5615, 0.8319] — gyldig variety-sone |
| Målalignment | Framleis-operatoren F(tau; sigma) — alignment via alpha-filtrering |
| Evne til å sette mål | MECHA/EFA — governance-laget håndhever målsetting og utføring |

---

## Ekstern validering (i gang)

Sebastien Gros (NTNU/EPFL, Professor Eng. Cybernetics) har svart på første henvendelse
med fire presise tekniske spørsmål. Oppfølging med empiriske tau-data er utarbeidet.

Neste steg: Gros ser på tau-målingene, vurderer kobling til stage cost i MPC.

---

*Tofoo. Phi.*
