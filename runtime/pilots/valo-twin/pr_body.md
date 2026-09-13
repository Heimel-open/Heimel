This is a simulated public demonstration — no production execution occurs.

## Summary
Builds a public `/demo` route on Valo-Twin that renders a deterministic, media-ready simulation of the VALO live governance pipeline.

### What this delivers
- **Three deterministic scenarios** (A: valid merge, B: technical-allowed/business-denied, C: clearance invalidation)
- **Vertical slice built first:** Scenario B (authority mismatch → REHT DENY → Core blocks commit → RACS receipt) demonstrates VALO's core differentiation: technical eligibility ≠ business legitimacy
- **Visible "SIMULATED SYSTEM DEMO" disclosure** at all times
- **Deterministic event-stream replay engine** with pause, replay, reset, speed controls
- **Evidence drawer** with formatted JSON + plain-language explanations
- **RACS receipt + hash-chain view**
- **Fullscreen 16:9 media mode** for screen recording / television capture
- **Offline-safe** — no DB, no model, no backend at runtime; fixtures only

### Scenarios implemented
| ID | Title | Final state |
|---|---|---|
| `valid-consequential-merge` | Valid consequential merge | `EXECUTED — SIMULATED` |
| `business-authority-mismatch` | Technical launch allowed, business action denied | `COMMIT BLOCKED — REHT DENY` |
| `stale-clearance` | Clearance invalidated by state change | `CLEARANCE INVALIDATED — COMMIT BLOCKED` |

### Architecture boundaries respected
- No VAIG, REHT, Core, or RACS governance semantics implemented or redefined
- Canonical outputs rendered from deterministic local fixtures only
- No production data, no write-capable connectors
- The `/demo` route works without any external API access

### Tech stack
- React 19 + TypeScript + Vite + Tailwind + shadcn/Radix + React Router + Vitest
- All existing patterns and components reused from Valo-Twin

### Verification
All checks pass:
- `npm run check` (tsc) ✅
- `npm run lint` ✅
- `npm run build` ✅
- `npm test` (vitest: 19 tests, 3 files) ✅

### Deployment
Preview deployment URL will be available via Vercel preview. Do not promote to production domain without explicit approval.

### Completion receipt
- Repository: nsolland/Valo-Twin
- Branch: demo/live-system-simulation-2026-07-21
- Commit SHA: 51e66ac
- Tests: 19 passed (tsc/lint/build/vitest)

Do not merge without Njål's approval.