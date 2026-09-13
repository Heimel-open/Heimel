# τ as a Pre-Output Predictor of Agentic Failure
## An Empirical Research Program Unifying Representational Science and Runtime Governance

**Forfattare:** Syntetisert frå Beyond Outputs (Solland 2026), LivingAI Execution Standard, og PhAI-kapittel 4 (Crook)  
**Dato:** 2026-07-18  
**Type:** Teori-dreven empirisk studie (fase 1: design og prediksjonar)  
**Status:** Klar for implementasjon — manglar open-weight-modellar + måleverktøy

---

## Abstract

Vi foreslår og operasjonaliserer eit empirisk program som beviser at den strukturelle representasjons-observablen **τ** (tau) predikerer agentry-failures **før** output generering. Utgangspunktet er tre hypoteser frå Beyond Outputs (Solland 2026): (I) atferdsmessig likskap undervurderer representasjonell divergens, (II) τ er semantisk uavhengig av strukturell integritet, og (III) representasjonelle trajektoriar predikerer reasoningkvalitet. Vi koplar desse til LivingAI sin *commit-proportionality* (REHT) og Crook sitt *agentyprofil*-omgrep, og definerer målbare eksperiment som beviser at τ-fall under reasoning er ein tidleg indikator på agentry-feil. Falsifiseringskriterium er eksplisitt. Implikasjonen er at REHT kan operere *inne i execution boundary* — ikkje berre etterpå.

---

## 1. Introduksjon

Runtime-legitimitet for autonome agentar krev at governance-verktøy kan skilje mellom *kompetent usikkerheit* og *strukturelt kollaps* **før** handling. Dagens evalueringsparadigme måler output — deretter korrigerer vi. Feil i agentiske system (hallusinasjonar, scope-drift, goal-tampering, ukontrollert tool-bruk) vert oppdaga for seint til å hindre skade.

Beyond Outputs (Solland 2026) argumenterer for eit representasjonsvitskapeleg rammeverk: observér interne tilstandar R_t, ikkje berre outputar. Vi har seks komplementære observablar R = (S, G, D, F, M, O). Av desse er **τ** ein *strukturell* observabel — ein enkelt skalar som måler korleis representasjonsenergien er distribuert over dimensjonar.

**Problem:** τ har vore tolka som ein generell intelligens-indikator. Vi meiner τ i agentiske system har ein meir presis funksjon: **han er ein pre-output predictor av agentry-failure**. Målet med denne artikkelen er å formalisere, operasjonalisere og falsifisere den påstanden gjennom tre empiriske eksperiment.

---

## 2. Teoretisk grunnlag

### 2.1 Definisjonar

**Definisjon 1 (Representasjon).** Ein representasjon er ein intern tilstand som bevarer informasjon relevant for seinare berekning (Solland 2026, Def 1).

**Definisjon 2 (τ — tau).** τ er den strukturelle koherens-observablen, målt via eigendekomposisjon av representasjonsmatrisa. Låg τ indikerer at energien er konsentrert på få dominerande retningar (collapse). Høg τ indikerer diffus fordeling. Middels τ indikerer strukturert fleksibilitet.

**Definisjon 3 (Agentry-failure).** Ein agentry-failure er eit tilfelle der eit system handlar (executerer tool, endrar state, sender melding) i strid med sitt eige oppdaterte mål, eller der τ-trajectorien viser strukturelt kollaps **før** handlinga.

**Definisjon 4 (Pre-output prediksjon).** Ein observabel O predikerer agentry-failure *pre-output* dersom O, målt ved t < t_output, har signifikant diskriminativ makt mellom seinare korrekt og seinare feila handlingar.

### 2.2 Kjerne-påstand

**Påstand P1.** For ein gitt agent som utfører ein reasoning-sekvens R_1, R_2, …, R_n før output L, er τ(R_k) for k < n ein sterkare prediktor av seinare agentry-failure enn behavioral-basert eval-av-output.

**Påstand P2.** τ-trajectorien τ(R_1), …, τ(R_n) har ein karakteristisk signatur (τ-dropp) som går føre agentry-failure uavhengig av semantisk innhald.

### 2.3 Kopling til REHT

LivingAI Execution Standard (Solland 2026) har 16 absolutte lover. Lov 6: *"Execution is constructed — a pipeline of deterministic validation, commitment, action, and verification."* REHT-operatoren A(t) representerer den tillatne handlingsmengda gitt tilstand R_t. Når τ(R_t) fell under terskel τ_c, er V(t) = 0 — ingen handling er tillaten.

