# VALO Twin

VALO Twin is the operator dashboard and demo UI for VALO governance workflows.

It is a React/TypeScript/Vite application for visualizing draft workflows, approval queues, watchlists, learning signals and governed action outcomes.

## Architectural role

```text
Speider collects external signals
        ↓
BARO interprets context
        ↓
REHT defines admissibility semantics
        ↓
VAIG evaluates and orchestrates governance conditions
        ↓
REHT clears or refuses the proposed action
        ↓
REHT V5 Core enforces bounded execution-state transitions
        ↓
RACS carries envelopes, decisions and receipts
        ↓
VALO Twin displays state and supports human review
```

VALO Twin is an application and operator surface only. It consumes governance outputs through typed interfaces or sample data. It does not own governance semantics, admissibility rules, execution authority or formal verification.

## Authoritative repositories

- [REHT](https://github.com/nsolland/reht) — admissibility semantics and clearance rules
- [VAIG](https://github.com/nsolland/VAIG) — runtime governance evaluation and orchestration
- [REHT V5 Core](https://github.com/nsolland/valo-v5-core) — bounded execution-state enforcement and formal verification
- [RACS](https://github.com/nsolland/Racs) — action envelopes, states and receipt contracts
- [BARO](https://github.com/nsolland/Baro) — contextual observation and interpretation
- [Speider](https://github.com/nsolland/speider) — collect-only field ingestion
- [VALO Platform](https://github.com/nsolland/valo-platform) — integration, services and operational platform

## Upstream dependencies

VALO Twin may consume:

- BARO observations and attention routes
- VAIG evaluation results
- REHT clearance results
- RACS envelopes, decisions and receipts
- platform APIs exposed by `valo-platform`

## Downstream consumers

- human operators
- pilot demonstrations
- approval and review workflows
- customer-facing governance views

## Scope

This repository may contain:

- operator dashboards
- demo UI
- approval queues
- watchlists
- content workflow prototypes
- digital-twin application surfaces
- visual monitoring of governed state and receipts

This repository must not contain:

- canonical VAIG evaluation logic
- REHT admissibility semantics
- BARO scoring pipelines
- RACS protocol definitions
- execution-state enforcement
- independent governance decisions
- formal verification specifications

## Digital Twin Engine

The Digital Twin Engine is documented in [docs/digital-twin-engine.md](docs/digital-twin-engine.md).

The twin may model identity, competence, projects, preferences, writing style, relationships and objectives. It may propose actions and display governance results. It must not clear, authorize or execute actions.

## Demo gate warning

The local `valoGate()` implementation in `api/lib/ai.ts` is a UI/demo gate only.

It is not the canonical VAIG runtime, REHT clearance mechanism or REHT V5 Core. It must not be presented as a production safety or compliance guarantee.

## Tech stack

- React 19
- TypeScript
- Vite
- Tailwind CSS
- Hono
- tRPC
- Drizzle ORM
- MySQL-compatible database
- Gemini API for draft generation

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Required environment variables:

```env
APP_ID=
APP_SECRET=
DATABASE_URL=
GEMINI_API_KEY=
SLACK_SIGNING_SECRET=
```

Optional demo constants:

```env
VALO_ALPHA=
VALO_C0=
```

## Commands

```bash
npm run dev
npm run check
npm run lint
npm run test
npm run build
npm run start
```

## Database

```bash
npm run db:generate
npm run db:migrate
npm run db:push
```

Do not commit real credentials.

## Architecture rule

Adapters and UI may render governance state. They must never own independent governance semantics. Logic belonging to REHT, VAIG, BARO, RACS or REHT V5 Core must remain in the authoritative repository and be consumed through an explicit interface.