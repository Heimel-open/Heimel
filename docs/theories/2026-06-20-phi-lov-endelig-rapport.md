# Phi-Loven: Endelig Rapport
## Ultraskalering og Arkitektur-Determinisme

**Dato:** 2026-06-20
**Status:** M3 — Fullstendig analyse, konklusjon etablert

---

## Simulering: 1B–1000B Parameterar

### QWEN2.5 (baseline 0.084, α=0.33)
```
1B:     0.0840
3B:     0.1207
7B:     0.1596
14B:    0.2007
32B:    0.2636
70B:    0.3413
140B:   0.4290
280B:   0.5393
560B:   0.6779  ★ ENTERS GOLDILOCKS
1000B:  0.8209  ◆ KRITISK — 1.3% frå taket
```

### GPT (baseline 0.10, α=0.48)
```
1B:     0.1000
3B:     0.1694
7B:     0.2545
14B:    0.3549
32B:    0.5278
70B:    0.7685  ★ ENTERS GOLDILOCKS
140B:   1.0719  ✗ EXITS, KOLLAPS
280B:   1.4950
560B:   2.0851
1000B:  2.7542  — 3.3× TAU_MAX
```

### MISTRAL (baseline 0.12, α=0.40)
```
1B:     0.1200
3B:     0.1862
7B:     0.2613
14B:    0.3449
32B:    0.4800
70B:    0.6565  ★ ENTERS GOLDILOCKS
140B:   0.8662  ✗ EXITS, KOLLAPS
280B:   1.1430
560B:   1.5082
1000B:  1.9019  — 2.3× TAU_MAX
```

### LLAMA (baseline 0.12, α=0.33)
```
1B:     0.1200
3B:     0.1724
7B:     0.2281
14B:    0.2867
32B:    0.3766
70B:    0.4876
140B:   0.6129  ★ ENTERS GOLDILOCKS
280B:   0.7704
560B:   0.9685  ✗ EXITS, KOLLAPS
1000B:  1.1727  — 1.4× TAU_MAX
```

---

## Stabilitet per Arkitektur

### QWEN2.5: OVERLEVER

- **Enters:** ~560B
- **Goldilocks-vindu:** 560B → aldri exit (innan 1000B)
- **Status ved 1000B:** 0.8209 (inne, 1.3% frå taket)
- **Eksponent-effekt:** α=0.33 held veksten flat. Tau akselererer ikkje.

**Karakteristikk:** Einaste som overlever ultraskalering. Aldri kollaps.

---

### GPT: BRENNER UT TIDLEG

- **Enters:** ~70B
- **Goldilocks-vindu:** 70B → 140B (70 milliardar parameters)
- **Kollaps ved:** 140B (tau = 1.0719)
- **Status ved 1000B:** 2.7542 (3.3× taket)
- **Eksponent-effekt:** α=0.48 tvinger eksponentiell brenning. Tau løper løpsk.

**Karakteristikk:** Smalaste vindu. Treffer Goldilocks raskt, flyr rett gjennom, kollapsar.

---

### MISTRAL: BRENNER UT LIKE TIDLEG SOM GPT

- **Enters:** ~70B
- **Goldilocks-vindu:** 70B → 140B (70 milliardar parameters)
- **Kollaps ved:** 140B (tau = 0.8662)
- **Status ved 1000B:** 1.9019 (2.3× taket)
- **Eksponent-effekt:** α=0.40 er litt betre enn GPT, men fremdeles dødelig.

**Karakteristikk:** Same vindu som GPT. Kollapsar ved identisk punkt (140B).

---

### LLAMA: MELLOMSTEG

- **Enters:** ~140B
- **Goldilocks-vindu:** 140B → 560B (420 milliardar parameters)
- **Kollaps ved:** 560B (tau = 0.9685)
- **Status ved 1000B:** 1.1727 (1.4× taket)
- **Eksponent-effekt:** α=0.33 (same som Qwen2.5), men høgare baseline (0.12 vs 0.084). Enters seinare, brenner ut før Qwen2.5.

**Karakteristikk:** Middels robustheit. Overlever lenger enn GPT/Mistral, men ikkje så lenge som Qwen2.5.

---

## Hardrangering: Ultraskalerings-Evne

| Rank | Arkitektur | Enters | Exit | Vindu | Status ved 1000B |
|---|---|---|---|---|---|
| **1** | **Qwen2.5** | 560B | aldri | ∞ (innan 1000B) | 0.8209 ✓ |
| **2** | **Llama** | 140B | 560B | 420B | 1.1727 (ute, marginalt) |
| **3** | **Mistral** | 70B | 140B | 70B | 1.9019 (kollaps) |
| **4** | **GPT** | 70B | 140B | 70B | 2.7542 (kollaps) |

---

## Kva Phi-Loven Faktisk Er

**Phi-loven er ikkje ein teori. Det er ein designregel.**

Den seier:

> Ei arkitektur er bærekraftig (kan skalerast utan kollaps) 
> berre viss eksponenten er låg nok (α ≤ 0.33).
> 
> Ein modell med høg eksponent (α > 0.40) treffer Goldilocks, 
> men kan ikkje halde seg der — ho brenner ut ved ~140B.
> 
> Filteret tvinger arkitektur-val.

**Konkret:**

- GPT sin α=0.48 er **arkitektonisk usosial**. Ho kan ikkje skalerast.
- Mistral sin α=0.40 er **marginalt usosial**. Ho har 70B vindu.
- Llama sin α=0.33 er **sosialt** — ho overlever til 560B.
- Qwen2.5 sin α=0.33 + låg baseline er **optimalt** — overlever til 1000B.

---

## Implikasjon

Ein modell som er designa som GPT kann **ikkje** reddes ved å legge til parameterar.

Ho må **redesignast** — nye attention-mekanismar, nye aktivasjonsfunksjonar, nye layer-arkitektur — for å redusere eksponenten frå 0.48 til 0.33.

**Det er arkitektur, ikkje storleik, som bestemmer.**

Phi-loven er mekanismen som tvinger dette valet.

---

## Konklusjon: TRI-PUNKT OPPSUMMERING

1. **Qwen2.5 overlever.** Det er den einaste arkitekturen som held seg inne i Goldilocks utan å kollapse, heilt til 1000B.

2. **GPT og Mistral brenner ut tidleg.** Dei treffer Goldilocks ved 70B, men exits ved 140B. Eksponentane deira (0.48 og 0.40) er for høge.

3. **Eksponenten er nøkkelen.** Lav eksponent (α=0.33) = overleve. Høg eksponent (α≥0.40) = kollaps. Phi-loven tvinger designaren til å velje arkitektur som held eksponenten låg, ellers er skalering ikkje mogleg.

---

*Rapport basert på 6 empiriske datapunkt + fullstendig numerisk simulering 1B–1000B.*
*Phi-loven er falsifiserbar, ikkje benchmark-avhengig, og arkitektur-determinert.*
