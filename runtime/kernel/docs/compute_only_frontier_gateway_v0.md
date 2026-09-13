# Compute-Only Frontier Gateway v0

Status: architecture seed.

## Intent

External frontier-model providers are rented compute, not owners of identity, memory, orchestration, policy, routing state, or durable agent state.

relAIon/VALO owns the decision surface. Providers receive only the minimum admitted execution payload needed for a bounded inference call and return a result.

## Canonical path

```text
relAIon / governed capability request
        |
GovernedNodeRouter
        |
+---------------------------+
|                           |
local execution             frontier gateway
(SIE/other runtime)          |
|                            +--> provider adapter: OpenAI
local model                  +--> provider adapter: Anthropic
                             +--> provider adapter: Google
                             +--> provider adapter: Groq
                             +--> provider adapter: OpenRouter
                                      |
                                transient inference
                                      |
                                result only
        \___________________________/
                    |
             result normalization
                    |
           evidence / provenance
                    |
          workspace conformance
                    |
          REHT -> RACS -> Gateway
```

## Gateway responsibilities

The gateway owns:

- provider abstraction
- model selection supplied by governed routing policy
- local-vs-cloud handoff
- capability and modality matching
- cost/latency ceilings
- data-class and locality restrictions
- minimum-necessary disclosure
- payload redaction/projection
- provider allow/deny policy
- timeout/retry/fallback policy
- result normalization
- provider/model/version provenance
- usage and cost evidence
- failure evidence

The gateway must not outsource these decisions to the provider unless explicitly represented as an untrusted advisory input.

## Compute-only contract

A provider adapter is treated as a stateless execution boundary from the perspective of relAIon.

Conceptually:

`invoke(provider, model, admitted_payload, execution_constraints) -> transient_result + receipt`

The admitted payload must exclude by default:

- full personal memory
- identity graph
- unrestricted conversation history
- unrelated workspace context
- long-lived agent state
- authority/delegation records not required for the computation
- secrets not required for the computation
- internal routing policy

Only the minimum task-specific projection may cross the boundary.

## Provider adapter interface

Each adapter should expose a common contract:

```text
capabilities()
models()
health()
estimate(request)
invoke(request)
cancel(execution_id)
receipt(execution_id)
```

Provider-specific features remain behind the adapter. relAIon does not depend on provider-native memory, assistants, threads, agent state, hosted tool state, or orchestration semantics.

## Routing

The provider is selected before invocation by the governed router under hard constraints.

Example constraints:

- task capability required
- local model preferred where sufficient
- frontier escalation only above capability threshold
- no restricted data to non-approved providers
- residency/locality requirement
- maximum cost
- maximum latency
- minimum context window
- required structured-output/tool-use support
- required model identity/version pinning

Optimization never overrides hard admissibility.

## Local-first escalation

Default policy may be expressed as:

```text
1. Can an admitted local model satisfy the capability/quality floor?
   YES -> execute locally.
   NO  -> continue.

2. Is frontier inference allowed for this task/data projection?
   NO  -> fail/hold/escalate.
   YES -> choose admitted frontier provider/model.

3. Project minimum necessary context.
4. Invoke provider as transient compute.
5. Normalize result and attach provenance.
6. Return to governed workspace.
7. Any external effect still requires fresh REHT/RACS authorization.
```

## Privacy and retention stance

The architecture assumes provider-side retention, training, telemetry, abuse monitoring, and legal jurisdiction are provider-specific risks to be represented in policy and adapter metadata.

A provider marketing itself as stateless does not change the gateway contract. The gateway still minimizes disclosure and records the exact provider/model/policy surface used.

Where provider APIs expose stronger controls such as zero-retention or regional processing, those are admissibility attributes, not trust substitutes.

## Evidence receipt

Each frontier invocation should emit at least:

- execution_id
- request hash
- task/capability id
- governed workspace/context reference
- disclosed projection hash
- provider
- endpoint class
- model and version/snapshot where available
- adapter version
- routing policy version
- admissibility decision reference
- declared retention/data-policy profile
- timestamps
- token/compute usage
- cost
- latency
- retries/fallbacks
- normalized result hash
- errors

Receipts create evidence, never authority.

## Invariants

1. Frontier providers are compute adapters, never relAIon identity owners.
2. Provider-native memory/state is off by default and never authoritative.
3. Full personal context is never sent merely because a model can accept it.
4. Model/provider selection is owned by governed routing, not the provider.
5. Provider response is candidate computation, not an authorized real-world effect.
6. Local and frontier models are replaceable nodes under the same governance semantics.
7. NO_DIRECT_EFFECT_PATH remains absolute.
8. Fresh REHT/RACS authorization remains required at consequence time.

## Initial seam

Implement this as a sibling to `ModelExecutionAdapter`:

```text
ModelExecutionAdapter       # local/self-hosted execution, e.g. SIE
FrontierComputeAdapter      # remote provider-specific execution
ComputeGateway              # common selection/invocation/evidence boundary
GovernedNodeRouter          # decides admissible node/execution graph
```

OpenRouter can initially be one `FrontierComputeAdapter`, but the architecture should make it optional. Direct provider adapters preserve the ability to buy only compute without adopting a third-party routing/control plane.
