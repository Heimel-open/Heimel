# BCCH – Persona-attractor: base model vs RLHF model

## Formål

Samle sporet slik at det ikke forsvinner: neste eksperimentelle steg for Boundary-Constrained Coherence Hypothesis (BCCH) er å teste om instruksjons-/RLHF-modeller viser sterkere attraktor-lignende dynamikk i residualstrømmen enn base-modeller.

Dette er ikke en konklusjonsfil. Det er et forskningsnotat / huskeliste.

## Hypotese

Predikert utfall:

- Base model: svak eller fraværende relaksasjon etter tilstandsperturbasjon.
- Instruct/RLHF model: målbar positiv relaksasjonsrate alpha etter perturbasjon.

Mer presist:

```text
base model          -> alpha ≈ 0 eller lav
                    -> høyere drift
                    -> større effektiv dimensjon
                    -> svakere persona-stabilitet

instruct/RLHF model -> alpha > 0
                    -> lavere drift
                    -> lavere / mer strukturert effektiv dimensjon
                    -> sterkere persona-stabilitet
```

## Eksperimentelt design

Anbefalt par:

- Zephyr-7B-beta som instruksjons-/RLHF-modell.
- Mistral-7B base som kontrollmodell.

Samme oppsett for begge:

- samme systemprompt
- samme brukerprompt
- samme tokenlengde
- samme epsilon-serie
- samme perturbasjonstidspunkt
- samme alpha-estimator

## Måling

1. Kjør baseline-bane `S_t`.
2. Injiser tilstandsperturbasjon i `past_key_values` ved tidspunkt `t0`.
3. Kjør perturbert bane `S'_t`.
4. Mål:

```text
d(t) = ||S'_t - S_t||
```

5. Fit:

```text
d(t) = d0 * exp(-alpha * t)
```

## Tolkning av alpha

```text
alpha > 0   -> perturbasjonen dør ut; stabil attraktor
alpha ≈ 0   -> nøytral drift; svak eller ingen tilbakeføring
alpha < 0   -> divergens; perturbasjonen vokser
```

Dette må tolkes som lokal relaksasjon, ikke som en global identitetsgaranti.

## Epsilon-regimer

Forventet oppførsel når perturbasjonsstørrelsen øker:

| epsilon | Forventet alpha | Tolkning |
|---:|---:|---|
| 0.001–0.01 | omtrent konstant | Lineært regime nær likevekt |
| 0.01–0.05 | omtrent konstant / svakt lavere | Fortsatt innenfor lokal basin |
| 0.05–0.15 | lavere | Ikke-linearitet begynner å dominere |
| 0.15–0.30 | betydelig lavere | Nær basin boundary |
| >0.30 | alpha → 0 / NaN | Systemet forlater attraktorens basseng |

## Viktig presisering

Hvis alpha faller når epsilon øker, svekker det ikke BCCH. Det styrker den reviderte modellen:

- Attraktoren er lokal, ikke global.
- Grenseoperatoren `P_Ω` trengs for å holde systemet inne i attraktorens basin.
- Stabil identitet krever derfor både boundary og attractor.

## Nye hovedmål

Ikke mål bare alpha.

Mål to ting:

```text
alpha_local  = hvor raskt systemet returnerer etter liten perturbasjon
epsilon_c    = basin radius; hvor stort avvik systemet tåler før det ikke returnerer
```

Dette gir en sterkere identitetsmodell:

```text
Identitet = lokal tilbakeføring + toleranse mot avvik.
```

## Forventet mønster per persona

```text
neutral:
  større basin radius
  lavere alpha
  robust, men mindre stilsterk

cheerful:
  middels alpha
  middels basin radius

sarcastic:
  høyere alpha lokalt
  lavere basin radius
  smalere og mer skjør manifold
```

## Status

Dette er et eksperimentelt spor som bør kjøres før sterke claims publiseres.

Riktig claim per nå:

> Predicted outcome: RLHF/instruction-tuned models should exhibit a measurable positive relaxation rate alpha after hidden-state perturbation, while base models should show weaker or absent relaxation. This would support the claim that alignment training induces attractor-like dynamics in the residual stream.

Ikke skriv at dette er bevist før faktisk kjøring og replikasjon.