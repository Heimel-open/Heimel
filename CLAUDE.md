# CLAUDE.md — Valo-Twin

## What this project is

VALO Twin is the **operator dashboard and demo UI** for the VALO AI governance ecosystem. It is a full-stack React web application for monitoring VALO signals, managing content approval workflows, and visualizing VALO safety gate decisions.

Primary use case: LinkedIn AI agent integration (VALO Twin v2.0) with content drafting, approval queues, and contact watchlists.

**Scope boundaries:** This repo is UI/demo only. Do not add BARO scoring, VAIG execution logic, or VAP protocol implementation here — those belong in separate repositories.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Vite 7.2.4 |
| Styling | Tailwind CSS 3.4.19 + shadcn/ui (40+ components) |
| Backend | Hono + tRPC 11.8.1 |
| Database | MySQL via Drizzle ORM 0.45.1 |
| AI | Google Gemini 2.0 Flash API |
| Server state | TanStack React Query 5.90.16 |
| Forms | React Hook Form 7.70.0 + Zod 4.3.5 |
| Charts | Recharts 2.15.4 |
| Runtime | Node 20 |

---

## Directory structure

```
api/                        # Backend (Hono + tRPC)
├── boot.ts                 # Server entry point + port binding
├── router.ts               # Main tRPC router registration
├── draftRouter.ts          # Content generation via Gemini + VALO gate
├── learnRouter.ts          # Behavioral analysis
├── queueRouter.ts          # Approval queue management
├── watchlistRouter.ts      # Contact watchlist endpoints
├── analyticsRouter.ts      # Analytics aggregation
├── slack.ts                # Slack integration (/valo slash command)
├── middleware.ts            # Auth and logging middleware
├── lib/                    # Server-side utilities
└── queries/                # Database query builders
src/                        # React frontend
├── pages/
│   ├── Home.tsx
│   ├── Dashboard.tsx       # Stats and activity overview
│   ├── DraftPage.tsx       # Draft generator (reply/DM/post/redteam)
│   ├── QueuePage.tsx       # Approval queue with persistent state
│   ├── LearnPage.tsx       # Learning and analysis interface
│   └── WatchlistPage.tsx   # Contact tracking with 4 flag types
├── components/ui/           # shadcn/ui component library
├── hooks/                   # Custom React hooks
├── providers/               # React Query and theme providers
├── types/valo.ts            # VALO-specific TypeScript types
├── lib/                     # Client-side utilities
├── valo_monitor/            # VALO state monitoring/visualization
└── App.tsx
db/
├── schema.ts               # Drizzle ORM table definitions
└── migrations/             # Auto-generated migrations (not committed)
contracts/                  # Blockchain contracts (if applicable)
```

---

## Development commands

```bash
npm run dev          # Start Vite dev server + Hono backend (HMR enabled)
npm run build        # Vite build + esbuild API bundle → dist/
npm run start        # Run production build
npm run lint         # ESLint
npm run format       # Prettier auto-format
npm run check        # TypeScript type check
npm run test         # Vitest unit tests

# Database management
npm run db:generate  # Generate Drizzle migrations from schema
npm run db:migrate   # Apply pending migrations (interactive TUI)
npm run db:push      # Push schema directly to DB (dev only, skips migrations)
```

---

## Environment setup

Copy `.env.example` → `.env` and set:

```
GEMINI_API_KEY=...      # Required for draft generation
DATABASE_URL=...        # MySQL connection string (PlanetScale, Railway, or local)
```

---

## Key files

| File | Purpose |
|------|---------|
| `api/boot.ts` | Hono server initialization |
| `api/draftRouter.ts` | Content generation + VALO safety gate integration |
| `db/schema.ts` | Database table definitions (drafts, queue, watchlist) |
| `drizzle.config.ts` | ORM connection and migration configuration |
| `context.md` | Deployment checklist and setup guide |
| `info.md` | Component inventory |
| `PROJECT_CONTEXT.md` | Project scope and boundaries |
| `knowledge-base.md` | Domain knowledge reference |

---

## Architecture patterns

- **API:** tRPC for type-safe RPC; Hono for lightweight HTTP routing
- **Forms:** Zod schemas validate at runtime; React Hook Form manages form state
- **State:** React Query for server state; local `useState` for UI state only
- **Styling:** Tailwind CSS with HSL CSS variables for theming; dark mode via `[class]` strategy
- **Database:** Migrations are generated but can be pushed directly in dev (`db:push`)

---

## VALO gate integration

The `/draft` endpoint passes generated content through an 8-instrument VALO safety gate. The UI displays a VU-meter showing the gate decision:

```
CLEAR → WATCH → FRICTION → COUNCIL → LOCK
```

Do not bypass or mock the gate in production code paths.

---

## Deployment

- **Target:** Vercel (edge function support)
- **Build output:** `dist/` for frontend; backend bundled as ESM for Node.js runtime
- **Database:** MySQL-compatible (PlanetScale, Railway, or local MySQL)
- **Migrations:** Not tracked in git; run `db:migrate` after each deployment

---

## Important constraints for AI assistants

- **Type safety:** Full TypeScript throughout; do not introduce `any` without justification
- **No VAIG logic here:** Keep VAIG execution, BARO scoring, and VAP protocol in their own repos
- **VALO gate is mandatory:** The draft workflow gate is not optional — never remove or stub it in production paths
- **Database schema changes** require generating and applying migrations (`db:generate` then `db:migrate`)
- **Slack integration:** The `/valo` slash command and approve/reject buttons are in `api/slack.ts` — keep Slack tokens in environment variables only
