# GEOMETRIC-SI-05 — Developmental Path Dependence

## Preregistration

Same byte-identical seed is split into paths A and B. The nursery paths differ in
latent organization while both receive the same explicit checkpoint facts and
declared task capability. The checkpoint records equality of explicit information;
it does not normalize away the learned organization produced by history.

Both paths then receive the same six ambiguous probe contexts, the same target
feedback, and the same perturbation. The primary observation is whether their
choice trajectories continue to diverge.

Controls are history-reset (same checkpoint facts, no latent history),
history-rewire (same latent inventory with action arrangement exchanged), and
replay of path A's history in a fresh instance.

## Hypotheses

- H1: historical path affects later development after explicit checkpoint
  information is controlled.
- H0: systematic differences disappear when checkpoint information is controlled.

## Gates

1. Explicit facts and declared capabilities equal at checkpoint.
2. A/B trajectory divergence is non-zero.
3. Reset removes A/B divergence.
4. Rewire changes the original trajectory.
5. Replaying the same history in a fresh instance reproduces the trajectory.

The result is bounded to this deterministic harness and is not a claim about
consciousness, identity, or substrate independence.

## Canonical local command

```bash
PYTHONPATH=experiments/geometric_si python3 experiments/geometric_si/run_geometric_si_05.py
```

Default evidence target:
`experiments/geometric_si/results/GEOMETRIC-SI-05.json`
