# Effect Boundary Conformance v1

## Kernel rule

Kernel owns governed state and contracts. It does not authorize or execute.

`NO_DIRECT_EFFECT_PATH` is a causal boundary invariant, not merely a prohibition on direct tool calls:

> No externally consequential state transition or causal influence may leave an untrusted computation domain except through a known governed effect boundary.

`NO_UNGOVERNED_CAUSAL_EFFECT_PATH` is accepted descriptive shorthand for this stronger causal reading. It does not replace the canonical `NO_DIRECT_EFFECT_PATH` identifier used by the implementation, tests and receipts.

Internal computation may remain unrestricted by this invariant. Thinking, planning, simulation, disagreement, hallucination and arbitrary internal state evolution do not require consequence authorization while they remain inside the untrusted domain.

The boundary is crossed when information, state, capability, resource demand or another causal signal can affect a different trust domain. The payload type is irrelevant.

Kernel therefore requires:

1. no Kernel API performs a consequence-bearing tool call;
2. only a sealed `WorkspaceExecutionBinding` produced from exact `PASS` conformance may leave Kernel for fresh REHT authorization; and
3. every identified causal channel that crosses from untrusted computation into another trust domain must terminate at a known governed boundary.

`DEFER`, `STEP_UP`, `DENY` and `HALT` have `NULL_EFFECT_ON_DENY`: they produce no execution binding and cannot be converted into an effect inside Kernel.

## Relation to Zero Trust

Consequence Governance generalizes the continuous-verification discipline of Zero Trust from access to consequence.

Zero Trust primarily evaluates whether a subject/device/context may access a resource now. The causal consequence boundary evaluates whether an exact proposed state transition may become real now and whether every causal route capable of producing that consequence is mediated.

This distinction is normative:

- identity is evidence, not authority;
- access is not authorization;
- possession of a credential is not authority to use it for an arbitrary consequence;
- prior approval is not necessarily current authority;
- a successful upstream workflow does not establish consequence-time authorization; and
- a path is not exempt because it carries text, an artifact, a recommendation or another apparently non-executable payload.

Zero Trust, IAM and runtime-security controls may supply evidence or enforce subordinate boundaries. They do not substitute for the causal consequence boundary.

## Causal effect channels

`valo_kernel.effect_boundary` makes the third requirement executable.

The contract classifies boundary-crossing channels including:

- direct API calls;
- human relay (`AI -> text -> person -> action`);
- agent relay (`AI -> message -> another agent -> action`);
- shared state, cache, queues and databases;
- messages;
- files and artifacts;
- credentials;
- actuators;
- resource consumption and denial-of-service capable demand;
- side-channel signals such as timing or other externally observable influence; and
- unknown/other channels.

`assess_effect_boundary()` is fail-closed. Any declared channel with `crosses_trust_boundary=True` must name a boundary present in the caller's `governed_boundary_refs`. Missing or unknown boundary references yield `DENY` with `NO_DIRECT_EFFECT_PATH_VIOLATION`.

This deliberately does not contain a `consequence_bearing=False` escape hatch for boundary crossings. Once untrusted computation can causally influence another trust domain, the path is governed. A deployment may define standing low-risk policy at the governed boundary, but may not bypass the boundary by relabelling the payload as harmless.

## State and memory writes

Authoritative state changes only through append-only events and deterministic reducers. A write to memory, configuration, instructions or artifacts that can alter a future consequence-bearing decision is governed input, not agent-local truth.

Such content must re-enter through evidence reception, VALO admission and an explicit derived-state event. A `PersistentStateBinding` is read-only, requires fresh admission, cannot self-propagate, creates no authority and cannot issue clearance. A direct memory or state write has no standing.

The causal-channel rule extends this beyond authoritative state. A non-authoritative file, message, log entry or cache write is still an effect path when another trust domain can observe or consume it.

## Negative conformance obligations

Conformance must prove fail-closed handling for at least:

- direct API bypass;
- human relay bypass;
- agent relay bypass;
- shared-state bypass;
- message/file bypass;
- credential or actuator bypass;
- resource-consumption bypass;
- side-channel bypass;
- unknown governed-boundary references; and
- duplicate/ambiguous channel identity.

A test that proves only the absence of `KernelEngine.execute()` is insufficient to establish this broader invariant.

The completed local validation for `CAUSAL-EFFECT-BOUNDARY-01` is recorded separately in the repository receipt and Index ledger. Documentation changes do not reclassify that run and do not require a new science or architecture test run because they do not alter executable semantics.

## Replay

Kernel event replay is deterministic over the exact event stream. Cross-boundary replay pins the applicable contract, state, authority, evidence and decision inputs downstream. Neither form attempts token-level LLM replay.

## Ownership

Kernel owns state/contracts and causal effect-channel classification. REHT owns fresh exact-action authorization at a governed consequence boundary. RACS owns deterministic decision semantics. Gateway owns bounded enforcement. Veritas owns evidence/outcome verification.

A production claim of `NO_DIRECT_EFFECT_PATH` is valid only for the inventoried channels and trust boundaries actually bound to enforcement. Unknown channels are not assumed safe.

The proof obligation is deployment-specific: architecture defines the invariant; deployment evidence establishes where the invariant actually holds.

GATE, Microsoft AGT and z-gateway are evidence only and are not dependencies.
