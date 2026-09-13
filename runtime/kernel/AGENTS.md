# AGENTS.md — valo-kernel

## What this is

`valo-kernel` is the **deterministic admission and state owner** of VALO's
governed operational representation. It is not intelligent. It is consistent.
It owns what VALO is currently entitled to treat as operative, not objective
or universal truth.

```text
candidate information -> VALO admission -> maintained Kernel state
     -> Governed Workspace -> any worker -> conformance -> REHT
     -> Gateway -> Veritas -> BARO -> Kernel Event
```

Canonical principle: the model evaluates, the kernel owns state, REHT decides
whether state may change through external action, Veritas proves what happened,
BARO verifies the result.

## Non-negotiable invariants

- **Kernel owns state.** No agent writes authoritative state directly. All
  state mutation happens through events and deterministic reducers.
- **SOVEREIGN_DOMAIN_CONTINUITY.** Sovereignty means replaceable operational
  dependencies, not absence of dependencies. Loss of a model, cloud, device,
  runtime, sensor or compute provider may degrade capability, but must not make
  identity, authoritative state, rights, relationships, governance, evidence or
  recovery constitutionally unrecoverable. See
  `docs/sovereign_domain_continuity_v1.md`.
- **PRINCIPAL_IS_AUTHORITY_ROOT.** Authority belongs to the logical principal,
  not a device, model, runtime, provider account, enclave, credential or compute
  location. Credentials may rotate, be revoked or be recovered without moving
  root authority to the infrastructure that holds them.
- **CAPABILITY_TO_COMPUTE_NE_AUTHORITY_TO_ACT.** Hardware capability,
  attestation, model availability, routing choice or successful inference can
  establish execution capability only. None creates authority, delegation,
  clearance or standing.
- **PORTABLE_SOURCE_IS_CANONICAL.** Hardware-specialized model deployments are
  disposable implementation artifacts. A provider-neutral model source artifact
  plus semantic contract is the portability anchor; every backend must prove
  semantic equivalence against a reference route before it is admissible.
- **NO_DIRECT_EFFECT_PATH.** Kernel never exposes an execution route. A
  consequence-bearing action leaves Kernel only as one sealed `PASS` execution
  binding for fresh REHT authorization and bounded Gateway enforcement.
- **LEAST_SEMANTIC_PRIVILEGE.** Components receive no more consequence-bearing
  meaning than their role requires. After exact-action conformance, concrete
  action semantics cross the Kernel boundary only inside a cryptographically
  sealed `SealedWorkspaceExecutionBinding` addressed to the REHT execution
  boundary. Clear `WorkspaceExecutionBinding` objects are internal pre-seal
  material and are not a permitted cross-boundary execution artifact.
- **JUST_IN_TIME_SEMANTIC_DISCLOSURE.** The sealed consequence action is opened
  only inside an explicit REHT execution-boundary disclosure context with fresh
  state, authority and evidence bindings. `UNSEAL != EXECUTE`: disclosure
  creates no authority, clearance or effect. Wrong boundary/key, expiry,
  tampering or commitment mismatch fails closed. Boundary private-key custody
  must be enforced by KMS/HSM/TEE or equivalent in production. See
  `docs/jit_semantic_disclosure_v1.md`.
- **Decision-relevant writes are governed.** State, memory, configuration,
  instruction or artifact writes that can alter a future consequence-bearing
  decision must enter through Kernel events or fresh persistent-state admission.
  Agent-local memory and direct authoritative writes are never operative state.
- **NULL_EFFECT_ON_DENY.** `DEFER`, `STEP_UP`, `DENY` and `HALT` create no
  execution binding. Kernel has no mechanism that can turn them into an effect.
- **Kernel owns admission.** Possession is not standing. Candidate material is
  bound to evidence, entities/relationships, provenance, contradictions and
  unresolved references, then evaluated by reproducible VALO policy. External
  assessments are optional provider-neutral inputs and can never create state,
  authority or clearance. See `docs/state_admission_v1.md`.
- **No named external dependency.** Margaret, Elsa, Jasper or any other named
  framework/system may be implemented as an adapter, but none is a required
  Kernel, workspace, conformance or execution dependency. Native VALO paths
  must remain testable with zero external providers.
