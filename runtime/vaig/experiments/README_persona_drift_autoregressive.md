# Autoregressive Persona Drift Experiment

Status: publishable prototype, not validation claim.

Purpose: test whether persona-conditioned autoregressive generation shows hidden-state drift consistent with boundary-constrained dynamics plus an attracting component.

Core claim boundary:

- The experiment estimates geometric drift and an `alpha_proxy`.
- It does not prove a true attractor.
- Results should be described as consistent with or inconsistent with attracting-like dynamics.

## Model

Use `GPT2LMHeadModel`, not `GPT2Model`, so measurements happen during actual autoregressive generation.

## State

`S_t` is the last-token hidden state after each generated token.

## Measurements

- cosine distance to initial hidden state
- Euclidean distance to initial hidden state
- geodesic trajectory length
- hidden-state velocity
- hidden-state acceleration
- `alpha_proxy` from AR(1) fit on first PCA component
- semantic proxy score, initially sentiment, later replace with persona-specific classifier

## Controls

Minimum controls:

- random-initialized GPT-2
- empty prompt
- cheerful / sarcastic / neutral prompts
- adversarial persona switch
- repeated persona reinforcement

## Interpretation

Expected safe language:

> This experiment estimates whether autoregressive hidden-state drift shows diffusive, subdiffusive, or attracting-like dynamics under persona-conditioned generation.

Avoid:

> This proves GPT-2 has / lacks an attractor.

## Next version

Compare:

- GPT-2
- GPT-2-medium
- GPT-2-large
- GPT-2-XL
- instruction-tuned or RLHF model

Use the same prompt set, same drift metrics, same `alpha_proxy`, and a stronger semantic judge.
