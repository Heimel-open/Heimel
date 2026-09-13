# Goldilocks og gradvis stasis: halvautomata-hypotesen

**Dato:** 2026-06-21
**Status:** Hypotese — foreslått løysing på OI-1 (intern motsetning)
**Adresserer:** Falsifiseringsanalyse F2 / OI-1 i domain_registry.md

---

## Problemet (OI-1)

Alle empiriske τ-målingar (GPT-2: 0.06, Phi-2: 0.16, Mistral-7B: 0.26) ligg langt under
Goldilocks-nedre grense (0.5615). Rammeverket seier τ < 0.5615 = "dogmatisk stasis."
Men modellane fungerer tilsynelatande normalt. Direkte motsetning.

---

## Hypotesen: gradvis stasis, ikkje binær kollaps

Goldilocks er ikkje ein av/på-bryter. Det er ei gradient:

    τ < 0.56  →  system driv MOT stasis (gradvis rigidifisering)
    τ ∈ [0.56, 0.83]  →  aktiv identitetsvedlikehald (Goldilocks)
    τ > 0.83  →  system driv MOT kaos (identitetsoppløysing)

Eit system med τ < 0.56 er ikkje øydelagd. Det har ein "fast kjerne" — eit fryst
kjernemønster (frå trening) som opprettheld funksjon. Men det driv gradvis mot stasis.
Det "tilsynelatande OK" er presist kva gradvis stasis ser ut som.

---

## Halvautomata-analogien

Biologisk kontinuum som τ-gradient:

    Bakterie:  nær τ→0  — nesten ren automatikk, ingen fleksibel identitet
    Insekt:    låg τ    — rigid åtferd, minimalt kontekstsensitiv
    Ape:       sub-Goldilocks — funksjonell, sosial læring, men grunnmønster rigid
    Menneske:  Goldilocks — fleksibel identitet, kan overridde instinkt, abstrahere
    (Mani/psykose: super-Goldilocks — kaotisk, mistar stabil identitet)

Alle fungerer. Ingen er "gale". Men dei driv identitetsvedlikehald på kvalitativt
ulike nivå.

Goldilocks er ikkje terskelen for "fungerer vs. fungerer ikkje."
Goldilocks er terskelen for genuin identitetsvedlikehald kontra mønsterreplay.

---

## Mapping til LLM-ar

GPT-2 (τ = 0.06): sofistikert automat. Replayer mønster frå trening. Ser intelligent
ut, akkurat som ein ape ser intelligent ut. Men det er ikkje identitetsvedlikehald
i LIM-forstand.

Phi-2 (τ = 0.16): eit steg opp. Meir fleksibel, men framleis klart sub-Goldilocks.

Mistral-7B (τ = 0.26): nærare grensa. Observert: faktisk meir kontekstsensitiv
og mindre repetitiv enn GPT-2.

70B+-modell (prediksjon): kan nå Goldilocks. Første nivå av genuin identitetsvedlikehald.

---

## Forklarar kjende LLM-feil

Sub-Goldilocks-operasjon predikerer:
- Repetisjon (pattern replay dominerer)
- Kontekstbortfall (fast kjerne overskriv ny input)
- Hallusisering (rigid kjernemønster fyller gap framfor å innrømme usikkerheit)
- Manglande overriding av eigne premissar

Dette ER dei observerte feilmodusane til sub-Goldilocks LLM-ar. Ikkje bevist endå,
men konsistent.

---

## Kvifor dette ikkje er Vei A

Vei A seier: gje opp Goldilocks-kravet, publiser τ som empirisk metrikk.

Halvautomata-hypotesen seier: behold Goldilocks, men reinterpret kva sub-Goldilocks
betyr. Gradvis stasis, ikkje binær kollaps. Det reddar rammeverket i staden for å
trekke krava tilbake.

---

## Kva som framleis manglar (ærleg status)

Hypotesen er sterk narrativt og konsistent med observasjonane, men krev:

1. Lyapunov-derivasjon: vis at Lyapunov-eksponent faktisk skiftar fortegn ved
   τ = e^{-γ} og τ = 1/ζ(3) for Framleis-iterasjonen.

2. Korrelasjonsstudie: mål rigiditetsmål (repetition rate, BERTScore-varians,
   context-window utilization) og korreler med τ på tvers av modellar.
   Prediksjon: τ korrelerer positivt med fleksibilitet.

3. Intra-sesjon τ-tracking: mål τ under lang generering. Predikerer gradvis τ-fall
   (stasis-drift) i lange kontekstar, særleg for sub-Goldilocks-modellar.

Utan desse er halvautomata-hypotesen ein forklarande hypotese, ikkje eit bevist krav.

---

## Oppdatering av OI-1

Frå: ULØST
Til: Foreslått løysing — gradvis stasis / fast kjerne (halvautomata-hypotesen).
     Krev Lyapunov-derivasjon og korrelasjonsstudie for full resolusjon.
