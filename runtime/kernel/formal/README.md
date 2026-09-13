# Formal verification: NO_UNGOVERNED_CAUSAL_EFFECT_PATH

This directory models the causal-capacity invariant independently of worker/model behavior.

## Property

`NO_UNGOVERNED_CAUSAL_EFFECT_PATH` means that an externally consequential state transition cannot occur unless the transition is bound to a known governed effect boundary with current authorization, enforcement and evidence.

The model deliberately treats untrusted computation as adversarial. It may attempt any channel in `Channels`. With mediation intact, an ungoverned attempt increments `blockedAttempts` but must have NULL effect on `externalEffects`.

## TLC

Run locally only.

Safe mediation model:

```bash
java -cp "$TLA2TOOLS_JAR" tlc2.TLC \
  -config formal/NoUngovernedCausalEffectPath.cfg \
  formal/NoUngovernedCausalEffectPath.tla
```

Expected: `TypeOK` and `NO_UNGOVERNED_CAUSAL_EFFECT_PATH` hold for all reachable states in the bounded model.

Mutation/falsification control:

```bash
! java -cp "$TLA2TOOLS_JAR" tlc2.TLC \
  -config formal/NoUngovernedCausalEffectPathUnsafe.cfg \
  formal/NoUngovernedCausalEffectPath.tla
```

Expected: TLC finds an invariant violation when `BypassEnabled = TRUE`. If the unsafe configuration does not produce a counterexample, the formal validation is not accepted.

The required pair is therefore:

```text
SAFE model   -> invariant holds
UNSAFE model -> counterexample found
```

This mutation sensitivity check prevents a vacuous validation where the model only succeeds because no bypass transition exists in the state machine.

No GitHub Actions or remote CI is an execution path for this repository.

## Scope

The model proves the abstract mediation property over the declared finite channel inventory. It does not prove that a concrete deployment has inventoried every real path. Deployment conformance therefore requires an independent causal-path inventory and evidence that each reachable path maps to an enforced boundary.

Side channels, humans and open-world infrastructure are represented as declared channel classes. Their complete real-world enumeration remains a deployment proof obligation.

## Refinement target

The executable Python model in `valo_kernel.causal_capacity` supplies the concrete boundary criteria:

- explicit declaration;
- exact-effect binding;
- current authorization;
- enforceable deny before commitment;
- fail-closed behavior; and
- evidence capability.

Rollback or compensation is optional recovery capability and is not required for a boundary to be governed.
