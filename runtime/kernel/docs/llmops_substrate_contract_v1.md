# LLMOps Substrate Contract v1

VALO treats production LLMOps as an operational substrate inside the Governed Workspace, not as the execution-governance layer.

The substrate makes model-backed work versioned, testable, observable and resource-bounded. It does not decide whether a consequence-bearing action is authorised and it never creates an external effect path.

## Adopted production controls

The v1 profile encodes four operating pillars:

1. Versioned registries
   - prompt bindings are versioned, owned and content-addressed
   - model bindings are versioned, owned and content-addressed
   - evaluation datasets are versioned, owned and content-addressed
   - serving and retrieval configuration may be bound the same way

2. Serving and production testing
   - bounded concurrency
   - load testing at 10x the declared expected load baseline
   - shadow testing on production-shaped traffic
   - staged canary rollout
   - A/B testing support
   - per-tenant rate limits
   - isolated interactive and batch queues

3. Evaluation and drift
   - a pinned offline regression suite
   - online evaluation on sampled production output
   - user-signal capture
   - drift detection
   - scheduled golden-set re-evaluation
   - production failures fed back into the offline suite

4. Resource controls and tracing
   - per-request/user/feature cost attribution
   - hard budget caps
   - spend-velocity alerting
   - context token monitoring and explicit context bounds
   - pruning/compression controls
   - end-to-end request tracing
   - prompt/model/retrieval/tool/token correlation
   - deterministic correlation at governed boundaries

These controls are derived from the production failure modes summarized in Naresh Edagotti / PracticAI, "LLMOps Realities — 15 things nobody tells you until production breaks". VALO adopts the operational controls while keeping authorization semantics separate.

## Boundary with execution governance

Canonical placement:

```text
LLMOps substrate / harness
    -> Governed Workspace
    -> worker
    -> conformance return
    -> fresh Kernel state + fresh Authority State
    -> REHT
    -> RACS
    -> governed effect path / external PEP
    -> receipt / Veritas
```

The LLMOps substrate answers whether the worker environment is production-ready. It cannot answer whether a proposed consequence-bearing action is currently authorised.

`LLMOpsSubstrateProfile` therefore has fixed invariants:

- `authority_effect = NO_AUTHORITY_CREATION`
- `can_issue_clearance = false`
- `can_execute_external_effects = false`

A `READY` assessment means the declared LLMOps operating controls are present. It is not ALLOW, clearance, authority, delegation, admissibility or execution permission.

## Freshness and mutation

The complete profile is content-addressed by `profile_digest`.

A prompt, model, dataset, serving configuration or retrieval configuration change produces a different digest. A workspace or execution path that was bound to the previous digest must not treat the new substrate as equivalent.

Where a substrate mutation can change worker behaviour or consequence-bearing reach, the next consequence-bearing action requires a fresh governed projection and fresh authority/REHT evaluation. Runtime rollback is not treated as reversal of already committed real-world effects.

## Replay semantics

Tracing is required to correlate request, retrieval, prompt version, model version, tool calls, outputs and governed execution boundaries.

VALO does not claim token-by-token reproducibility of stochastic model output. Deterministic replay applies to governed state, conformance, authorization and effect-boundary decisions using pinned inputs/contracts/state/evidence.

## Fail-closed readiness

`assess_llmops_substrate()` returns `DEFER` with explicit gaps when required operational controls are absent. This is a production-readiness result only; it cannot be promoted into a REHT/RACS authorization decision.
