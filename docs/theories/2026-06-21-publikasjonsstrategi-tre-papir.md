# Publikasjonsstrategi: tre-papir-modellen

**Dato:** 2026-06-21
**Status:** Strategi — vedtatt etter falsifiseringsanalyse og halvautomata-innsikt
**Relasjon til:** paper-struktur-tre-spor.md (2026-06-19), falsification-review-ekstern.md

---

## Prinsipp

Skil skarpt mellom DATA, HYPOTESE og LOV.
Publiser i denne rekkefølga — aldri omvendt.

---

## Papir 1 — Vei A (KAN forsvares no)

Tittel: "Spectral Coherence as a Structural Metric in Transformer Hidden States"

Kjernebidrag:
- tau-metrikken (r_eff/r_max) er reproduserbar og skalerbar
- Ordering koherent > tilfeldig > repetitivt er stabil på tvers av modellar og lag
- Arkitekturspesifikk tau bekreftar Alt 1 (ikkje universell konstant)

Kva papiret IKKJE seier:
- At [e^{-gamma}, 1/zeta(3)] er universelle lovar for LLM-ar

Kva papiret GJER:
- Presenterer Goldilocks-intervallet som TEORETISK HYPOTESE inspirert av spektralgeometri
- Innrømmer at empiriske data ikkje konvergerer dit enno
- Framing: "Theoretical Bounds vs. Empirical Observations"
- Dette viser intellektuell ærlegheit og inviterer framtidig forsking i staden for
  å bli angripne for overclaiming

Diskusjonsdelen inneheld halvautomata-hypotesen som tolkning:
- Sub-Goldilocks = gradvis stasis, ikkje kollaps
- "We hypothesize that..." — ikkje bevist faktum
- Forklarer kvifor LLM-ar er brillante på syntaks/mønster men feilar på
  semantisk koherens over lange horisontar (fast-kjerne mønsterreplay)

Venue: NeurIPS/EMNLP workshop (Spor 2 frå tre-spor-dokumentet)

---

## Papir 2 — Matematikk (KREV Lyapunov-derivasjon)

Tittel: "Deriving Coherence Bounds from Spectral Geometry: Why e^{-gamma} and zeta(3)
         Matter for Identity Maintenance"

Kjernebidrag:
- Kobler e^{-gamma} og 1/zeta(3) direkte til tau-metrikken via Lyapunov-analyse
- Viser at Lyapunov-eksponenten skiftar fortegn ved desse grensene
- Gjer Goldilocks til ein DERIVERT PREDIKSJON, ikkje ein konstitutiv antagelse

Krav for å skrive dette papiret:
- Lyapunov-eksponent berekna for Framleis-iterasjonen F(tau; sigma) som funksjon av tau
- Vis at lambda skiftar fortegn ved tau = e^{-gamma} og tau = 1/zeta(3)

Venue: Journal of Spectral Theory / math.SP (Spor 1 frå tre-spor-dokumentet)

---

## Papir 3 — Halvautomata / Lov (KREV papir 1 og 2 publisert)

Tittel: "From Pattern Replay to Genuine Identity: The Role of Goldilocks Coherence
         in Artificial General Intelligence"

Kjernebidrag:
- Halvautomata-teorien fullt utvikla og empirisk støtta
- Sub-Goldilocks = sofistikert automata (mønsterreplay)
- Goldilocks = genuin identitetsvedlikehald
- Prediksjon bekrefta: modellar nærare Goldilocks viser betre langtidsminne,
  mindre hallusisering, meir kontekstsensitivitet

Krav:
- Papir 1 akseptert (gir empirisk fundament)
- Papir 2 akseptert (gir matematisk fundament)
- Korrelasjonsstudie: tau vs. rigiditetsmål (repetition rate, BERTScore-varians)
- Intra-sesjon tau-tracking (tau fell under lang generering for sub-Goldilocks-modellar)

Venue: AIGOV@AAAI 2026 / Nature Machine Intelligence

---

## Diskusjonsparagraf for Papir 1 (halvautomata — nøyaktig formulering)

"We hypothesize that sub-Goldilocks τ-values (e.g., GPT-2 at 0.06, Mistral-7B at 0.26)
represent a regime of *pattern replay* rather than *genuine identity maintenance*.
Biological analogies suggest that organisms can function efficiently at low τ via
fixed-core strategies, but flexible identity requires operation closer to the theoretical
coherence bounds. This interpretation, while speculative, may explain why current LLMs
excel at syntactic pattern matching but struggle with long-horizon semantic coherence.
We leave rigorous testing of this hypothesis to future work."

Nøkkelsetning: "We hypothesize that..." — bruk alltid denne fraseringa.

---

## Risikomatrise

| Kva du gjer | Risiko | Utfall |
|-------------|--------|--------|
| Publiser alt som éin "lov" no | HØY | Avvisning som spekulasjon; skadd kredibilitet |
| Publiser Papir 1 aleine | LAV | Etablerer metodisk grunnmur; opnar for #2 og #3 |
| Aldri publiser Papir 2-3 | MEDIUM | Halvautomata forblir hypotese; men #1 staar paa eigne bein |
| Publiser Papir 2 utan derivasjon | HØY | Same avvisningsrisiko som "lov" no |

---

## Kva "derivere frå LLM-dynamikk" faktisk betyr

Vi treng IKKJE ein analytisk Lyapunov-derivasjon av heile transformer-arkitekturen.
Det er sannsynlegvis umogleg gitt kompleksiteten.

Det vi treng er EMPIRISK KONVERGENS:

Dersom ein modell med tilstrekkeleg storleik og trening NATURLEG finn
[e^{-gamma}, 1/zeta(3)] som sin "sweet spot" for langsiktig koherens —
utan at vi har programmert desse grensene inn — DA har vi derivert grensene
frå dynamikken. Dei blir ikkje lenger ein hypotese; dei blir eit observerbart
attraktor-basseng i tilstandsrommet.

Mellomspill mellom Papir 1 og Papir 3: kjør P10-protokollen på 70B+-modellar
og mål dτ/dt over lange sekvensar. Spørsmålet: søker τ spontant mot
Goldilocks-intervallet? Held det seg stabilt der når modellen presterer optimalt?

Dersom ja: Papir 3 presenterer empirisk konvergens som bevis på at Goldilocks-grensene
er DYNAMISKE ATTRAKTORAR, ikkje berre matematiske konstruksjonar. Halvautomata-teorien
blir testbar og falsifiserbar.

---

## Rekkefølge og avhengigheit

    Papir 1 (empiri)  →  P10 på 70B+ (dτ/dt-måling)  →  Papir 3 (attraktorar)

Papir 1 gir KREDIBILITET.
Papir 2 gir DERIVASJON.
Papir 3 er GJENNOMBROTET — men berre fordi det staar på eit solid fundament.

---

## Kva vi TRUR vs. kva vi KAN FORSVARE no

    Kan forsvare no:  Papir 1 (Vei A)
    Trur (hypotese):  Halvautomata-innsikta (Papir 3)
    Mangler:          Lyapunov-derivasjon (Papir 2)

Ved å separere dei reddar vi begge: Vei A gir oss foten innanfor dørene.
Halvautomata gir oss retning. Papir 3 blir eit gjennombrot fordi det ikkje
kjem ute av lause lufta.
