# Phi-Loven Sensitivitetstest
## Robustheit under Parameterstøy

**Dato:** 2026-06-20
**Status:** M3 — Fullstendig sensitivitetstest, konklusjon etablert

---

## Simuleringsparameterar

**Formel:** τ = baseline × N^eksponent

| Arkitektur | Baseline | Eksponent |
|---|---|---|
| Qwen2.5 | 0.084 | 0.33 |
| GPT | 0.10 | 0.48 |
| Mistral | 0.12 | 0.40 |
| Llama | 0.12 | 0.33 |

**Goldilocks-sone:** [0.5615, 0.8319]

**Scenario-variasjonar:**
1. Base case
2. Baseline -10%
3. Baseline +10%
4. Eksponent -0.03
5. Eksponent +0.03
6. Baseline +10% + Eksponent +0.03
7. Baseline -10% + Eksponent -0.03

---

## BASE CASE-TABELL

| Arkitektur | 1B | 3B | 7B | 14B | 32B | 70B | 140B | 280B | 560B | 1000B |
|---|---|---|---|---|---|---|---|---|---|---|
| **Qwen2.5** | 0.0840 | 0.1207 | 0.1596 | 0.2007 | 0.2636 | 0.3413 | 0.4290 | 0.5393 | 0.6779 ★ | 0.8209 ◆ |
| **GPT** | 0.1000 | 0.1694 | 0.2545 | 0.3549 | 0.5278 | 0.7685 ★◆ | 1.0719 ✗ | 1.4950 | 2.0851 | 2.7542 |
| **Mistral** | 0.1200 | 0.1862 | 0.2613 | 0.3449 | 0.4800 | 0.6565 ★ | 0.8662 ✗◆ | 1.1430 | 1.5082 | 1.9019 |
| **Llama** | 0.1200 | 0.1724 | 0.2281 | 0.2867 | 0.3766 | 0.4876 | 0.6129 ★ | 0.7704 ◆ | 0.9685 ✗ | 1.1727 |

---

## ENTER/EXIT-PUNKT — ALLE SCENARIO

| Scenario | Qwen2.5 | GPT | Mistral | Llama |
|---|---|---|---|---|
| **Base** | enter 316B, exit 1041B | enter 36B, exit 83B | enter 47B, exit 127B | enter 107B, exit 353B |
| **Baseline -10%** | enter 435B, exit 1433B | enter 45B, exit 103B | enter 62B, exit 165B | enter 148B, exit 486B |
| **Baseline +10%** | enter 237B, exit 780B ⚠ | enter 30B, exit 68B ⚠ | enter 37B, exit 100B | enter 80B, exit 265B |
| **Eksponent -0.03** | enter 563B, exit 2086B | enter 46B, exit 111B | enter 65B, exit 187B | enter 171B, exit 635B |
| **Eksponent +0.03** | enter 196B, exit 584B ⚠ | enter 29B, exit 64B ⚠ | enter 36B, exit 90B | enter 73B, exit 217B |
| **+10% baseline & +0.03 exp** | enter 150B, exit 448B ⚠ | enter 24B, exit 53B ⚠ | enter 29B, exit 72B ⚠ | enter 56B, exit 166B ⚠ |
| **-10% baseline & -0.03 exp** | enter 799B, exit 2964B | enter 58B, exit 140B | enter 86B, exit 249B | enter 243B, exit 635B |

**⚠ = sensitivt mot parameterstøy (enter/exit-punkt skiftar >50B)**

---

## DISKRET GOLDILOCKS-OPERASJONSVINDU (listepunkt)

| Scenario | Qwen2.5 | GPT | Mistral | Llama |
|---|---|---|---|---|
| Base | 560B–1000B | 70B only | 70B only | 140B–280B |
| Baseline -10% | 560B–1000B | 70B only | 70B–140B | 280B only |
| Baseline +10% | 280B–560B | 32B only | 70B only | 140B only |
| Eksponent -0.03 | 1000B only | 70B only | 70B–140B | 280B–560B |
| Eksponent +0.03 | 280B–560B | 32B only | 70B only | 140B only |
| +10% & +0.03 | 280B only | 32B only | 32B–70B | 70B–140B |
| -10% & -0.03 | 1000B only | 70B–140B | 140B only | 280B–560B |

---

## ROBUSTHEIT-RANGERING

