# Semantic architecture audit — completion

Status: COMPLETE
Date: 2026-08-23
Repository anchor: `nsolland/valo-reht`
Canonical base SHA: `5ecf09f2ef94c83a04b10a7ef4bcf3becc92a32d`
Branch: `audit/full-semantic-architecture-map`
PR: #39

## Final conclusion

The consolidation discovered the right authority ownership but collapsed the runtime picture too far.

The correct statement is:

`KERNEL owns canonical operative state.`

`REHT alone owns execution authorization.`

Everything else must either:
- provide evidence/state to those owners,
- restrict/interrupt an already-governed path,
- mechanically enforce an exact REHT-authorized effect,
- verify/record what actually happened, or
- compile/orchestrate work without acquiring authority.

The incorrect statement is:

`Kernel + REHT + the current small EffectBoundary already constitute the complete execution runtime.`

They do not.

## Reconstructed architecture by function

### 1. State plane — Kernel

Kernel owns:
- canonical entities, identities, facts, evidence, authority, delegation, rights, obligations, purpose, contracts, constraints/resources and execution state;
- append-only deterministic mutation/replay/invariants;
- state/evidence admission;
- governed workspace projection and conformance;
- semantic identity/meaning continuity;
- persistent-state admission;
- authority projection and distributed revocation assurance;
- emergency mandate semantics;
- exact execution context for REHT.

Kernel does not execute external effects and does not issue execution clearance.

### 2. Authorization plane — REHT

REHT owns exactly one decision at the consequence boundary:

`May this exact actor perform this exact consequential transition, against this current state, purpose, authority and constraints, now?`

REHT owns clearance/permit semantics. STEP_UP and DENY create no executable permit.

No VAIG, BARO, RACS, Gateway, substrate, attestation provider, credential broker or model may independently create execution authority.

### 3. Restriction / interrupt plane — never ALLOW

These mechanisms may only narrow, interrupt or require reauthorization:
- Kernel governed whiskers;
- Gateway runtime control plane;
- platform containment controller;
- RACS active-session continuity;
- emergency/global/scoped HALT;
- revocation and restart-block state.

Critical rule:

`A component that can STOP does not thereby own ALLOW.`

The current simplified path lost or orphaned most of these interlocks.

### 4. Mechanical consequence substrate — replaceable, non-authoritative

The portfolio already contains the required abstraction in `valo-platform/execution_substrate`.

Its intended role is:

`REHT-cleared exact action -> prepare -> precommit revalidation -> controlled execute -> evidence/receipt -> revoke/terminate`

Required properties already represented there include:
- exact authorization-proof verification;
- replay protection;
- default-deny egress;
- exact payload/action/target/path binding;
- capability-bound credentials;
- workload identity;
- bounded non-renewable credential leases;
- proof of possession;
- revocation;
- audit availability fail-closed;
- resource constraints;
- deterministic teardown;
- provider-neutral adapters;
- normalized evidence and receipts.

This substrate must never decide legitimacy, purpose, authority or acceptable consequence. Those remain REHT inputs/decisions.

The new REHT `EffectBoundary` correctly proves several commit mechanics but duplicates only a strict subset of this substrate. It should not be treated as proof that the richer substrate semantics became unnecessary.

### 5. Physical non-bypass / containment

A valid architecture must make the governed path the only usable effect path, not merely the path agents are expected to choose.

Existing implementations provide:
- boundary-only tool invocation;
- direct network/tool/connector/credential deny;
- exact approved egress adapter;
- containment/runtime/environment/path-head binding;
- global/scoped HALT;
- permit and credential revocation;
- restart recovery block;
- human recommission.

Current generic callable EffectBoundary does not prove this invariant.

### 6. Continuity plane

Long-running or embodied action is not one static authorization event.

Existing RACS continuity semantics provide:
- runtime SENSOR/WATCHER observations;
- currentness checks;
- PAUSE/STOP/REAUTHORIZE/ROLLBACK/HANDOVER/HALT;
- narrowing-only bound modification;
- failed recovery remains halted.

These are not authority ownership. They are continuous enforcement of whether an earlier authorization is still usable.

### 7. Evidence / reality loop

The valid completion path is not `effect returned without exception`.

The reconstructed chain is:

`REHT authorization -> mechanical effect -> execution receipt -> Veritas verification/WORM -> Kernel observed outcome -> BARO/reality/postcondition verification -> next REHT context`

This is how the system prevents "green while dead": a successful tool call does not prove the intended world-state transition occurred.

Current EffectBoundary stops before this chain becomes mandatory.

### 8. Compile/orchestration plane

