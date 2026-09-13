# Vallikat/VectorPeak PoA v3 — Dialog og konvergenspunkt, 2026-06-22

## Dokumenter mottatt

- Fleet Routing PoA Validation Results v3 (hovudrapport)
- R1 Dynamic Demand Derivation v2 (bevis for arrival-rate-invarians)
- R5 Benchmark Comparison v2 (korreksjon av c_B)
- Fleet Routing PoA V3 Script (Python-implementasjon, 10 testar)

## Korreksjon frå v2

c_B var feil sett til l_can(1) = 1 - exp(-π) ≈ 0.957 i v2.
Kanonetisk Pigou-nettverk krev c_B = 1.0 (motorveg, fri-flyt-tid normalisert til 1).

Med c_B = 1.0:
- x_opt = 1/√(2π) ≈ 0.39894 (eksakt)
- τ* = exp(-1/2) ≈ 0.60653 (eksakt)
- PoA = (1 - exp(-π)) / (1 - exp(-1/2)/√(2π)) = 1.2622 (eksakt)

V2-påstanden "0.584611 = exp(-1/2)" er tilbaketrekt. Tala stemde ikkje fordi c_B var feil.

## Testresultat v3: 10/10 PASS

T1 [ALG] — l''(x_opt) = 0: PASS (< 1e-12)
T2 [SIM] — Gradientnedstigning finn x_opt utan at det er spesifisert: PASS (|diff| = 2.94e-10)
T3 [ALG] — l(x_opt) + τ* = c_B = 1: PASS (eksakt til 15 desimalar)
T4 [ALG] — PoA = 1.2622 algebraisk: PASS
T5 [SIM] — Blind toll-søk oppdagar τ* = e^{-1/2} utan at det er sett inn: PASS (|diff| = 0.0065)
T6 [SIM] — Braess-paradoks: IBR bekreftar at toll korrigerer paradokset: PASS
T7 [SIM] — Fire topologiar: IBR toll reduserer kostnaden i alle: PASS
T8 [SIM] — M/M/∞ kø: τ* slår ingen-toll i 4/4 λ-verdiar (λ∈{2,4,8,16}): PASS
T9 [BENCH] — Lineær PoA = 4/3 (Roughgarden 2002) som metodologianker: PASS
T10 [SIM] — N=100,000 køyrety: simulert PoA = 1.2622 (0.00% avvik): PASS

## Konvergenspunkt med Tofoo

### 1. τ* = exp(-1/2) ligg inne i Goldilocks-intervallet

τ* = exp(-1/2) ≈ 0.6065
Goldilocks: [e^{-γ}, 1/ζ(3)] = [0.5615, 0.8319]
0.5615 < 0.6065 < 0.8319 — τ* ligg inne.

Dette er ikkje konstruert. Det kjem frå ein heilt uavhengig optimeringsderivering over
latencyfunction l(x) = 1 - exp(-πx²) i eit transportnettverk.

### 2. Infleksjonspunktet som invariansmekanisme (R1)

Beviset for at τ* er arrival-rate-invariant:
- l''(x_opt) = 0 (x_opt er infleksjonspunkt for l_can)
- Taylor-utvidinga av E[l(X)] rundt x_bar = rho gir: E[l(X)] ≈ l(x_bar) + (1/2)·l''(x_bar)·rho
- Ved x_bar = x_opt forsvinn korreksjonsleddet eksakt: SC_dynamic(x*) = SC_static(x*)
- τ* = exp(-1/2) er dermed robust mot stokastisk etterspurnadsvarianss — same toll for ALLE λ

Struktur: perturbering forsvinn ved x_opt fordi andrederiverte er null der.

Dette er same struktur som Lyapunov-argumentet i Gros-dialogen:
ved eit stabilt fikspunkt forsvinn også perturbering fordi systemet er lokalt flatt.
l''(x_opt) = 0 er den analoge mekanismen i transportkonteksten.

### 3. Blind T5-test som uavhengig validering

T5 søkjer over τ ∈ [0, 1.2] utan at exp(-1/2) er kjent for søkealgoritmen.
Optimum funne: τ = 0.60, som er exp(-1/2) ≈ 0.6065 innanfor eitt gittrinn (0.02).
Konstanten dukkar opp frå optimeringa, ikkje frå innsetting — same prinsipp som
at e^{-γ} og 1/ζ(3) dukka opp frå τ-måling, ikkje frå derivering.

## Kva dette IKKJE er

τ* = exp(-1/2) frå fleitruting er IKKJE τ frå transformer-spektralmåling.
Det er to uavhengige størreisar med same formel men ulik mekanikk.
Konvergensen er strukturell, ikkje identitet.

Det som konvergerer: infleksjonspunkt-mekanismen er felles. I begge tilfelle oppstår
ein naturleg konstant fordi systemet er lokalt flatt (andrederiverte null) ved optimumet.

## Status

V3-validering: FULLSTENDIG, 10/10 PASS, 2026-06-22
Korreksjon frå v2: c_B = 1.0 (ikkje l_can(1))
Issue #39 (numerisk inkonsistens): LUKKA — 0.584611 var ein c_B-feil, ikkje eit avrundingsproblem
Issues #38, #40: løyste av v3-skriptet (T8 fiksa, R1-bevis fullstendig)

Tofoo.