- **No shadow world models.** A company/organization brain, memory graph, RAG
  store, dashboard or agent memory is a derived read model only. It may project
  or cache Kernel state and explicitly labelled inference, but it cannot own
  authoritative facts, identity, rights, obligations, purpose, authority or
  delegation; mutate WorldState directly; or override current Kernel state.
  Governed use must retain source state root, provenance/evidence references and
  freshness. See `docs/organization_projection_boundary.md`.
- **Persistence creates no standing.** Files, memory entries, configuration,
  instructions, handoffs and cached artifacts that survive a worker/session
  boundary are not operative merely because they persist. Before exposure to a
  governed worker, the exact bytes must correspond to admitted evidence inside
  the current governed projection and be freshly bound to workspace, state root
  and purpose. Worker-produced artifacts must re-enter through evidence
  reception and admission before they can become later persistent input. See
  `docs/persistent_state_admission_boundary_v1.md`.
- **Governing contracts cannot drift.** A contract that governs a work unit must
  be declared explicitly in the workspace. Its exact Kernel-state digest is a
  hidden freshness dependency, the workspace cannot outlive it, and amendment,
  termination or replacement forces `DEFER` before any execution binding can be
  produced. See `docs/governing_contract_drift_v1.md`.
- **Read views are immutable.** `KernelEngine.state()` returns a deep copy; a
  caller can never mutate authoritative state through the public API.
- **Governed workspaces are non-authoritative.** They are immutable,
  purpose-bounded projections with opaque capability leases. They cannot carry
  authority, issue clearance or execute. Only deterministic `PASS` conformance
  may bind one exact candidate action for fresh REHT evaluation.
- **Idempotency is owned by the store.** `idempotency_key` deduplication lives
  in the append-only store, so it survives engine restarts over the same store.
- **Execution identity is mandatory.** Every executable actor needs an explicit
  active, verified `IdentityClaim`. There is no type-based bypass
  (unverified ServiceIdentity is not executable either).
- **Deterministic replay.** The same event stream always produces the same
  state. LLMs are never required for replay. Boundary replay pins governed
  inputs; token-level LLM replay is not attempted.
- **Events are append-only.** History is never rewritten. Errors are corrected
  with CorrectionEvent / SupersessionEvent / RevocationEvent, never DELETE.
- **Evidence is not derived state.** Evidence must flow receive -> VALO state
  admission -> explicit derived-state event -> WorldState. A direct admission
  or confirmation bypass fails closed.
- **Authority is data.** Authority, delegation, rights and obligations are
  explicit first-class records, never role descriptions in a prompt.
- **Delegation never widens.** A delegation can only limit or carry forward
  existing authority, never increase it.
- **Fail closed.** Unknown schema, broken hash, missing tenant, missing identity,
  authority conflict, version conflict and invalid temporal ordering are hard
  failures.
- **Reservations are atomic.** Parallel workflows can never double-book a
  resource. Optimistic concurrency with expected_version; no silent
  last-write-wins.
- **Tenant isolation.** tenant_id is mandatory on every object. Cross-tenant
  is DENY by default; federation is built explicitly later.
- **No /execute.** The kernel produces execution context for REHT. It does not
  authorize and does not execute external actions.
- **Truth is not binary.** Facts carry TruthStatus (CONFIRMED, ASSERTED,
  INFERRED, CONFLICTED, STALE, REVOKED, UNKNOWN). Probabilistic output is never
  written directly as CONFIRMED state.

## Layout

