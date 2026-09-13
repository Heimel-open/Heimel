# valo-reht

The real REHT — the sole runtime authorization boundary of VALO — as a separate component. v1.1 candidate.

The authoritative runtime is deliberately narrow:

```text
Kernel -> REHT -> effect -> outcome evidence -> Kernel
```

Kernel owns operative state. REHT owns the decision about whether one exact proposed consequential transition may occur now. No other runtime component owns authority or operative state.

REHT decides ALLOW, STEP_UP or DENY from the current canonical Kernel execution context + the exact action contract. It is generic: no domain names and no hidden state.

Reasoning, planning, simulation, recommendation and telemetry remain outside execution governance while they remain inside their bounded trust domain. VAIG/BARO/semantic/behavioral/model diagnostics may supply evidence, but cannot create authority or clearance. RACS, Gateway and Veritas are subordinate effect-boundary functions/contracts, not additional governance authorities.

```text
Kernel authoritative state
        -> free worker/model reasoning where applicable
        -> exact consequence proposal
        -> fresh sealed Kernel execution context
        -> REHT
             identity / authority / scope / purpose / constraints / freshness
             exact action / state / consequence continuity
        -> ALLOW + action-bound permit
        -> mechanical governed effect enforcement
        -> outcome evidence
        -> Kernel
```

For Governed Workspace actions, conformance PASS and the Kernel origin proof are evidence inputs only. REHT verifies Kernel origin, context freshness, workspace lifetime, dependency integrity, exact action, purpose and digest continuity, then independently evaluates current authority at the authorization instant. None of those upstream artifacts can create authority by themselves.

## Consequence Governance and Zero Trust

Consequence Governance generalizes the continuous-verification discipline associated with Zero Trust from access to consequence.

Zero Trust primarily asks whether this identity/device/context may access this resource now. REHT asks whether this exact consequential state transition is authorized now under the operative state, authority, purpose, constraints and evidence that exist at the effect boundary.

Access is evidence, not authorization. Identity is evidence, not authority. A valid credential proves possession of a capability, not a current right to use that capability for any consequence. Prior approval does not automatically survive authority drift, state change or changed purpose.

Zero Trust, IAM, runtime security and agent security can operate upstream or beside REHT. They do not replace consequence-time authorization.

## Causal effect-path invariant

The canonical invariant remains `NO_DIRECT_EFFECT_PATH`, with the stronger operational meaning:

> No externally consequential state transition or causal influence may leave an untrusted computation domain except through a known governed effect boundary.

`NO_UNGOVERNED_CAUSAL_EFFECT_PATH` is descriptive shorthand for this causal reading; it does not replace the canonical identifier used by implementation, tests or receipts.

A direct API/tool call is only one possible effect path. Human relay, agent relay, shared state, files/messages, credentials, actuators, resource consumption and side-channel influence are also governed when they can causally affect another trust domain.

This creates a strict separation:

```text
untrusted internal computation
        -> proposed consequential crossing
        -> fresh REHT authorization
        -> governed enforcement
        -> external consequence
```

If another causal path reaches the external consequence, the deployment does not satisfy the invariant for that path.

Canonical execution-governance principles:

`Task success != valid success.`

`Do not govern thought. Govern consequence.`

`Capability != authority.`

`Access != authorization.`

Nominal workflow completion is not sufficient. A consequential completion is valid only when the exact action and resulting state remain within current authority and constraints. Any transformed, repaired, clamped, or replanned candidate is a new action and requires fresh REHT authorization before execution; authorization never transfers from candidate A to candidate B.

Governance may persist, but executable authority is ephemeral. Expiry, revocation, stale governed state, broken causal continuity, authority drift, or material context change requires authority to be re-established and the consequential action to be freshly authorized. Execution permits are action/attempt-bound and single-use at the effect boundary; failed invocation does not re-arm a consumed permit.

## Deployment proof obligation

The causal invariant is not an automatic claim that every integration is non-bypassable. Production deployment must inventory the actual consequential channels and demonstrate that each relevant direct and indirect path terminates at enforced governance.

If a direct API, privileged service account, legacy automation, human relay, agent relay, shared-state route, side channel or another causal path can still create the effect outside the governed boundary, the security claim does not hold for that path.

Architecture defines the invariant. Deployment evidence establishes where it actually holds.

External evidence:

- [`docs/OCL_EXECUTION_BOUNDARY_EXTERNAL_VALIDATION_2026.md`](docs/OCL_EXECUTION_BOUNDARY_EXTERNAL_VALIDATION_2026.md)
- [`docs/ACCOUNTABILITY_MACHINE_SPEED_EXTERNAL_VALIDATION_2026.md`](docs/ACCOUNTABILITY_MACHINE_SPEED_EXTERNAL_VALIDATION_2026.md)

`repo-manifest.yaml` contains the one canonical runtime dependency: `valo-kernel` at a pinned immutable SHA. External assurance harnesses may be used in tests, but they are not part of the authoritative runtime dependency graph.
