# Final semantic preservation ledger

Status: COMPLETE
Date: 2026-08-23
Audit branch: `audit/full-semantic-architecture-map`

This is the final gate for the current consolidation audit. `PRESERVED` means the semantic invariant still exists. `WIRED` means it is demonstrated on the canonical consequence path. `ORPHANED` means implementation exists but is not on that path. `CONFLICT` means a second component currently claims or implements semantics that must belong elsewhere.

| Invariant | Canonical owner / required carrier | Current state | Final status | Blocks complete-runtime claim |
|---|---|---|---|---|
| Canonical operative state | Kernel | Kernel deterministic append/replay/invariants | PRESERVED_WIRED | No |
| Execution authorization | REHT | `RealReht.authorize` | PRESERVED_WIRED | No |
| Fresh exact execution context | Kernel -> REHT | Kernel context + REHT | PRESERVED_WIRED | No |
| Exact action snapshot at commit | Effect boundary | REHT `EffectBoundary` | PRESERVED_WIRED | No |
| Single-use permit consumption | Mechanical boundary | EffectBoundary PermitStore | PRESERVED_WIRED, deployment-dependent durability | No if durable/atomic |
| Failed effect never re-arms permit | Mechanical boundary | EffectBoundary | PRESERVED_WIRED | No |
| Local cheap governed whisker probes | Kernel uniform whiskers | Code exists, no production consequence wiring | PRESERVED_ORPHANED | Yes |
| Whisker ENFORCE BLOCK/STEP_UP | Kernel/mechanical boundary | No active wiring | PRESERVED_ORPHANED | Yes |
| Whisker can never ALLOW/create authority | Kernel contract | Explicitly enforced | PRESERVED | No |
| BARO detection sensors remain advisory | BARO | GREEN != ALLOW, RED != DENY | PRESERVED | No |
| Global runtime HALT | Runtime control/containment | Gateway/platform implementation not wired to EffectBoundary | MISSING_ON_CANONICAL_PATH | Yes |
| Scoped runtime HALT | Runtime control plane | Gateway implementation orphaned | MISSING_ON_CANONICAL_PATH | Yes |
| Runtime actor/principal/authority revocation latch | Runtime control plane | Fresh REHT state overlaps but no independent latch equivalence | PARTIAL | Yes |
| Containment breach atomically stops domain | Containment controller | Implementation exists, not wired | PRESERVED_ORPHANED | Yes |
| Revoke open permits on containment loss | Containment | Implementation exists, not wired | PRESERVED_ORPHANED | Yes |
| Invalidate credential leases on containment loss | Containment | Implementation exists, not wired | PRESERVED_ORPHANED | Yes |
| Restart cannot recover pre-breach capability | Containment | restart token/epoch mechanism exists, not wired | PRESERVED_ORPHANED | Yes |
| Human recommission before resume | Containment | implementation exists, not wired | PRESERVED_ORPHANED | Yes |
| Default-deny direct network/tool/connector/credential egress | Containment/substrate | Rich implementation exists outside current EffectBoundary | PRESERVED_ORPHANED | Yes |
| Approved exact egress adapter/path | Containment/substrate | not represented by generic EffectBoundary callable | MISSING_ON_CANONICAL_PATH | Yes |
| Physical no-direct-effect-path | Gateway/tool boundary/substrate | generic callable EffectBoundary cannot prove it | MISSING | Yes |
| Execution substrate identity/environment binding | Platform substrate + containment | rich implementation exists; optional REHT confidential binding only | PARTIAL | Yes where required |
| Exact payload hash at provider boundary | Platform substrate | QM/Cube substrate supports | PRESERVED_ORPHANED | Yes |
| Authorization proof replay protection | Platform substrate | durable/in-memory implementations exist | PRESERVED_ORPHANED | Yes |
| Commit-time substrate policy revalidation | Platform substrate | `precommit_check` exists | PRESERVED_ORPHANED | Yes |
| Default-deny L7 egress | Platform substrate | Cube/QM policy compiler/adapters | PRESERVED_ORPHANED | Yes |
| Deterministic teardown | Platform substrate | Cube/QM adapters | PRESERVED_ORPHANED | Yes |
| Capability-bound one-shot credentials | Platform substrate | runtime capability + strict adapters | PRESERVED_ORPHANED | Yes when credentials used |
| Human approval replay prevention | Governed runtime capability service | durable SQLite store available, production durability check explicit | PRESERVED_ORPHANED | Yes when human approval used |
| Credential scope cannot broaden | Credential PDP | deterministic exact/narrower checks | PRESERVED_ORPHANED | Yes when credentials used |
| Credential lease non-renewable/bounded use | Credential lease registry | explicit state machine | PRESERVED_ORPHANED | Yes when credentials used |
| Sender-constrained PoP | Credential proxy/boundary | DPoP-compatible verification + replay store | PRESERVED_ORPHANED | Yes for proxy credential lane |
| Workload identity binding | Credential PDP | SPIFFE/SVID-style verifier | PRESERVED_ORPHANED | Yes when credential issuance depends on workload |
| Credential revocation registry fail-closed | Credential subsystem | separate registry | PRESERVED_ORPHANED | Yes |
| Credential audit outage blocks issuance/use | Credential subsystem | separate audit/persistence probes | PRESERVED_ORPHANED | Yes |
| Provider revocation honestly reports residual validity | Credential provider/revocation | explicit UNKNOWN/RESIDUAL/CONFIRMED | PRESERVED | No, but required if subsystem used |
| No open-forwarding proxy | Credential proxy | exact target/method/PoP/header/redirect constraints | PRESERVED_ORPHANED | Yes for proxy lane |
| Resource budget atomic reservation/consume | Gateway ResourceBudgetLedger | REHT validates declaration only | MISSING_ON_CANONICAL_PATH | Yes for bounded-resource actions |
| Parent/child resource limits never widen | Resource ledger | implementation exists outside simplified path | PRESERVED_ORPHANED | Yes |
| Full-chain structural replay before effect | RACS/Gateway/platform substrate | partial action/context/permit checks in EffectBoundary | PARTIAL | Yes |
| Evaluation -> determination -> clearance digest continuity | RACS | no proven replacement equivalence | PARTIAL/MISSING | Yes |
| Boundary bindings cannot be dropped/injected | RACS | no proven complete replacement | PARTIAL/MISSING | Yes |
| Active long-running execution currentness | RACS continuity | not wired into simplified EffectBoundary | MISSING_ON_CANONICAL_PATH | Yes for long-running/embodied actions |
| SENSOR/WATCHER runtime observations | RACS continuity | continuity implementation exists, not wired | PRESERVED_ORPHANED | Yes for active sessions |
| PAUSE/STOP/REAUTHORIZE/ROLLBACK/HANDOVER/HALT continuity actions | RACS continuity | not wired | PRESERVED_ORPHANED | Yes for active sessions |
| Runtime modification may only narrow bounds | RACS continuity | implementation exists, not wired | PRESERVED_ORPHANED | Yes |
| Failed recovery remains halted | RACS continuity | implementation exists, not wired | PRESERVED_ORPHANED | Yes |
| Success/failure execution receipt | Gateway/platform substrate | current EffectBoundary returns result but no mandatory canonical receipt | MISSING | Yes |
| Receipt binds action/authority/clearance/permit/runtime | Gateway/platform substrate | rich receipt/evidence models exist outside simplified path | PRESERVED_ORPHANED | Yes |
| Verified execution handoff | Veritas | verifier exists, no mandatory EffectBoundary handoff | PRESERVED_ORPHANED | Yes |
| Tampered execution evidence rejected before admission | Veritas | preserved | PRESERVED_ORPHANED | Yes |
| Append-only/WORM execution evidence | Veritas | preserved | PRESERVED_ORPHANED | Yes |
| Observed post-effect state admitted to Kernel | Workflow/Veritas/Kernel | not mandatory after current EffectBoundary | MISSING | Yes |
| Verified prior outcome available to next REHT decision | REHT outcome feedback | validator exists; upstream evidence production not mandatory | PARTIAL | Yes when causal prior outcome required |
| Reality/postcondition divergence detection | BARO/Kernel | implementations exist, not mandatory after effect | PRESERVED_ORPHANED | Yes for valid-completion claim |
| BARO RealityPackage cannot contain authority semantics | BARO | construction-time forbidden-key guard | PRESERVED | No |
| BARO evidence loop does not authorize/enforce/execute | BARO | explicit contract | PRESERVED | No |
| Probabilistic output cannot directly WRITE | Workflow ISA | compiler remains | PRESERVED_WHERE_USED | No for core; yes if workflow bypassed |
| Irreversible WRITE requires safe retry/idempotency semantics | Workflow ISA | compiler/runtime remain | PRESERVED_WHERE_USED | No for core; yes for orchestrated write flows |
| HALT has no forward successor | Workflow ISA | preserved | PRESERVED | No |
| Compensation/reconcile semantics | Workflow ISA | preserved | PRESERVED | No |
| Composite function cannot lower risk/widen autonomy | Function Fabric | preserved | PRESERVED | No |
| Composite cannot hide effects/requirements | Function Fabric | preserved | PRESERVED | No |
| External attestation cannot mint authority | AAS/REHT | explicit | PRESERVED | No |
| Approver evidence proves actual approval authority | AAS/REHT | preserved | PRESERVED_WIRED when selected | No |
| Persistent state requires admitted evidence | Kernel | preserved | PRESERVED | No |
| Persistent state cannot self-propagate or grant authority | Kernel | preserved | PRESERVED | No |
| Rail projection cannot widen principal authority | Kernel | preserved | PRESERVED | No |
| Represented principal distinct from authority holder | Kernel projection v2 | preserved | PRESERVED | No |
| Signed revocation epoch/checkpoint for distributed execution | Kernel assurance | preserved | PRESERVED, deployment-specific wiring | No for local core; required distributed |
| Emergency path cannot be triggered by ordinary DENY | Kernel emergency governance | preserved | PRESERVED | No |
| Emergency response bounded by pre-authorized mandate | Kernel emergency governance | preserved | PRESERVED | No |
| Semantic workspace prevents identity/meaning/provenance escape | Kernel | preserved | PRESERVED | No |
| Confidential substrate attestation cannot create authority | Kernel/REHT | preserved | PRESERVED | No |
| HAP receipt becomes evidence only, never clearance/execution | Platform HAP bridge/trust | preserved | PRESERVED | No |
| VAIG evaluation report has `execution_authority=False` | VAIG | preserved | PRESERVED | No |
| VAIG normative gate can only NO_OVERRIDE/DEFER/STEP_UP | VAIG | preserved | PRESERVED | No |
| VAIG security pipeline emits evidence only | VAIG | preserved | PRESERVED | No |
| VAIG AAEC evaluator cannot issue clearance/permit/effect | VAIG | preserved | PRESERVED | No |
| VACS READY requires verified REHT clearance | VAIG/VACS | preserved in execution adapter | PRESERVED / DESIRED | No |
| AARM claims authoritative ALLOW/MODIFY/... | VAIG legacy | still present | AUTHORITY_CONFLICT | Yes |
| VAIG `/api/v1/authorize` returns AARM decision without REHT clearance | VAIG legacy API | still present | DIRECT_AUTHORITY_BYPASS_CONFLICT | Yes |
| VAIG `src/authority_gate.py` independently owns delegation/check/ALLOW | VAIG legacy | still present | AUTHORITY_AND_STATE_OWNERSHIP_CONFLICT | Yes |
| ROI local ALLOW vocabulary cannot become execution authority | VAIG legacy support | no external effect; semantic naming collision | REQUIRES_BOUNDARY_CLARITY | No if evaluation-only |
| Spend local ALLOW vocabulary cannot become execution authority | VAIG legacy support | resource policy/accounting | REQUIRES_BOUNDARY_CLARITY | No if subordinate |
| ModelRouter local ALLOW vocabulary cannot become execution authority | VAIG legacy support | routing only | REQUIRES_BOUNDARY_CLARITY | No if subordinate |

## Final gate

Supported:

`AUTHORITATIVE OWNERSHIP = KERNEL STATE + REHT EXECUTION AUTHORIZATION`

Not supported:

`CURRENT CANONICAL RUNTIME ALREADY PRESERVES ALL EXECUTION-GOVERNANCE SEMANTICS`

The complete-runtime claim remains blocked by two classes of defects:

1. Missing/orphaned consequence mechanics: whisker interrupts, runtime HALT/revocation, containment/default-deny egress, physical non-bypass, resource consumption, rich execution substrate, receipts/WORM, Kernel outcome admission, BARO poststate and RACS active-session continuity.
2. Conflicting authority ownership in VAIG legacy surfaces: AARM, `/api/v1/authorize`, and `src/authority_gate.py`.

No further deletion or architectural simplification is admissible until the blocking rows have a proven canonical destination and regression tests.
