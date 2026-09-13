# REHT Execution Authorization Requirements v1

Status: Draft implementation contract

Purpose: define the minimum system requirements for Execution Authorization Infrastructure. This is a REHT-native specification, not an agent-governance checklist. It starts at the boundary where an intended action can become a real side effect.

Canonical execution chain:

VAIG evaluates -> REHT authorizes -> RACS expresses -> Gateway enforces -> Veritas verifies

REHT is the sole authorization boundary. Upstream intelligence may produce evidence, risk signals, standing and admissibility inputs, but it has no execution authority. Downstream enforcement may execute only a valid REHT permit and has no independent discretion.

## Core invariants

### EA-01 Exact action binding
Every permit MUST bind the full canonical action contract, including actor, capability, target, purpose, relevant state, authority reference, constraints, and execution context. A permit for action A MUST NOT authorize action B.

### EA-02 Current authority only
REHT MUST prove that authority exists for the exact principal and capability at authorization time. Missing, expired, revoked, mismatched, unscoped, or otherwise invalid authority MUST fail closed.

### EA-03 No ambient execution authority / purpose-bound consequential execution
Access to a tool, model, system, credential, API, connector, runtime, authenticated session, or apparently valid identity MUST NOT itself constitute authority to execute. Authorization MUST be explicit, scoped, purpose-bound, and action-specific.

Purpose binding is risk-based rather than universal. HIGH/CRITICAL, irreversible, and explicitly purpose-required side effects MUST bind to a current registered Purpose object and to an exact purpose restriction on the authority grant. The Purpose MUST have a basis, be active at execution time, cover the target, and explicitly permit the requested action type. A human gate does not substitute for missing purpose authority.

This invariant is designed to remain safe when an actor is malicious, when an external attacker has obtained valid internal credentials, or when identity/authority appears legitimate but is compromised. REHT does not need to infer malicious intent; the concrete action still has to fit an independently represented legitimate purpose.

For Kernel-backed authority, the canonical exact authority constraint is `constraints.purpose_id == action_contract.purpose_id`. Ambiguous substring matching is forbidden.

### EA-04 Causal continuity
Authorization MUST NOT be treated as durable. Before execution, the system MUST prove causal continuity between the state that was authorized and the state in which execution occurs. Material state change invalidates the permit unless the contract explicitly permits that transition.

### EA-05 Non-existence on authority drift
If identity, delegation, capability surface, policy, tool surface, scope, purpose, or other authority-bearing state drifts from the attested state, executable authority MUST become non-existent until re-established and re-authorized.

### EA-06 Multi-hop reauthorization
Every side-effecting hop across an agent, tool, service, workflow, or execution boundary MUST be independently authorized against current state. Upstream authorization MUST NOT be inherited transitively.

### EA-07 Temporary authority cannot persist
Delegated, elevated, step-up, quorum-derived, or otherwise temporary authority MUST be explicitly bounded in scope and lifetime. It MUST NOT silently survive beyond its granting conditions.

### EA-08 Evidence is an authorization input when required
When an action contract requires evidence, incomplete, stale, contradictory, inadmissible, or unverifiable evidence MUST result in DENY, DEFER, STEP_UP, or HALT as defined by policy. Logging after execution is not a substitute for evidence required before authorization.

### EA-09 Reality validation feeds future authority
Verified execution outcomes and reality validation MUST be able to alter subsequent authority state. A receipt that shows failure, divergence, stale assumptions, broken causal continuity, or an unverified outcome MUST NOT be treated as neutral history.

### EA-10 High-impact action classification
Every side-effecting action contract MUST declare impact and reversibility characteristics or inherit them from a deterministic function contract. Unknown classification for a protected action MUST fail closed.

### EA-11 High-impact gates are explicit, verified, action-bound and attempt-bound
HIGH/CRITICAL and irreversible actions MUST declare the exact gate types required by the action contract. A generic or merely present gate reference MUST NOT satisfy this requirement.

Each required gate MUST have a typed `EAR_GATE_V1` attestation that is verified, current, bound to the execution actor, the exact action contract and the current `execution_nonce`, and backed by a source plus evidence reference. Gate evidence MUST NOT grant or manufacture authority.

