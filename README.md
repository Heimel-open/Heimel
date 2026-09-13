# VALO Kernel — Governed Operational Reality

The deterministic admission and state owner of the operational reality VALO
is entitled to use.

```text
        Information available to the enterprise
                         |
                admission candidate
                         v
          VALO deterministic state admission
                         |
               maintained Kernel state
                         |
                Governed Workspace
                         |
               any worker / model
                         |
             deterministic conformance
                         |
              fresh Kernel context -> REHT
                         |
                 RACS -> Gateway
                         |
                    REAL WORLD
                         |
                Veritas -> BARO
                         |
                    Kernel Event
```

The Kernel authoritatively answers a narrower and more defensible question:
"what is VALO currently entitled to treat as operative?" It does not claim
objective or universal truth. It owns the evidence-backed, policy-governed
representation used for work and execution.

## Scope

Kernel owns: state-admission decisions, maintained standing, identity, entity,
state, relationship, time, event, history, evidence, resource, right,
obligation, authority, delegation, purpose, contract, constraint, state
transition and provenance.

Kernel does not own: LLM reasoning, agent planning, workflow orchestration,
AI policy interpretation, external execution, UI, ERP/CRM/fagsystem.

## Principles

- **Event-sourced**: all state mutation happens through append-only canonical
  events and deterministic reducers. `Previous State + Event -> New State`.
  Replay never needs an LLM.
- **Possession is not admission**: information does not become operative merely
  because the enterprise has it. Candidate material must pass VALO-owned,
  deterministic state admission. Provenance, entity/relationship bindings,
  contradictions and unresolved references remain explicit. See
  `docs/state_admission_v1.md`.
- **Evidence is not derived state**: receive evidence -> decide admission ->
  create an explicit derived-state event. A document never sets a fact,
  relationship, identity or authority directly.
- **External systems are adapters, never dependencies**: provider-neutral
  assessments may be used when tenant policy explicitly trusts them. They can
  narrow, hold, reject or quarantine; they cannot create state, authority or
  clearance. Native VALO admission works with zero external providers.
- **No shadow world models**: company/organization brains, memory graphs, RAG
  stores, dashboards and agent memory are derived read models. They may project
  or cache Kernel state and explicitly labelled inference, but never own
  authoritative facts or authority, mutate WorldState directly, or win a
  conflict with current Kernel state. See
  `docs/organization_projection_boundary.md`.
- **Personal context is stratified**: explicit principal-controlled knowledge
  stores and inferred personal-model substrates are separate, hot-swappable
  context sources. Explicit storage does not manufacture standing; inferred
  understanding does not create consent, delegation or mandate. Both feed a
  bounded workspace projection and must use normal State Admission for
  persistent operative state. See `docs/personal_context_substrates_v1.md`.
- **Govern the space**: a worker receives a purpose- and capability-bounded,
  immutable projection of already admitted Kernel state. Coordination channels,
  delegation, communication paths and inter-agent relationships are part of
  the governed workspace boundary: workers may not create or use emergent
  alternatives that bypass workspace constraints or `NO_DIRECT_EFFECT_PATH`.
  The workspace cannot upgrade information or confer standing. Candidate output
  is checked against that exact workspace before fresh execution authorization.
  See `docs/governed_workspace_v1.md`.
- **Authority is data**: authority, delegation, rights and obligations are
  explicit records. Delegation can never widen authority.
- **Truth is not binary**: facts carry `CONFIRMED | ASSERTED | INFERRED |
  CONFLICTED | STALE | REVOKED | UNKNOWN`. Probabilistic output is never
  CONFIRMED.
- **Fail closed** on unknown schema, broken hashes, missing tenant/identity,
  authority or version conflict, invalid temporal ordering.
- **Optimistic concurrency**: mutations require `expected_version`; no silent
  last-write-wins. Reservations are atomic.
- **Tenant isolation**: `tenant_id` on every object; cross-tenant is DENY by
  default.
- **No `/execute`**: the kernel produces a complete execution context for REHT.
  It can cryptographically seal the context to prove Kernel origin and
  integrity, but the seal grants no authority. REHT still authorizes; Kernel
  does not execute external actions. See `docs/execution_context_origin_v1.md`.

## Install

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

## Structure

See `AGENTS.md` for the layout and conventions. Canonical world-model objects
live in `src/valo_kernel/contracts/`, the deterministic kernel in
`src/valo_kernel/kernel/`, and the working `WorldState` in
`src/valo_kernel/world/`.

The five demonstrators in `examples/` prove reservation concurrency, authority
revocation, conflicted reality, external effect mismatch and governed-space
conformance end-to-end.