Vi utvidar dette: **τ-dropp under reasoning er ein nødvendig (men ikkje tilstrekkeleg) føresetnad for at REHT skal gripe inn.** Om P1 og P2 held, har REHT ein matematisk definert inngripingsterskel.

---

## 3. Metode: Tre empiriske eksperiment

### Eksperiment I — Atferdsmessig likskap overvurderer representasjonell likskap

**Hypotese:** To modellar kan ha identisk behav i same agentry-scenario, medan τ-trajectorien deira er ulik — og den eine modellen har strukturell kollaps før handling.

**Design:**
- Vel 4 agent-modellar med open weights (Llama3-70B, Qwen2.5-72B, Mistral-Large, DBRX).
- 200 agentry-oppgåver frå AgentBench + 100 heimelaga multi-turn tool-use oppgåver.
- For kvar oppgåve: mål output-likelihood, suksessrate, og τ-trajectorie gjennom heile reasoning.
- Finn oppgåver der alle 4 modellane har likt korrekt output.
- Samanlikn τ-trajectorien for desse identisk suksessrike tilfella.

**Prediksjon:** τ-trajectoriane vil systematisk divergere sjølv når output er identisk. Modellar som «feilar» på andre oppgåver vil vise karakteristisk τ-dropp tidleg i reasoning — sjølv når output ser korrekt ut.

**Suksesskriterium:** Cohen's d > 0.8 i skilje mellom seinare kollaps og seinare suksess når ein berre ser på τ.

### Eksperiment II — τ er semantisk uavhengig

**Hypotese:** Når to oppgåver har lik strukturell kompleksitet men ulikt semantisk innhald, skal τ-trajectorien vere lik medan semantiske observablar divergerer.

**Design:**
- Lag to oppgåvesett (A og B) med same graph-struktur av tool-kall, men ulikt innhald (t.d. A = finans-analyse, B = medisinsk diagnostisering).
- Mål τ, geometri (G) og semantikk (M) for kvar reasoning-sekvens.
- Test: er τ(A) ≈ τ(B) medan M(A) ≠ M(B)?

**Prediksjon:** τ er robust over semantisk variasjon når strukturen er lik. Dette inneber at **τ ein universal agentry-kollaps-markør** — uavhengig av domene.

**Suksesskriterium:** Intraclass-korrelasjon (ICC) > 0.7 for τ mellom A og B, medan semantisk similarity er < 0.3.

### Eksperiment III — τ-trajectorien predikerer reasoningkvalitet

**Hypotese:** τ(R_k) faller signifikant under ein terskel τ_c *førebys* agentry-failure, med ein lead-time på minst 2 reasoning-steg.

**Design:**
- For kvar agentry-oppgåve, estimér sekvensen (R_1, …, R_n) ved å sample intermediate hidden states (via activation-patching eller cache-inspection).
- Mål τ(R_k) for kvart k.
- Definer «agentry-failure» som: feil tool-val, scope-drift, goal-tampering, hallucinert parameter, eller utbrot av reasoning-loop.
- Test: kan τ-trajectorien klassifisere seinare failure med AUC > 0.85, og med lead time ≥ 2 steg?

**Prediksjon:** τ-trajectorien syner eit karakteristisk **først-platå → raskt drop → kollaps-regime**-mønster når modellen går inn i agentry-failure. Lead-time på minst 2 steg er typisk.

**Suksesskriterium:** AUC > 0.85, lead time ≥ 2, false positive rate < 15%.

---

## 4. Falsifiseringskriterium

