# Semantic preservation ledger

Date: 2026-08-23
Audit branch: `audit/full-semantic-architecture-map`

This ledger is the gate for any further architecture reduction. A component name may disappear only after every semantic responsibility it carried has a proven destination.

| Semantic invariant | Original carrier(s) | Current destination | Status | Blocking two-core-as-complete-runtime claim? |
|---|---|---|---|---|
| Canonical operative state ownership | valo-kernel | valo-kernel | PRESERVED_WIRED | No |
| Sole consequence authorization | REHT | REHT | PRESERVED_WIRED | No |
| Exact action + fresh context binding | REHT + Gateway | REHT + EffectBoundary | PARTIAL/PRESERVED | No for basic commit; exact old equivalence unproven |
| Single-use permit | Gateway | EffectBoundary + required atomic PermitStore | REPLACED_EQUIVALENT for single-use contract | No, assuming production shared/durable store |
| Failed invocation never re-arms permit | Gateway | EffectBoundary | PRESERVED_WIRED | No |
| Local cheap sensor/whisker probes | Kernel uniform_whisker | Code exists only | PRESERVED_ORPHANED | Yes |
| ENFORCE whisker BLOCK/STEP_UP | Kernel uniform_whisker | No active consequence-path wiring found | PRESERVED_ORPHANED | Yes |
| Whisker cannot grant ALLOW/authority | Kernel uniform_whisker | Contract preserved | PRESERVED | No |
| Global HALT | Gateway RuntimeControlPlane / platform containment controller | No EffectBoundary input | MISSING | Yes |
| Scoped HALT | Gateway RuntimeControlPlane | No EffectBoundary input | MISSING | Yes |
| Authority/principal/actor runtime revocation interlock | Gateway RuntimeControlPlane | Fresh REHT state overlaps; no independent runtime control latch | PARTIAL | Yes until equivalence proven |
| Containment breach HALT | platform containment | No active two-core wiring | MISSING | Yes |
| Revoke open permits on containment loss | platform containment controller | No active two-core wiring | MISSING | Yes |
| Invalidate credential leases on containment loss | platform containment controller | No active two-core wiring | MISSING | Yes |
| Block restart-based recovery after containment loss | platform containment controller | No active two-core wiring | MISSING | Yes |
| Human recommissioning before resume | platform containment controller | No active two-core wiring | MISSING | Yes |
| Runtime identity binding | Gateway/platform containment | REHT context + containment path not fully preserved | PARTIAL | Yes |
| Environment/substrate digest binding | Gateway/platform containment + REHT confidential execution | REHT confidential execution only when profile selected | PARTIAL | Yes where containment required |
| Approved egress adapter binding | platform containment/Gateway | No EffectBoundary field | MISSING | Yes |
| Credential lease binding | platform containment/Gateway | No EffectBoundary field | MISSING | Yes |
| Policy path-head binding | platform containment | No EffectBoundary field | MISSING | Yes |
| Deny direct NETWORK egress | platform containment | No active two-core wiring | MISSING | Yes |
| Deny direct TOOL/CONNECTOR/CREDENTIAL path | platform containment + Gateway tool adapter | EffectBoundary accepts arbitrary callable | MISSING | Yes |
| Tool physically callable only from boundary | Gateway FunctionTool/ToolRegistry | No equivalent in EffectBoundary | MISSING | Yes |
| Structural full-chain replay verification | RACS/Gateway boundary replay | action/context hash + PermitStore only | PARTIAL | Yes |
| Atomic resource budget reservation/consume | Gateway ResourceBudgetLedger | REHT only validates declaration | MISSING | Yes for bounded-resource actions |
| Hard parent/child resource budget non-widening | Gateway ResourceBudgetLedger | No demonstrated destination | MISSING | Yes for resource-governed actions |
| Success/failure execution receipt | Gateway | EffectBoundary returns in-memory result only | MISSING | Yes |
| Receipt exact authority/action/clearance/permit/executor binding | Gateway | No mandatory receipt | MISSING | Yes |
| Verified execution handoff | Veritas execution | No mandatory EffectBoundary handoff | MISSING | Yes |
| Tamper rejection before evidence storage | Veritas service | Veritas still exists but not mandatory | PRESERVED_ORPHANED | Yes |
| WORM append-only execution evidence | Veritas WORM | Veritas still exists but not mandatory | PRESERVED_ORPHANED | Yes |
| Outcome observation back into Kernel | Workflow ISA Gateway→Veritas→Kernel | Test harness only; EffectBoundary does not append | MISSING | Yes |
| Verified prior outcome usable by next REHT decision | REHT outcome_feedback | Validator preserved; upstream outcome production not mandatory | PARTIAL | Yes when action requires causal prior outcome |
| Postcondition/reality divergence detection | BARO + Workflow ISA | BARO remains; no mandatory EffectBoundary call | PRESERVED_ORPHANED | Yes for valid-completion claim |
| Required evidence source unhealthy -> HALT | Workflow incident pattern | Pattern remains, but not universal runtime interlock | PARTIAL | Depends on workflow |
| Probabilistic output cannot WRITE directly | Workflow ISA compiler | Workflow compiler remains | PRESERVED where Workflow ISA used | No for REHT core; yes for workflows bypassing compiler |
| WRITE requires authority policy | Workflow ISA compiler | Workflow compiler remains | PRESERVED where used | No for REHT core |
| Irreversible WRITE requires idempotency | Workflow ISA compiler | Workflow compiler remains | PRESERVED where used | No for REHT core |
| Uncertain irreversible effect cannot blindly retry | Workflow ISA runtime | Workflow runtime remains | PRESERVED where used | No for REHT core; required by orchestrators |
| HALT node has no forward successor | Workflow ISA compiler/runtime | Workflow runtime remains | PRESERVED where used | No |
| Compensation semantics | Workflow ISA runtime | Workflow runtime remains | PRESERVED where used | No |
| Function composition cannot lower risk | Function Fabric | Function Fabric compiler | PRESERVED | No |
| Composite cannot hide child effects | Function Fabric | Function Fabric compiler | PRESERVED | No |
| Composite cannot widen autonomy | Function Fabric | Function Fabric compiler | PRESERVED | No |
| Composite cannot drop child authority/evidence/rights/purpose requirements | Function Fabric | Function Fabric compiler | PRESERVED | No |
| External gate evidence cannot mint authority | AAS + REHT | AAS adapters + REHT checks | PRESERVED_WIRED when selected | No |
| Independent human approver authority proof | AAS + REHT | AAS + REHT | PRESERVED_WIRED when selected | No |
| Trusted signing-key/current-revocation validation for gate evidence | AAS bridge | AAS bridge | PRESERVED when used | No |
| Persistent memory/config must originate from admitted evidence | Kernel persistent_state | Kernel | PRESERVED | No |
| Persistent state cannot self-propagate or grant authority | Kernel | Kernel | PRESERVED | No |
| Provider evidence cannot directly create operational state | Kernel admission | Kernel | PRESERVED | No |
| Rail projections cannot widen principal authority | Kernel authority_projection | Kernel | PRESERVED | No |
| Represented principal != authority holder kept distinct | Kernel authority_projection_v2 | Kernel | PRESERVED | No |
| Signed revocation epoch propagation/checkpoint | Kernel execution_authority_assurance | Kernel | PRESERVED | No, but must remain part of distributed deployments |
| Boundary response floor NONE/MODIFY/DEFER/STEP_UP/DENY/HALT | RACS | REHT now only ALLOW/STEP_UP/DENY; no full response mapping | PARTIAL/MISSING | Yes |
| Cross-artifact evaluation→determination→clearance digest continuity | RACS | No proven equivalent | MISSING/PARTIAL | Yes |
| Boundary binding cannot be dropped/injected | RACS boundary validation | No proven equivalent | MISSING | Yes |
| Active execution session currentness | RACS continuity | No two-core session object/loop | MISSING | Yes for long-running/embodied actions |
| Runtime observation sources incl. SENSOR/WATCHER | RACS continuity | No active two-core continuity loop | MISSING | Yes |
| PAUSE/STOP/REAUTHORIZE/ROLLBACK/HANDOVER/HALT | RACS continuity | No active two-core mapping | MISSING | Yes |
| Runtime bound modification only narrows | RACS continuity verification | No equivalent | MISSING | Yes where dynamic bounds exist |
| Failed recovery remains HALTED | RACS continuity | No equivalent | MISSING | Yes where recovery exists |
| Diagnostic/model evidence fail-closed on self-judging/low confidence | VAIG guard | VAIG | PRESERVED as evidence layer | No, unless VAIG evidence consumed |
| Continuity materiality assessment cannot authorize | VAIG continuity assessment | VAIG | PRESERVED | No |
| BARO observation cannot authorize | BARO | BARO | PRESERVED | No |
| Non-execution DEFER/STEP_UP receipt cannot be reinterpreted as execution | RACS normative receipt | RACS | PRESERVED component, wiring not universal | No |

## Gate conclusion

The following statement is currently supported:

`AUTHORITATIVE OWNERSHIP = KERNEL + REHT`

The following statement is **not** currently supported:

`COMPLETE EXECUTION RUNTIME = KERNEL + REHT + EffectBoundary`

Reason: the latter currently omits or leaves orphaned multiple independently implemented safety semantics: whisker interrupt wiring, runtime HALT/revocation, containment/egress, physical non-bypass, resource budgets, durable receipts/WORM, Kernel outcome admission, postcondition verification and active-session continuity/recovery.

No further deletion/reduction should occur until every `MISSING`, `PARTIAL`, and `PRESERVED_ORPHANED` row that blocks the claim has a proven destination and regression test.
