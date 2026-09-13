# Production Acceleration Plan

This document defines how VALO Twin and future VALO modules should be built faster without losing architectural control.

The goal is speed through repeatable structure, not speed through chaos.

## Principle

```text
Prototype fast.
Keep the core clean.
Make every module follow the same contract.
```

Development tools may change.

The platform contract should not.

## Golden path

Build one complete flow first:

```text
Import
  |
  v
Twin Profile
  |
  v
Find Skills
  |
  v
Evidence
  |
  v
Suggestion
  |
  v
Approval Queue
  |
  v
Governance Review
  |
  v
Receipt
```

Do not build broad modules until this works end to end.

## Standard module template

Every module should follow the same structure:

```text
modules/<module-name>/
  README.md
  schema.ts
  api.ts
  service.ts
  worker.ts
  policy.ts
  receipt.ts
  sample-data.ts
  tests/
  ui/
    index.tsx
    components/
```

Each module must define:

- purpose
- inputs
- outputs
- permissions
- evidence requirements
- governance policy
- receipt format
- failure modes
- UI surfaces
- sample data
- tests

## Module contract

Each module should expose a clear contract:

```ts
export interface ValoModule {
  id: string
  name: string
  version: string
  inputs: ModuleInput[]
  outputs: ModuleOutput[]
  permissions: PermissionScope[]
  actions: ModuleAction[]
  evidence: EvidenceRequirement[]
  governancePolicy: GovernancePolicy
  receiptSchema: ReceiptSchema
}
```

This makes modules replaceable and testable.

## Recommended monorepo structure

```text
apps/
  web/
  api/

packages/
  ui/
  core/
  auth/
  database/
  connectors/
  twin-engine/
  skill-engine/
  governance/
  receipts/
  search/
  telemetry/

modules/
  find-skills/
  content-engine/
  scout/
  roi-scout/
  fordelspilot/
  baro-lite/
  approval-queue/
  data-vault/
```

## Fastest build stack

For MVP speed:

- Lovable for UI prototype and layout.
- GitHub as source of truth.
- Cursor, Claude Code, Codex or similar tools for implementation.
- Supabase for quick auth, Postgres, storage and realtime.
- n8n for temporary workflows before hardcoding.
- Docker later when the MVP stabilizes.

Do not let Lovable, Replit or any tool own the architecture.

They are build accelerators, not the platform.

## UI acceleration

Build a shared UI kit early.

Required components:

- Twin Card
- Skill Card
- Evidence Card
- Action Card
- Approval Queue Item
- Receipt Card
- Connector Card
- Risk Badge
- Trust Score
- Timeline
- Activity Feed
- Search Command Palette
- Empty State
- Module Shell

Use the same UI components across every module.

## Demo data first

Every module should ship with realistic demo data.

This allows:

- faster UI testing
- better investor demos
- earlier sales conversations
- development without full integrations
- regression testing

A module without demo data is not demo-ready.

## Agent work pattern

Do not ask coding agents to build whole apps.

Give them small tasks:

- create schema
- create API route
- create React component
- create seed data
- create test
- create receipt schema
- create policy file
- refactor one module

Small tasks reduce hallucination and architectural drift.

## Build sequence

### Phase 1: Shell

- app layout
- navigation
- module shell
- demo data
- shared cards

### Phase 2: Core data model

- twin_profiles
- source_documents
- skills
- skill_evidence
- content_suggestions
- approval_queue
- governance_receipts
- consent_scopes

### Phase 3: Golden path

- import material
- build twin profile
- extract skills
- link evidence
- generate suggestion
- approve/reject
- create receipt

### Phase 4: Connectors

- manual import
- GitHub summary
- Markdown files
- PDF/text upload
- Google Drive later
- LinkedIn later

### Phase 5: Governance hardening

- policy files
- evidence requirements
- risk flags
- receipt hashing
- audit log

## What to avoid

Do not start with:

- full enterprise architecture
- every integration
- autonomous execution
- full marketplace
- complex graph UI
- real-time everything
- advanced permissions before a working demo

## Definition of done for a module

A module is done when it has:

- schema
- API
- UI
- sample data
- governance policy
- receipt schema
- tests
- documentation
- demo path

## First module to finish

Finish `find-skills` first.

Reason:

It proves the core VALO distinction:

```text
claimed skill
inferred skill
evidenced skill
admissible public claim
```

This is useful, understandable and directly connected to Twin, Content, Approval and Governance.

## Product acceleration sentence

VALO should move fast by standardizing how modules are built, not by improvising each product separately.
