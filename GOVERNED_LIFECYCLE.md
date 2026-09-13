# Governed Content Lifecycle (Valo-Twin #8)

Valo-Twin is the **operator dashboard and demo UI** for the VALO governance
ecosystem. It is UI/demo only — it does not implement VAIG execution or BARO
scoring (those live in their own repos). This makes Valo-Twin the natural
**"vertical 0"**: the surface where governed flows are observed and operated.

## The lifecycle

The four operator routers already expose the governed content path. This adds a
**type layer** (`src/types/governedLifecycle.ts`) that binds them into one
type-safe lifecycle:

```
DRAFT  ──>  GATED  ──>  QUEUED  ──>  LEARNED  ──>  WATCHLISTED
(draftRouter) (VALO 8-instr gate) (queueRouter) (learnRouter) (watchlistRouter)
```

- **DRAFT** — content generated (`draftRouter`, Gemini + VALO gate)
- **GATED** — the 8-instrument VALO safety gate (`CLEAR→WATCH→FRICTION→COUNCIL→LOCK`),
  producing an `IntegrityResult` + `WORMEntry`
- **QUEUED** — approval queue (`queueRouter`, persistent state)
- **LEARNED** — behavioral analysis (`learnRouter`), tagged with distrust level D0–D4
- **WATCHLISTED** — contact tracking (`watchlistRouter`, 4 flag types)

## Scope boundary (respected)

- This type layer is **types-only**. It describes states + transitions.
- It does **NOT** implement VAIG/BARO logic. The gate remains mandatory in
  `draftRouter`; the routers keep their own behavior.
- `canTransition()` enforces no-skipping at the type level; `isSettled()` marks
  terminal phases. Runtime enforcement stays in the routers.

## Why

Gives the UI one coherent state machine to render the whole governed path, reusing
the existing `IntegrityResult` / `DistrustLevel` / `WORMEntry` types from
`src/types/valo.ts`. No new runtime surface; just shared shape.
