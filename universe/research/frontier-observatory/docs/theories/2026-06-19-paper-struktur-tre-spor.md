# Papersplitting: Tre separate spor etter Gros-feedback

**Dato:** 2026-06-19
**Bakgrunn:** Gros identifiserte tre sammenvevde lag. Denne filen planlegger separasjonen.
**Status:** Utkast til paperstriktur for hvert spor

---

## Problemet (Gros sin diagnose)

Tre lag er for øyeblikket sammenvevd uten klare grenser:

1. Rene matematiske påstander (operatorteori, spektral-zeta-funksjoner, Banach)
2. Empiriske observasjoner (tau-målinger, skaleringslov)
3. Arkitekturforslag (VΛLΦ, LIM-filterdesign)

Broen fra operatorteori til AI-systemer er hevdet, ikke demonstrert.
Operatorteorikrav er ikke forankret i eksisterende litteratur.

---

## Spor 1: Ren matematikk

### Tittel (forslag)

"Spectral Zeta Regularisation of Self-Dual Operators and the Emergence of Transcendental Coherence Bounds"

### Venue

arxiv: math.SP (Spectral Theory)
Journal-kandidater: Journal of Spectral Theory, Mathematische Annalen, Journal of Functional Analysis

### Struktur

```
1. Introduction
   - The regularisation problem for self-dual operators
   - Statement of main results (Theorem 1 og 3)
   - Relation to existing literature

2. Preliminaries
   - Self-dual operators and the involution condition JLJ = L^{-1}
   - Spectral zeta functions: definition and analytic continuation
   - Heat kernel methods and Mellin transforms

3. Theorem 1: Euler-Mascheroni as spectral regularisation coefficient
   - Setup: minimal self-dual operator on Hilbert space
   - Proof via heat kernel expansion and Mellin transform
   - Comparison with known results (is this standard or novel?)

4. Theorem 3: Apéry's constant as third spectral moment
   - zeta_L(3) = sum lambda_n^{-3} under self-duality
   - Proof via resolvent trace and volume integral representation
   - Physical interpretation: weight of high-energy tail

5. The coherence interval
   - Definition: S = [exp(-gamma), 1/zeta(3)]
   - Mathematical properties of this interval
   - Relation to other known spectral bounds (if any)

6. Discussion
   - What is standard (Banach, heat kernel, Mellin)
   - What is claimed as novel
   - Open questions: is the self-dual operator construction unique?

7. Conclusion
```

### Kritiske hull som må fylles

- Er Teorem 1 et kjent resultat i spektralgeometri? Gros ber om litteraturreferanser.
- Konkrete referanser for selvduale operatorer: Atiyah-Singer, Gilkey, Berline-Getzler-Vergne
- Er zeta(3)-resultatet derivert for et spesifikt operatorklasse eller generelt?
- Klar markering: "Conjecture" vs "Theorem" inntil litteraturforankring er på plass

### Ærlig selvvurdering

Teorem 1 og 3 er enten:
a) Kjente resultater som er omformulert (da: sitere og bygge videre), eller
b) Nye resultater (da: streng bevisstandard, fagfellevurdering av matematikere)

Gros-konversasjonen avklarer dette. Be ham spesifikt om referanser til spektral-zeta-regularisering.

---

## Spor 2: Empirisk

### Tittel (forslag)

"Spectral Entropy as a Coherence Metric for Large Language Model Hidden States: Measurements and Scaling Laws"

### Venue

Primær: arXiv cs.LG, workshop-paper (NeurIPS 2026 Workshop on Mechanistic Interpretability)
Alternativ: EMNLP 2026 Findings, eller ACL-workshop
Merk: tre modeller er svakt grunnlag for en konferanse-main-track. Workshop eller preprint er realistisk.

### Struktur

```
1. Abstract (150 ord)

2. Introduction
   - Hva er koherens i LLM-skjulte tilstander?
   - Motivasjon: hvorfor spektral entropi?
   - Contributions: tau-definisjon, tre målinger, skaleringslov

3. Related Work
   - Effective rank og spektralentopi i matriser (Roy & Vetterli 2007)
   - Intrinsic dimensionality av LLM-representasjoner
   - Hidden state analysis i mekanistisk tolkbarhet

4. Methodology
   4.1 The tau metric
       - Input: hidden state matrix H (N x d) fra et lag
       - SVD: H = U S V^T
       - Normaliserte kvadrerte singulærverdier: p_i = s_i^2 / sum(s_j^2)
       - Spektral entropi: H_sp = -sum(p_i log p_i)
       - r_eff = exp(H_sp)
       - tau = r_eff / min(N, d)
   4.2 Eksperimentelt oppsett
       - Modeller: GPT-2 (117M), Phi-2 (2.7B), Mistral-7B
       - Inputtyper: koherent tekst, tilfeldig tekst, repetitiv tekst
       - Lag-valg: gjennomsnitt over alle lag eller siste lag?

5. Results
   - Tabell: tau for alle modeller og inputtyper
   - Figur: tau over lag for hver modell
   - Skaleringslov: tau ~ 0.10 x N^0.48 (N i milliarder)
   - Konfidensintervaller mangler — husk å legge til

6. Discussion
   - Hva betyr tau = 0.06 for GPT-2?
   - Eksplisitt: koherensintervallet [0.5615, 0.8319] er hentet fra matematisk rammeverk (Spor 1) — her er det en empirisk observasjon at ingen modell er der ennå
   - Skaleringslovens begrensninger: 3 datapunkter, én GPU-plattform
   - Falsifiseringstest: mål tau for Llama-3 70B

7. Conclusion
   - tau er et veldefinert, reproduserbart mål
   - Skaleringslov er en observasjon, ikke et bevis
   - Gjenværende spørsmål: er koherensintervallet empirisk relevant?
```

