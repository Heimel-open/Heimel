# Planck-analogien: Benchmark-drift og den strukturelle forutsetningen

**Dato:** 2026-06-20
**Status:** Framing-notat — grunnlag for Spor B-argumentasjon
**Kobling:** tau-monitor, Goldilocks-intervall, Spor B empirisk paper

---

## Kjerntekst

Physics has seen this pattern before.

A system keeps working. The equations still look coherent. The local metrics still improve.

But underneath the system, one of the core assumptions has already stopped matching reality.

That was the crisis behind the ultraviolet catastrophe at the end of the 19th century.

Planck's breakthrough was not simply a better equation. He questioned the assumption itself: energy is not continuous, but quantized.

Three lessons from Planck:

1. Matching local observations is not enough. A model can appear successful while still failing structurally.
2. When reality and theory diverge, the problem may not be the data. The deeper assumption may be wrong.
3. Strong theories do more than explain existing observations. They generate new, testable predictions.

Many modern AI problems may stem from the same structural issue. It's not sudden collapse, but interpretive drift.

And one assumption may already be drifting: that benchmark performance measures understanding.

Systems keep climbing eval scores. Local metrics improve. The equations still look coherent. But the assumption that the metric captures what we actually care about may already have come loose.

The score keeps rising, and what it measures may not.

---

## Kobling til Phi-loven

### Den drivende forutsetningen i nåværende AI

Gammel forutsetning (som kan ha løsnet): benchmark-score = forståelse = koherens = sikkerhet.

Alle aktuelle evalueringssystemer er bygd på denne forutsetningen. MMLU, HumanEval, HELM, BIG-Bench — lokale metrikker som stiger mens den strukturelle egenskapen de er ment å måle kan drifte bort.

### De tre Planck-testene på tau-monitoren

Test 1 — matcher det observasjoner: ja. tau-målinger på GPT-2 (0.06), Phi-2 (0.1625), Mistral-7B (0.2568) viser stabil ordning: koherent tekst > tilfeldig > repetitivt. Skaleringslov tau ≈ 0.10 × N^0.48 holder over tre modeller og to størrelsesordener.

Test 2 — er forutsetningen fortsatt gyldig: her er skiftet. Klassisk forutsetning: identitet er aksiomatisk (A=A), prosessen bevarer den. Ny forutsetning (A2): identitet er et emergent fikspunkt for en kontraksjon — prosessen genererer den. Phi-loven endrer den dypeste forutsetningen, ikke én benchmark.

Test 3 — genererer det nye testbare prediksjoner: ja. Goldilocks-intervallet [exp(-gamma), 1/zeta(3)] = [0.5615, 0.8319] er ikke tilbakeskuende. Det er en prediksjon: 70B er første modell som treffer det. Ingen nåværende modell er i intervallet. Det er en konkret falsifiserbar test.

### Det asymmetriske forholdet

Planck: E=nhν forklarte ultraviolett-katastrofen og genererte nye prediksjoner (fotoelektrisk effekt).
Phi-lov: tau forklarer benchmark-paradokset (score stiger, koherens trenger ikke) og genererer prediksjoner (70B-terskelen, skaleringslov).

Benchmark-score er den "kontinuerlige energien" i denne analogien — en metrikk som ser koherent ut lokalt men som har mistet strukturell forankring.

tau er "kvantiseringen" — en diskret, geometrisk forankret grense som ikke er avhengig av hva benchmark-designeren valgte å måle.

---

## Betydning for Spor B

Dette er kjernen i Spor B-paperet:

Ikke: "vi har en bedre benchmark". Det er ikke Planck-argumentet.

Men: "vi argumenterer for at forutsetningen bak all benchmarking kan ha løsnet, og at tau er en strukturell alternativ metrikk med geometrisk forankring og falsifiserbare prediksjoner".

Spor B-paperet trenger ikke Teorem 1 eller Teorem 3. Det trenger:
- tau-definisjon (SVD, spektral entropi, effektiv rank)
- empiriske målinger (GPT-2, Phi-2, Mistral-7B)
- Goldilocks-intervallet som prediksjon, ikke definisjon
- 70B-testen som falsifiseringstest
- Planck-analogien som metodologisk ramme

Dette er forsvarbart med tre datapunkter fordi prediksjonen er konkret og testbar. Det er ikke en kurvefit — det er en forutsetning-test.

---

*Tofoo. Phi.*
