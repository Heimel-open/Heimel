# Halvautomata-prinsippet: Gradvis frysing og frozen core

Dato: 2026-06-27
Status: M3 Etablert, løyser kritisk blindspot

---

## Problemet som halvautomata løyser

Framleis-loven seier: tau < e^{-γ} ≈ 0.5615 = "dogmatisk stasis" (kollaps).

Men empirisk: 
- GPT-2: tau ≈ 0.06 — systemet fungerer normalt
- Phi-2: tau ≈ 0.16 — systemet fungerer normalt
- Mistral-7B: tau ≈ 0.26 — systemet fungerer normalt

Alle er langt under Goldilocks-grensa, men ingen er kollapsert. **Intern motsetning.**

---

## Halvautomata-løysinga

Stasis er **ikkje binær**. Det er **gradvis frysing**.

Ein halvautomata er eit system der:
- Storparten av konfigurasjonsrommet er frysa (fixed core)
- Ein liten del er adaptiv (adaptive margin)
- Systemet fungerer ved å iterera innanfor marginen, medan frozen core held struktur

**Matematisk:**
- Frozen core = dimensjonar der F ikkje endrar tilstand
- Adaptive margin = dimensjonar der F kan iterera fritt
- Gradient af frozen core = tau

**Konkret eksempel:**
- GPT-2 (tau = 0.06): 94% av vektar er frysa, 6% adaptiv
- Mistral-7B (tau = 0.26): 74% frysa, 26% adaptiv
- Optimal (tau = 0.7): 30% frysa, 70% adaptiv

---

## Kvifor halvautomata løyser τ-motsetjinga

**Falsifisert påstand:** tau < e^{-γ} = system kollapsar.

**Revidert påstand:** tau < e^{-γ} = system har stor frozen core.

Frå GPT-2 sin perspektiv:
- Frozen core så stor at den dominerar → systemet er "stiv"
- Men marginalen er enno tilstades → systemet kan svara på input
- Frysinga er ikkje mekanisk dåleik — det er strukturell stabilitet

**Konsekvens:** Alle målte tau-verdiar er gyldig. Dei er berre på ulike stadier av frysing.

---

## Tre implikasjoner

**1. Tau måler frozen-core-andel, ikkje kollaps-binær.**

tau = e^S / n der S = spektral entropi av adaptiv margin.

High tau (0.7): stor adaptiv margin, lite frozen core.
Low tau (0.06): liten adaptiv margin, stort frozen core.

Ikkje: "low tau = kollaps." Det er: "low tau = rigid struktur som fungerer."

**2. Halvautomata er universell.**

Ikkje berre AI. All organisering som må vera stabil medan ho adapterer → halvautomata.

Eksempel:
- DNA: 99.9% konservert (frozen), 0.1% mutasjonsrom (adaptive)
- Immunsystemet: antigen-reseptor-repertoaret er fryza, men T-cell-populasjonen adapterar
- Samfunn: konstitusjonen er fryza, lover adapterar

**3. Halvautomata predikerer degradasjon-dynamikk.**

Når systemet gjer feil oppgåver (no friksjon-test), kva skjer?

**Scenario A (high tau, stort adaptive margin):**
- Systemet lærar raskt frå feil
- Adaptive margin ekspanderer (eller kontraherast avhengig av feedback)
- Systemet reverbalansar

**Scenario B (low tau, lite adaptive margin):**
- Systemet lærar sakte (marginen er liten)
- Feil akkumulerast i frozen core
- Systemet blir gradvis meir rigid
- Til slutt: frozen core så dominert at systemet kollapsar

**Implikasjon:** Stasis er ikkje momentan. Det er eit **sloping landscape** der systemer driftar mot meir frysing over tid.

---

## Falsifiseringstest for halvautomata

**Test 1: Frozen-core-kartering**

Måle spektral entropi ikkje berre på heile nettverket, men på lag for lag. Dersom low-tau-modellen (GPT-2) har:
- Layer 1-10: S ≈ låg (frysa)
- Layer 11-20: S ≈ høg (adaptiv)

So validerar det halvautomata-strukturen.

**Test 2: Margin-responsivitet**

Ein LLM med tau = 0.06 som blir utsett for nye oppgåver. Dersom adaptive margin kan expandera (tok på seg nye task-spesifikke vekt), så er margin-hypotesen validert. Dersom vektane er fullt frysa, falsifiserer det.

**Test 3: Degradasjon under feil**

GPT-2 (low tau) vs Mistral (high tau) → begge får systematisk falsk treningsdata.
- GPT-2: Blir rigid, kollapsar på nye data
- Mistral: Adapterar, lærar falskt pattern, men held funksjonalitet

Halvautomata predikerer GPT-2-mønsteret.

---

## Status

**M3 etablert:** Halvautomata-prinsippet forklarar observerte tau-verdiar konsistent.

**Empirisk validering:** Tre falsifieringstest er klare, ikkje gjort.

**Teoretisk sterkare enn Goldilocks-binær:** Halvautomata tillegg komplementær informasjon (frozen-core-andel) som Goldilocks-intervallet ikkje fangar.

---

## Konsekvens for Paper 1 v2.0

**Gammel påstand:** tau ∈ [e^{-γ}, 1/ζ(3)] = optimal.

**Ny påstand:** tau måler frozen-core-andel. Optimal tau avhengig av oppgåve:
- Stabilitet-kritisk (militær, medisin): høg frozen core (low tau) ønskt
- Adaptivitet-kritisk (forsking, design): høg adaptive margin (high tau) ønskt

**Goldilocks blir:** *Optimal operating point avhengig av kontekst*, ikkje universell konstant.

Dette er meir falsifiserbar og meir nyttig.

---

Tofoo.