```
src/valo_kernel/
├── contracts/       # canonical world-model objects (frozen pydantic, extra="forbid")
│   ├── common.py         # enums, canonical_digest, utcnow
│   ├── admission.py      # candidate, optional assessment, policy + decision
│   ├── persistent_state.py  # admitted cross-worker persistent input binding
│   ├── semantic_disclosure.py  # sealed consequence action + JIT boundary contracts
│   ├── sovereignty.py    # reconstructible principal domain + disclosure authority
│   ├── model_portability.py  # portable source + hardware/backend equivalence
│   ├── time.py           # explicit time semantics
│   ├── identity.py       # identity claims + verification state
│   ├── entity.py         # canonical entity
│   ├── relationship.py   # typed relationship graph
│   ├── provenance.py     # canonical provenance
│   ├── evidence.py       # evidence object + status lifecycle
│   ├── fact.py           # facts + truth status
│   ├── authority.py      # authority + delegation
│   ├── rights.py         # rights
│   ├── obligations.py    # obligations
│   ├── purpose.py        # purpose (first-class)
│   ├── contract.py       # contract representation (state basis only)
│   ├── resource.py       # resources + reservation
│   ├── constraint.py     # generic constraints
│   ├── workspace.py      # projection, candidate, conformance + binding contracts
│   └── events.py         # canonical event + event types
├── world/
│   ├── state.py          # WorldState model
│   ├── history.py        # state.at(t), replay
│   └── invariants.py     # world invariants
├── kernel/
│   ├── integrity.py      # event hash, chain hash, state root hash, snapshot
│   ├── admission.py      # deterministic VALO-owned admission evaluator
│   ├── persistent_state.py  # seal/verify persistent workspace input
│   ├── semantic_disclosure.py  # encrypt/decrypt exact action at REHT boundary
│   ├── sovereignty.py    # provider-loss + exact disclosure assessment
│   ├── model_portability.py  # deterministic backend admissibility assessment
│   ├── reducers.py       # deterministic Event -> State reducers
│   ├── engine.py         # append, idempotency, concurrency, tenant, fail-closed
│   ├── queries.py        # deterministic query model
│   ├── transitions.py    # transition contract validation
│   ├── execution_context.py  # complete context delivery to REHT
│   ├── workspace.py      # deterministic projection + conformance
│   └── baro.py           # postcondition / divergence checks
├── storage/
│   ├── base.py           # append-only store interface (storage-agnostic)
│   └── memory.py         # in-memory append-only store (first implementation)
├── packs/
│   └── base.py           # world pack registration (domain extensions)
examples/            # demonstrators 1-4
tests/               # unit + negative + property tests
```

## Conventions

- Python `>=3.11`, pydantic `>=2.6`.
- Contracts: frozen `pydantic.BaseModel` with `extra="forbid"`, lifecycle
  validators, and `ConfigDict(extra="forbid", frozen=True)`.
- WorldState and reducers are plain mutable models (working data), never
  exported as contracts.
- `from __future__ import annotations` where union syntax is used.
- No comments unless they carry intent the code does not.
- Determinism: hash inputs are canonical (sorted JSON, `separators=(",",":")`).
- No LLM output may enter CONFIRMED state; it must pass admission/verification.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q                       # unit tests
.venv/bin/python -m pytest --cov=valo_kernel        # coverage report
.venv/bin/python -m compileall -q src tests examples
.venv/bin/python -m ruff check src tests examples
```

All execution, validation, test and experiment runs are **local-only**. Do not use GitHub Actions or any remote CI runner as an execution path. GitHub is source/control-plane only: branches, commits, reviews and PRs. Run commands locally, preserve the resulting evidence locally, and register run status/results through the project’s local run/index process.

## Testing expectations

- Every fail-closed path has a test.
- Negative tests are mandatory: direct state mutation rejected, expired/revoked
  authority, governing-contract drift, delegation expansion, double reservation,
  duplicate payment event, cross-tenant reference, event-chain modification,
  backdated mutation, probabilistic fact treated as confirmed, external success
  without verified effect.
- Replay determinism is proven: same event stream -> identical state hash.
- Non-PASS workspace outcomes are proven to produce no execution binding, and
  decision-relevant memory cannot bypass evidence admission.
- JIT semantic disclosure proves no clear consequence payload crosses in the
  sealed binding, wrong boundary/key and expiry fail closed, tampering is
  detected, and successful unseal has no execution effect.
- Sovereign continuity proves provider loss may degrade capability but cannot
  remove the required reconstruction set or recovery threshold; disclosure is
  exact-destination, exact-projection and fresh-state bound; hardware backend
  acceptance requires semantic-equivalence evidence.
- Tampering is detected: any event-hash-chain or state-root break raises.
- Property tests cover invariants (no delegation widening, no double
  reservation, no tenant crossing, chain integrity).
- The five demonstrators in `examples/` must be runnable and assert their
  contract.

## Branch discipline

Never work on `main` directly. Create a branch per change, e.g. `hermes/`,
`fix/`, `feat/`, then open a PR. Keep the working tree clean before starting.