Workflow ISA and Function Fabric remain required where their semantics apply:
- probabilistic result cannot directly become WRITE;
- irreversible/retry/idempotency/reconcile semantics;
- HALT and COMPENSATE control flow;
- compositions cannot lower risk, widen autonomy, hide effects or discard child authority/evidence/rights/purpose requirements.

They do not own runtime authorization.

### 9. Evaluation plane — VAIG

The current/correct VAIG architecture is:

`measure / evaluate / abstain / recommend / restrict -> REHT`

Confirmed correct modules include:
- evaluation report: `execution_authority=False`, `requires_reht_clearance=True`;
- normative governance: only NO_OVERRIDE/DEFER/STEP_UP and never ALLOW/MODIFY;
- security evidence pipeline: evidence only;
- AAEC trajectory evaluator: recommendation only;
- VACS execution adapter: READY requires verified REHT GovernanceClearance.

But legacy authority code still coexists:

1. `vaig/aarm.py` declares AARM owner of authoritative ALLOW/MODIFY/DEFER/DENY/STEP_UP/HALT semantics.
2. `vaig/api.py` exposes `/api/v1/authorize` directly from AARM without REHT clearance.
3. `src/authority_gate.py` owns its own delegation store and independently returns execution ALLOW.

These are not naming nits. They are competing authority implementations and must not remain on any canonical production execution path.

Local `ROI`, `SpendGate` and `ModelRouter` also use ALLOW vocabulary. Their implementations are optimization/resource/routing controls, not execution authority. Their contract must remain explicitly subordinate so the vocabulary cannot be confused with clearance.

### 10. Observation plane — BARO

BARO is correctly evidence-only.

Confirmed:
- `RealityPackage` actively rejects authority/decision/admission/clearance/permit semantics in observation keys;
- detection sensors state GREEN != ALLOW and RED != DENY;
- evidence loop correlates REHT authorization and Veritas observations but does not authorize/enforce/execute;
- observability convergence routes attention only;
- no BARO execution-authority source path was found in authority/authorize searches.

BARO's defect is not role confusion. It is that post-effect BARO/reality verification is not mandatory on the current effect path.

## Blocking findings

The audit identifies these blocker families before the consolidation may be called semantically complete:

1. Governed Kernel whiskers exist but are orphaned from consequence execution.
2. Global/scoped runtime HALT and revocation interlocks are not consumed by the current EffectBoundary.
3. Containment/default-deny egress and restart/recommission semantics are not on the current path.
4. Physical `NO_DIRECT_EFFECT_PATH` is not proved by an arbitrary callable effect boundary.
5. Atomic resource budget reservation/consumption is not part of the current path.
6. The richer provider-neutral execution substrate exists but is not the canonical REHT effect mechanism.
7. Canonical execution receipts, Veritas admission/WORM, Kernel outcome admission and BARO poststate are not mandatory after effect.
8. RACS active-session continuity/recovery is not integrated with the simplified path.
9. Full cross-artifact replay/binding equivalence from the prior RACS/Gateway path has not been proven.
10. VAIG AARM still claims authoritative execution verdict ownership.
11. VAIG `/api/v1/authorize` exposes a direct AARM authorization surface without REHT clearance.
12. VAIG legacy `AuthorityGate` independently owns delegation state and execution ALLOW.

## Non-blocking preserved support

The following are correctly subordinate and should remain so:
- AAS external attestation/trust;
- HAP authority evidence/trust bridge;
- Kernel semantic/confidential/persistent workspace controls;
- distributed authority/revocation assurance;
- VAIG security/normative/evaluation reports;
- BARO observation/evidence;
- Workflow ISA compile/runtime safety;
- Function Fabric monotonic composition;
- model routing/value/ROI/efficiency/reward research where kept out of authority.

## Architectural target fixed by the audit

The audit does not prescribe more named layers. It fixes responsibilities:

`Kernel state`
`-> evidence/evaluation inputs`
`-> REHT sole authorization`
`-> restrictive interrupts/currentness checks`
`-> one non-authoritative mechanical execution substrate`
`-> verified immutable execution evidence`
`-> Kernel observed outcome + BARO reality/poststate`
`-> next fresh REHT decision`

Anything may be packaged together operationally if and only if these semantic boundaries remain explicit and regression-tested.

## Audit gate

Source coverage: COMPLETE for execution-governance relevance.
Semantic mapping: COMPLETE.
Production repair: NOT performed in this audit PR.

No further simplification/deletion is allowed from the consolidation premise until every blocking invariant in `semantic-preservation-ledger-final.md` has a proven destination and tests.