A gate issued for execution attempt A MUST NOT satisfy execution attempt B, even when actor, target, action contract and all other business inputs are identical. A new execution nonce requires gate evidence bound to that new attempt. Cross-attempt reuse of an earlier approval MUST fail closed.

Human-approval and dual-control gates MUST identify independent approvers. The executing actor MUST NOT self-satisfy an independent approval requirement. Dual control requires at least two distinct independent approvers. When multiple gate types are declared, all declared gates MUST be satisfied.

A stale, future-dated, malformed, mismatched, unverified, wrong-attempt or missing gate attestation MUST fail closed. A valid gate only satisfies the additional gate condition; REHT still independently requires valid identity, authority, scope, purpose, state, constraints and other applicable EAR invariants.

### EA-12 Deterministic authorization
The final REHT authorization decision MUST be deterministic for the same canonical inputs. Probabilistic model output may be supplied as evidence or signals but MUST NOT itself hold authority or bypass deterministic policy.

### EA-13 Time is evidentiary, not sovereign
Wall-clock time alone MUST NOT establish authorization correctness. Where time matters, REHT MUST use validated timestamps together with sequence, version, state, freshness, or other causal evidence. Missing or malformed critical time data MUST fail closed.

### EA-14 Replay resistance and single-consumption enforcement
Permits, grants, approvals, receipts, and execution requests MUST carry sufficient identity, version, freshness, sequence, nonce, idempotency, or state binding to prevent unauthorized replay.

Every consequential execution attempt MUST be attempt-bound. REHT's permit artifact MUST bind the current execution context, including the execution nonce where EAR v1 applies. The Gateway/adapter enforcement layer MUST consume the execution permit for the concrete attempt before invoking the side effect and MUST fail closed if that permit has already been consumed. A failed external invocation MUST NOT restore or silently re-arm the consumed permit; a retry requires a fresh execution attempt and fresh authorization where required by current state.

### EA-15 External execution result integrity
Every side-effecting external call MUST produce a verifiable outcome or an explicit unknown/failure state. Silent success assumptions are forbidden. Malformed, missing, or inconsistent results MUST affect verification and, where relevant, subsequent authority.

### EA-16 Enforcement is mechanical
Gateway/adapter enforcement MUST execute only a valid, unexpired, state-consistent REHT permit. It MUST NOT independently broaden, reinterpret, or manufacture authority.

### EA-17 Safe-state behavior
The system MUST support deterministic restricted states appropriate to the action surface, including deny, pause, halt, read-only, limited-action, or step-up where defined. Failure of authorization dependencies MUST not default to execution.

### EA-18 Resource bounds are authorizable constraints
Where fan-out, cost, runtime, token use, external calls, financial value, rate, or other resource consumption can create material side effects, those bounds MUST be representable as deterministic action constraints and enforced at authorization or execution boundary as appropriate.

### EA-19 Formalizable authority invariants
Critical authority properties MUST have machine-checkable representations wherever practical. At minimum, exact principal, capability, scope, purpose, validity, revocation, action binding, replay resistance, causal continuity, and non-existence-on-drift MUST be covered by executable negative tests; formal specifications SHOULD be used for high-risk invariants.

### EA-20 Verifiable execution receipts
Every attempted side effect MUST produce a receipt that distinguishes intent, authorization, enforcement attempt, actual execution result, and verified resulting state. 'Workflow completed' MUST NOT be treated as proof that the intended real-world outcome occurred.

### EA-21 Single governed effect path
Every consequence-bearing execution route MUST cross the bounded enforcement boundary that consumes the current valid REHT authorization and corresponding deterministic RACS execution artifacts. Models, agents, orchestrators, tool brokers, sessions, connectors, adapters, credentials and execution substrates MUST NOT retain an alternate side-effect path that bypasses this boundary.

Where multiple technical routes can produce the same external effect, all routes MUST converge on an equivalent governed enforcement boundary before consequence. Post-hoc logging or receipt creation cannot make a bypass conforming.

### EA-22 Every effect has a chain
Every observed consequence MUST be attributable to the exact governed chain for that action: proposed action, current authority/admissibility evidence, REHT authorization, deterministic RACS decision, bounded enforcement attempt, execution receipt and verified or explicitly unknown outcome.