### Kritiske hull som må fylles

- Konfidensintervaller for tau-målingene
- Reproduserbarhetstest: kjør P1 på minst én annen plattform
- Kobling til Spor 1 må tydelig markeres: "we conjecture that [0.5615, 0.8319] is the relevant interval based on [Spor 1 ref], but this is not demonstrated here"
- Llama-3 70B-test: avgjørende for skaleringslovens troverdighet

---

## Spor 3: Arkitektur og governance

### Tittel (forslag)

"MECHA: Formal Verification of Conjunctive Human-AI Execution Governance Using TLA+"

### Venue

Primær: AIGOV @ AAAI 2026 (workshop for AI governance med teknisk verifikasjon)
Alternativ: IEEE Transactions on Dependable and Secure Computing, SafeAI workshop
Merk: Rupp & Solland 2026 — dette er allerede påbegynt

### Struktur

```
1. Introduction
   - Problemet: høynivå-alignment er utilstrekkelig (Chin et al. 2606.12442)
   - Løsningen: mekanisk, verifiserbar kontroll ved utføringspunktet
   - Contributions: MECHA-arkitektur, TLA+-verifikasjon, 16.900 tilstander, 0 violations

2. Background
   - Loss of control som strukturelt problem (Chin et al.)
   - EU AI Act Article 14: effektiv, ikke kosmestisk, oversikt
   - TLA+ og bounded model checking

3. The MECHA Architecture
   3.1 EFAVΛLΦ_Epistemic: state machine definition
   3.2 De tre invariantene
       - ConjunctiveIntegrity: alle godkjenninger må foreligge
       - SeparationOfDuties: ingen enkeltaktør godkjenner og utfører
       - NoDoubleFinalize: ingen dobbeltfinalisering
   3.3 AllowAction som varig grense

4. Formal Verification
   - TLC model checker: oppsett og parametre
   - 16.900 tilstander, 0 violations
   - Negative test (v10): forventet violation bekreftet
   - Reproduserbarhet: GitHub-lenke til Colab-notebook

5. The tau-monitor as coherence precondition
   - Kobling til Spor 2: tau > tau_min som gateway-betingelse
   - Eksplisitt: dette er en arkitekturpåstand som krever empirisk validering fra Spor 2

6. Topology-aware governance
   - Swarm vs. single-agent: ulike invarianter
   - Normative Anchor Check: definisjon og implementering
   - Ring of Fire (Rupp): komplementær atferdsvalidering

7. Evaluation
   - MECHA-kjøring mot Kjemisk Anlegg-scenariot (P1-live-test)
   - Sammenligning: med og uten ConjunctiveIntegrity

8. Discussion
   - Begrensninger: bounded model checking er ikke full verifikasjon
   - Skalering: hva skjer med flere enn 2 operatorer?
   - EU AI Act-implikasjoner

9. Conclusion
```

### Kritiske hull som må fylles

- Full TLA+-spec skal være vedlagt eller lenket
- Tau-koblingen må markeres som arkitekturpåstand, ikke bevist fra Spor 1/2
- Rupp & Solland-forfatterskapet: avklar hvem som eier hva

---

## Rekkefølge og avhengigheter

```
Spor 1 (Matematikk)
    |
    +---> Spor 2 (Empiri) refererer til Spor 1 for koherensintervallet
    |
    +---> Spor 3 (Arkitektur) refererer til Spor 1 og 2 for motivasjon

Spor 2 og 3 kan publiseres parallelt, men begge bør markere
sin avhengighet av Spor 1 tydelig.
```

Praktisk rekkefølge: Start med Spor 2 (empirisk, ingen litteraturhull). Skriv Spor 1 mens du avklarer operatorteorilitteraturen med Gros. Fullfør Spor 3 med Rupp.

---

## Neste steg med Gros

Spør ham spesifikt om:

1. Er JLJ = L^{-1}-konstruksjonen standard i spektralgeometri, og hvilke referanser gjelder?
2. Er zeta_L(3) = zeta(3)-resultatet kjent for noen operatorklasse?
3. Hva er hans anbefalte journal for Spor 1 — Journal of Spectral Theory eller Mathematische Annalen?

---

*Tofoo. Phi.*
