# Semantic preservation rebaseline — 2026-08-24

Status: CURRENT REBASELINE
Canonical REHT base: `c9a00ddc331fe24f9889158a202c1dde37925124`
Historical audit: PR #39 / `docs/architecture/semantic-preservation-ledger-final.md`

This document does not rewrite the historical audit. It re-evaluates the blocker families from #39 after the repairs merged in #40, #41 and #42 and after the VAIG REHT-only authority hardening.

Canonical ownership remains:

- Kernel owns operative state.
- REHT is the sole execution-authorization owner.
- Consequence interlocks, containment, resource accounting, continuity and evidence closure are subordinate mechanical/evidence mechanisms and create no authority.
- Veritas verifies/admits execution evidence; it does not authorize.

## Rebased blocker families

| #39 blocker family | Current evidence | Rebased status |
|---|---|---|
| Global/scoped HALT and runtime revocation | #40 adds global/scoped HALT plus authority/principal/actor revocation checked before REHT and immediately before capability consumption | CLOSED |
| Containment loss / capability revocation / restart safety | #40 adds containment interlock, runtime/environment/adapter/credential/path bindings and fail-closed consequence checks | CLOSED for canonical EffectBoundary; deployment-specific adapters remain conditional |
| Physical no-direct-effect path | #40 seals `BoundaryEffect`; production `EffectBoundary` rejects raw callables and requires the governed effect path | CLOSED |
| Resource reservation and non-widening | #40 adds hierarchical budgets, child attenuation, shared ancestor ceilings and action-bound single-use reservation consumption | CLOSED |
| Pre-commit mechanical revalidation | #40 adds subordinate pre-commit probes that may OBSERVE/STEP_UP/BLOCK but cannot ALLOW | CLOSED |
| Success/failure terminal receipt | #40 makes terminal receipts mandatory for REHT non-ALLOW, mechanical block, effect failure and success | CLOSED |
| Active long-running execution currentness | #41 adds active sessions, observations, PAUSE/STOP/REAUTHORIZE/ROLLBACK/HANDOVER/HALT and material-context reauthorization | CLOSED |
| Runtime modification may only narrow | #41 enforces monotonic attenuation of dynamic bounds | CLOSED |
| Failed recovery remains halted | #41 requires fresh REHT ALLOW to resume and keeps failed reauthorization halted | CLOSED |
| Veritas/WORM handoff | #42 requires production evidence closure through Veritas before return | CLOSED |
| Kernel outcome admission | #42 requires Veritas-backed `EXTERNAL_EFFECT_OBSERVED` admission to Kernel | CLOSED |
| Evidence cannot create authority | #42 hard-binds `authority_granted=false`; Kernel evidence admission is non-authoritative | CLOSED |
| Reality/postcondition divergence | #40 supports required postcondition/reality verification and distinguishes committed effect from valid completion | CLOSED where action declares this requirement |
| VAIG AARM independent ALLOW authority | VAIG regression contract asserts AARM ALLOW has `execution_authority=False`, `requires_reht_clearance=True`, `can_execute=False` | CLOSED |
| VAIG `/api/v1/authorize` independent authority | VAIG regression contract requires no clearance/permit and `execution_authority=False`; endpoint ALLOW is compatibility evaluation only | CLOSED |
| VAIG legacy `AuthorityGate` independent authority | VAIG regression contract requires legacy ALLOW to remain evaluation-only and require REHT clearance | CLOSED |

## Still conditional or unverified

These are not open authorization-owner defects:

1. Durable/shared `PermitStore` semantics remain a deployment requirement for restart/multi-worker safety.
2. Credential/workload/provider-specific lanes remain conditional capabilities: when used, their native fail-closed credential, PoP, revocation and audit invariants still apply.
3. Distributed revocation/checkpoint propagation remains deployment-specific even though the canonical authority model is unchanged.
4. Cross-repository reachability must continue to prove that no legacy VAIG/platform/Gateway surface can reach an external effect without the REHT-governed boundary. Current VAIG regression tests prove non-authoritative semantics at its known legacy authority surfaces; they do not by themselves prove universal cross-repo effect reachability.
5. Workflow ISA and Function Fabric retain their own safety invariants when those optional capabilities are used; they are not universal authority/runtime hops.

## Current conclusion

The blocker list in the historical #39 ledger must not be read as current open status.

At REHT base `c9a00ddc331fe24f9889158a202c1dde37925124`, the consequence-runtime families restored by #40-#42 are CLOSED on the canonical EffectBoundary path. The VAIG authority-conflict family is also CLOSED at its current REHT-only regression contract.

The remaining material system-level question is reachability evidence: prove continuously that no alternate legacy or provider path can bypass the governed consequence boundary. Absence of that cross-repo proof is `UNVERIFIED`, not evidence of a known bypass.