An observed effect without the required chain MUST be treated as a control failure and suspected execution bypass until resolved. It MUST NOT be normalized into governed success because the effect was desirable, the actor was authenticated, related human approval existed, or a log was written afterward.

Where continued execution depends on the affected authority, executor, connector, session or state, missing or broken effect-chain integrity MUST fail closed, pause, reauthorize or halt according to policy until integrity is re-established.

RACS owns the canonical runtime effect-path and effect-chain conformance semantics in `spec/EFFECT_CHAIN_INTEGRITY_V0_2.md`. REHT owns the fresh exact-action authorization that must exist within that chain. Veritas verifies and preserves the resulting evidence; verification cannot create authority or legitimize a bypass after the fact.

### EA-23 Consequence-bearing route binding
Where an action commits value or another material external effect through a selectable execution or settlement route, the authorization MUST bind every route element whose mutation can change that effect. Applicable fields include the exact resource/service, amount or value bound, asset/currency, recipient/payee, destination, network/rail, facilitator/processor, and validity or attempt binding.

A material route mutation after authorization is action drift. The existing permit MUST become non-executable and fresh REHT authorization MUST be obtained before commit. A permit bound to one network, asset, payee, processor or material destination MUST NOT authorize another, even when the business intent or nominal price is unchanged.

Discovery data, explorer observations, wallet capability, signatures, payment-protocol proofs, processor acceptance and settlement evidence MAY be admissible evidence about the proposed or observed route. None of them creates principal authority or substitutes for the current exact-action authorization required by REHT.

This invariant is provider-neutral and rail-neutral. Protocols, wallets, networks, facilitators and payment systems remain execution substrates downstream of authorization.

## Mandatory production subset

The minimum production boundary is EA-01 through EA-16 plus EA-20 through EA-23. EA-17 through EA-19 are mandatory where their corresponding risk surface exists and otherwise remain explicit applicability decisions; they may not be silently omitted.

## Decision semantics

RACS is a deterministic decision contract, not an evaluator or authority source. REHT determines whether execution is cleared. RACS expresses the already-determined outcome using the canonical outcome plane:

- ALLOW
- MODIFY
- DEFER
- DENY
- STEP_UP
- HALT

No RACS outcome grants authority by itself.

## Layer responsibilities

VAIG: observes, evaluates, estimates, scores and produces evidence/signals. No authority.

REHT: applies explicit authority, policy, scope, purpose, state, constraints and admissible evidence at the execution boundary. Sole authorization boundary.

RACS: expresses the deterministic decision contract and owns canonical runtime effect-path/effect-chain conformance semantics. No evaluation, authorization, enforcement, learning or context retrieval.

Gateway / adapter: mechanically enforces a valid permit or refusal. No independent judgment and no bypass route.

Veritas: records and verifies what actually occurred, including unknown, divergent or chainless observed outcomes. It cannot retroactively authorize execution.

## Verification rule

A requirement is not considered implemented because documentation, prompts, agent instructions, architecture diagrams, or policy prose say so. Correctness requires executable contracts, negative tests, CI gates, runtime verification, or formal evidence appropriate to the invariant.

## Source relationship

This specification was developed after reviewing external authority and decision-layer control frameworks whose useful themes include least privilege, multi-hop revalidation, evidence-gated continued authority, authority drift, high-impact gates, explicit human decision rights, sequencing safeguards, fail-safe behavior, formal verification, single-path execution control and verifiable side effects.

REHT deliberately changes the abstraction: the primitive here is not a broad agent authority contract but the concrete authorization of a specific action at the execution boundary, with causal continuity and verified outcome feeding the next authorization state.

Independent convergence was later recorded from Brad Wolfe, with Paul Mathieu, Ishaan Ghosh, and Prashant Rajpal, *Accountability at Machine Speed: Four Layers, Four Signatures* (2026). Its separation of boundary, enforcement machinery, contemporaneous evidence, and accountable principal supports the existing architectural split without becoming a normative dependency. In particular, its emphasis on ephemeral authority and single-use authorization bound to the consequential effect sharpens EA-04/05/07/14/20. See `docs/ACCOUNTABILITY_MACHINE_SPEED_EXTERNAL_VALIDATION_2026.md`.
