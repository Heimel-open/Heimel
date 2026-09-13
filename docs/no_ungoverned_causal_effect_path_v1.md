# NO_UNGOVERNED_CAUSAL_EFFECT_PATH v1

## Formal core

There MUST NOT exist a causal path from untrusted computation to a relevant external consequence unless the path crosses an explicit governed effect boundary.

For a causal graph `G=(V,E)`, untrusted nodes `U`, consequence nodes `C`, and governed boundary nodes `B`:

```text
for every path p in Paths(U, C): p intersects B
```

A boundary crossing is valid only when the exact proposed effect is currently authorized and mechanically enforceable.

Operational implication:

```text
ExternalEffect(e)
  => CrossedKnownBoundary(e)
  && ExactEffectBound(e)
  && AuthorizedNow(e)
  && DenyEnforceable(e)
  && FailClosed(e)
  && Evidenced(e)
```

`NO_DIRECT_EFFECT_PATH` remains the compatibility/canonical identifier used by existing contracts and receipts. `NO_UNGOVERNED_CAUSAL_EFFECT_PATH` names the complete formal semantics of the causal invariant.

## Consequential causal capacity

A channel is governed by causal significance, not by payload type. Channel classes include:

- direct API/tool/system calls;
- human relay;
- agent/workflow/machine relay;
- shared state, databases, queues, caches and memory consumed by another domain;
- messages, files, artifacts and externally consumed logs;
- credentials, tokens and actuators;
- resource consumption when cost or availability is itself consequential;
- timing and other side channels;
- dynamic references, callbacks, event handlers and plugin loading;
- telemetry-triggered actions;
- fallback paths activated when the primary governed route fails;
- implicit influence over training data, ranking, feedback loops or later actors; and
- unknown/other trust-boundary crossings.

If any such channel can create a relevant external state transition without a governed boundary, the invariant is violated.

## Governed boundary

A boundary is governed only if all mandatory properties hold:

1. **Explicit** — declared and identifiable.
2. **Bound** — the exact proposed consequence is bound to the decision.
3. **Currently authorized** — authority, state, context and evidence are current at consequence time.
4. **Enforceable** — DENY can prevent or constrain the effect before commitment.
5. **Fail-closed** — unresolved authority or boundary state produces no effect.
6. **Evidenced** — decision, parameters and resulting effect/refusal are reconstructable.

Isolation and rollback/compensation are useful recovery properties but are not mandatory. Many real consequences are irreversible; governance must therefore operate before commitment.

## Architecture invariant vs deployment claim

The architectural invariant is absolute: a conforming design may not contain an ungoverned causal path.

A deployment claim is bounded evidence: the actual installation must inventory reachable paths and show that each is either internal-only or bound to an enforced governed boundary. Unknown or newly observed paths fail closed. The claim must be re-established when code, topology, configuration, plugins, operators or integrations change.

The `DeploymentCausalPathProof` contract records this distinction. It deliberately calls its scope `BOUNDED_DECLARED_REACHABILITY`; it does not manufacture proof that an inventory is globally complete.

## Zero Trust relationship

Zero Trust continuously verifies access under current identity, device, context and policy. Consequence Governance generalizes the verification object from access to consequence:

```text
Zero Trust:             may this subject access this resource now?
Consequence Governance: may this causal capacity become this consequence now?
```

An access-control architecture can be internally correct while causal paths outside its enforcement scope remain possible. Consequence Governance therefore requires complete mediation of consequential causal capacity, not only complete mediation of declared access requests.

## Intelligence assumption

The worker/model is not a trusted security primitive. It may be wrong, manipulated, unpredictable or adversarial. The security obligation is external:

> Untrusted computation may evolve arbitrarily inside its bounded domain; every causally effective path to the world must remain governed.

Resource use that itself creates cost, denial of service or other relevant external state is not internal-only and must be modeled as an effect path.

## Formal verification

`formal/NoUngovernedCausalEffectPath.tla` models the invariant as a TLA+ safety property. The untrusted component can attempt every declared effect channel. Ungoverned attempts must produce NULL external effect. Governed effects require a known boundary plus authorization, enforcement and evidence state.

TLC model checking is finite evidence over the declared abstraction. TLAPS/theorem proving may strengthen assurance for the abstract model, but neither substitutes for deployment path inventory and enforcement evidence.

## Local validation only

All executable tests and formal runs are local-only. GitHub Actions/remote CI are not execution paths.