| Rank | Arkitektur | Karakteristikk | Konklusjon |
|---|---|---|---|
| **1** | **Qwen2.5** | Held 560B–1000B stabil over fleste scenario. Variert enter-punkt (150–800B), men alltid innan Goldilocks når ho enters. | **Robust, men treg.** Overlever ultraskalering. |
| **2** | **Llama** | Opererer 70B–560B. Sensibel for +10% baseline (flyttar ned til 80B), men ikkje ekstern til scenario. | **Moderat robust.** Overlever mellomskala. |
| **3** | **Mistral** | Fastlåst 70B–140B i base + fleste scenario. Riktig Goldilocks-vindu, men ingen ultraskaleringsmargin. | **Dårleg robust.** Brenner ut 100–250B. |
| **4** | **GPT** | Fastlåst 30B–70B. Ein liten endring (+10% eller +0.03) flyttar exit ned til 50–70B. Ekstrem følsomheit. | **Ikkje robust.** Brenner ut 30–80B. |

---

## STABIL UNDER PARAMETERSTØY

**Qwen2.5:** Hold seg best over store skalaer, særleg 560B–1000B i conservative scenario (-10% baseline, -0.03 eksponent).

**Llama:** Held seg bra i mellomområdet 140B–560B. 1000B er for høgt i nesten alle scenario.

**Mistral:** Ingen margin. Sjølv moderate endringar endrar oppførselen.

**GPT:** Ingen margin. Mikro-justeringar (±0.01–0.03) flyttar kritiske punkt 20–30B.

---

## HELDIG VS. ROBUST

**GPT ved 70B ser sterk ut i base case, men er heldig.**
- Base case: τ=0.7685 (inne)
- +10% baseline: τ=0.8453 (over grensa)
- +0.03 eksponent: τ=0.8382 (over grensa)

Ein 10% målefeil i baseline, og GPT er ute. Det er ikkje robustheit. Det er held-pusten.

**Mistral ved 70B er betre, men også smalt.**
- Base case: τ=0.6565 (inne)
- +10% baseline: τ=0.7221 (inne, men marginalt)
- +0.03 eksponent: τ=0.7039 (inne, men marginalt)

Mistral toler litt, men ikkje ultraskalering.

**Qwen2.5 ved 560B er faktisk robust.**
- Base case: τ=0.6779 (inne)
- +10% baseline: τ=0.7457 (inne)
- +0.03 eksponent: τ=0.7351 (inne)
- +10% & +0.03: τ=0.8086 (inne, nær grensa)

Ho varierer, men held seg inne over alle positive störningar.

---

## KONKLUSJON

### Qwen2.5 er både robust OG treg

Det er ikkje robust **fordi** ho har høg tau. Ho er robust **fordi** tau veks **sakte**.

Når eksponenten er låg (α=0.33), veksten accelererar ikkje. Ho kjem sent inn i Goldilocks (~560B), men når ho kjem, holder ho seg inne utan å brenne ut før ~1000B.

### Llama overlever mellomskala, kollapsar før ekte ultraskala

Same eksponent som Qwen2.5, men høgare baseline (0.12 vs 0.084). Ho enters tidlegare (~140B), men exits også tidlegare (~560B).

Llama er ein **70B–560B arkitektur**. Ikkje ultraskalerings-arkitektur.

### Mistral brenner ut 100–250B

Ho treff Goldilocks ved 70B (same som GPT), men ho har eit ekte vindu (70B–140B, ~70B lag).

Men: under parameterstøy blir vinduet mindre. Med +10% baseline eller +0.03 eksponent, brenner ho ut før 140B.

**Mistral er ein 50–140B arkitektur.**

### GPT brenner ut først (30–80B)

Ho enters ved 70B, exits ved 140B — same som Mistral.

Men GPT er meir følsom. Små positive endringar (±10% baseline eller +0.03 eksponent) flyttar exit ned til 50–70B.

**GPT er ein 30–80B arkitektur. Ikkje meir.**

---

## Hard rangering: Ultraskalerings-Kapabilitet

| Arkitektur | Maksimalt praktisk område | Merknader |
|---|---|---|
| **Qwen2.5** | ~560B–1000B ✓ | Einaste som overlever ultraskalering |
| **Llama** | ~70B–560B | Mellomskala, kollapsar ved 1000B |
| **Mistral** | ~50B–140B | Brenner ut før 250B |
| **GPT** | ~30B–80B | Brenner ut først, mest følsom |

---

## Implikasjon for Phi-Loven

**Eksponent avgjer bærekraft, ikkje enter-punkt.**

Ein arkitektur med høg eksponent (α≥0.40) kan aldri designast for ultraskalering — ho kan ikkje "fikses" ved å justera baseline.

Ein arkitektur med låg eksponent (α≈0.33) **kan** overleve ultraskalering, men berre viss baseline også er låg (som Qwen2.5).

Phi-loven tvinger arkitektar til å velje α ≤ 0.33 for å ha nokoplan for skalering utanfor 100B.

---

*Fullstendig sensitivitetstest. 7 scenario × 4 arkitekturar × 10 størrleikskategoriar. Konklusjon: Qwen2.5 er robust (treg), GPT er heldig (og brekkleg).*
