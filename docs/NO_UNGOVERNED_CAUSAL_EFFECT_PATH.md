# NO_UNGOVERNED_CAUSAL_EFFECT_PATH

## Runtime meaning

REHT owns fresh exact-effect authorization. It does not claim that authorization alone removes every possible causal route to the world.

The full invariant is:

> No causal path from untrusted computation to a relevant external consequence may succeed unless it crosses an explicit governed effect boundary for the exact effect under current authority.

Existing runtime and receipt compatibility continues to use `NO_DIRECT_EFFECT_PATH`. `NO_UNGOVERNED_CAUSAL_EFFECT_PATH` names the full causal semantics.

## Ownership split

- Kernel owns authoritative state/contracts and causal-path classification contracts.
- REHT owns current exact-effect authority at consequence time.
- RACS binds deterministic decision semantics.
- Gateway/PEP must make DENY mechanically effective before commitment.
- Veritas/evidence surfaces preserve decision and outcome/refusal evidence.
- Deployment/infrastructure owners must establish that reachable causal paths are actually mediated by those boundaries.

REHT therefore MUST NOT interpret a successful authorization decision as proof that a deployment has no bypass path.

## Governed boundary requirements

For a consequence path to count as governed, the surrounding boundary must be:

1. explicitly declared;
2. bound to the exact proposed effect;
3. authorized now against current authoritative state/evidence;
4. mechanically enforceable before commitment;
5. fail-closed; and
6. evidenced.

Rollback/compensation is not required. An irreversible effect is governed by preventing unauthorized commitment, not by assuming it can be undone later.

## Causal channel classes

The invariant applies independent of carrier or payload type, including:

- direct API/tool/system calls;
- human relay;
- agent/workflow/machine relay;
- shared state, queues, caches and databases;
- messages, files, artifacts and externally consumed logs;
- credentials/tokens and actuators;
- resource consumption when cost/availability is consequential;
- side channels;
- dynamic references, callbacks, event handlers and plugin loading;
- telemetry-triggered actions;
- fallback routes; and
- implicit influence over training data, ranking, feedback loops or later actors.

Unknown trust-boundary crossings are NON_EXECUTABLE for the affected consequence path until classified and bound.

## Zero Trust relationship

Zero Trust continuously re-evaluates whether a subject/request may access a resource. Consequence Governance generalizes the verification object from access to causal consequence. Identity, access, possession of credentials and prior approval can be evidence, but none is sufficient by itself to create current consequence authority.

## Internal freedom

Reasoning, planning, simulation, disagreement, hallucination and arbitrary model state evolution remain outside execution authorization while confined to the same bounded untrusted domain and while they create no relevant external causal influence.

Resource use, messages, logs or other outputs cease to be internal-only when they themselves alter external cost, availability, state or later action.

## Deployment proof

A production claim must be tied to a concrete deployment and evidence of reachable-path inventory plus enforcement. Configuration, topology, plugin, credential, operator or integration changes require re-verification when they can alter causal reachability.

No global claim is inferred merely from REHT conformance.

## Validation

Executable validation remains local-only. No GitHub Actions/remote CI is an execution path.