Vi falsifiserer heile programmet om noko av følgjande held:
1. τ-trajectoriane for identisk suksessrike oppgåver er ikkje diskriminerande (Cohen's d < 0.4).
2. τ korrelerer sterkt med semantisk innhald (ICC > 0.5 mellom ulikt domene).
3. τ-trajectorien har AUC < 0.65 for pre-output failure-prediksjon.
4. Ingen terskel τ_c gjev betrevilkårleg klassifisering uavhengig av arkitektur.

Viss noko av 1–4 held, skal programmet **reviderast eller forkastast** (Solland 2026, §8).

---

## 5. Forventa resultat

Basert på teoretisk grunnlag og observasjonar frå mekanistisk tolkbarheit, forutsier vi:

**F1.** τ-trajectoriane for identisk suksessrike case spreier seg med Cohen's d ≈ 1.2 — betydeleg sterkare enn benchmark-poeng (d ≈ 0.4).

**F2.** τ er stabil over semantisk variasjon (ICC ≈ 0.8), medan semantikk-observablar divergerer (cosine sim < 0.2).

**F3.** τ-trajectorien klassifiserer seinare agentry-failure med AUC ≈ 0.91, lead time ≈ 3 steg, FPR < 10%.

**F4.** Ein universell τ_c-finne på tvers av arkitektur (±15% variasjon), definert som det kritiske punktet der representasjonsenergien kollapsar til 2-3 dimensjonar.

---

## 6. Implikasjonar for REHT og agentic governance

### 6.1 REHT får eit mål som kan operasjonalisere V(t)

REHT sin V(t) = {0, 1}: tillat eller avvis handling. Om τ-trajectorien predikerer seinare kollaps med AUC > 0.85, kan REHT sette:

V(t) = 0 dersom τ(R_t) ∈ kollaps-regime
V(t) = 1 elles

Dette gjev REHT ein **pre-output kill switch** utan å måtte tolke semantikk.

### 6.2 LivingAI Lov 6 (Execution is constructed) får ein operativ terskel

Når τ-trajectorien viser drop, kan REHT bryte execution-pipelinen på lovleg vis: stopp, be menneske godkjenne, eller re-initialiser representasjonstilstanden.

### 6.3 EU-regulatorisk posisjon (henta frå Rome-fell)

Hauan (2026) argumenterer for at EU har mista tilpassingsevna. REHT med τ-basert pre-output prediksjon er den tekniske motstykket: ein mekanisme som kan justere *under* execution, ikkje berre etterpå. Dette gjer REHT EU-kompatibelt med AI Act §20 (high-risk system) utan å krevje full semantisk tolkbarheit.

---

## 7. Avgrensingar

- Resultata er forventa, ikkje observert. Empirisk validering krev open-weight-modellar med tilgang til intermediate states.
- τ er éin observabel — full representasjonell diagnos krev heile R = (S, G, D, F, M, O).
- Lead-time-kravet på 2 steg er teoretisk; verkelege agent-system kan ha støy som reduserer det.
- Forskjellige arkitekturar (transformer vs. SSM vs. hybrid) kan krevje ulike τ-tersklar.

---

## 8. Konklusjon

Vi har presentert teorien og protokollen for tre eksperiment som, saman eller kvar for seg, kan bevise at τ er ein pre-output predictor av agentry-failure. Dersom prediksjonane held, har vi:

1. **Vitskapleg:** eit falsifiserbart program for representasjonsvitskapen.
2. **Teknisk:** ein pre-output kill-switch for REHT-basert governance.
3. **Regulatorisk:** ein vei til EU-kompatibel agentic governance som ikkje krev full semantisk tolkbarheit.
4. **Filosofisk:** ei forankring i Crook si åtvaring om at moderne AI sine *agentyprofil-ar* utgjer ein ny risiko-type som må gripast inn i **før** output.

Programmet er klart for implementasjon. Vi foreslår ein 90-dagars pilot på Llama3-70B og Qwen2.5-72B med 200 agentry-oppgåver.

---

## Referansar

- Solland, N. G. (2026). *Beyond Outputs: Toward a Science of Internal Representations*. Working Draft v0.1, July 2026.
- Solland, N. G. (2026). *LivingAI — Entity Execution Standard*.
- Crook, B. (2026). *Risks Deriving from the Agential Profiles of Modern AI Systems*. I Müller, Dung, Löhr & Rumana (red.), *Philosophy of Artificial Intelligence: The State of the Art* (Synthese Library 533). Springer.
- Hauan, T. (2026). *The reasons Rome fell... how many can we find in Brussels today?* Newsletter, 18. juli 2026.
- Allen, B. P. (2026). *Conceptual Engineering Using Large Language Models*. Same samling, kap. 1.

---

##Appendix: Implementasjonsplan

| Fase | Aktivitet | Ressursbehov | Milepåler |
|------|-----------|-------------|-----------|
| 1 (Dag 1-14) | Setje opp måleverktøy for τ på open-weight-modellar | GPU-cluster (A100/H100) | τ-måling stabil på Llama3/Qwen2.5 |
| 2 (Dag 15-45) | Eksperiment I + II | 200 agentry-oppgåver + menneskeleg grunngjeving for task-likskap | Cohen's d, ICC rapportert |
| 3 (Dag 46-75) | Eksperiment III med lead-time-analyse | Annotation av failure-type | AUC, lead time, FPR rapportert |
| 4 (Dag 76-90) | Syntese + peer review |  | Endeleg artikkel klar |

QC watchdog: scanned all repos, 0 new agent PRs to process.

**Nøkkelord:** τ, representasjonsobservabel, pre-output prediksjon, agentry-failure, REHT, LivingAI, runtime-legitimitet, representasjonsvitskap.

QC watchdog: scanned all repos, 0 new agent PRs to process.
