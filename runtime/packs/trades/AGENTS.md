# AGENTS.md — valo-trades-pack

## What this is

`valo-trades-pack` is the **first vertical proof** of the VALO architecture.
It runs one complete, realistic business workflow end-to-end over the generic
core:

```text
VALO Kernel -> Workflow ISA -> Function Fabric -> Trades Pack
```

The goal is not a tradesman ERP. The goal is to prove the generic core can
drive one complete workflow: customer request -> qualification -> quote ->
booking -> qualified electrician -> work -> evidence -> invoice -> payment ->
verified completion.

## Non-negotiable invariants

- **Only the pack is electrician-specific.** Kernel, Workflow ISA, VERIFY_
  IDENTITY etc. are exactly the same components used by public sector. If a
  fix requires editing core, refactor — never copy.
- **Reuse core Functions.** The pack must use the exact same core versions of
  VERIFY_IDENTITY, VERIFY_EVIDENCE, REQUEST_EVIDENCE, CHECK_AUTHORITY,
  MATCH_RESOURCE, RESERVE_RESOURCE, SCHEDULE, PRICE, APPROVE, NOTIFY, INVOICE.
  Copying them fails the architecture review.
- **State transitions only through Functions/Workflow ISA.** No direct status
  write; no agent judgment substitutes for credential/evidence enforcement.
- **The compiled graph IS the execution path.** The same EV_CHARGER_JOB
  FunctionGraph that compiles runs through the Workflow ISA Runtime against
  Kernel-owned state and the real REHT/RACS/Gateway/Veritas/BARO ports. No
  local authorization boundary, no parallel state machine, no separate shadow
  implementation.
- **Kernel owns business truth.** Workers' credentials are authorities in
  Kernel state; work order transitions are append-only Kernel events. REHT
  authorizes against the fresh execution context the Kernel produces.
- **Completion requires verified evidence.** `WorkOrder != COMPLETED` from a
  worker pressing a button. Completion = evidence verified + requirements
  satisfied + authorized transition.
- **Payment requires verified external effect.** HTTP 200 from a payment
  provider is not a paid WorkOrder; the observed account state must show the
  payment.
- **REHT revalidates at every write boundary.** Credential expiry between
  booking and dispatch is detected (DEFER and re-match).
- **Shadow mode never writes.** The golden path can be simulated with proposed
  actions, required authority, missing evidence, expected effects and an
  automation percentage — no real-world writes.
- **No domain leakage.** Trades types never appear in valo-kernel or
  valo-workflow-isa; Function Fabric changes only for genuinely general
  Function semantics.

## Dependency anchors

Pinned merge SHAs in `repo-manifest.yaml`:
- `nsolland/valo-kernel` @ `108f770` (frozen v1.0.0)
- `nsolland/valo-workflow-isa` @ `2ccb25f` (frozen v1.0.0)
- `nsolland/valo-function-fabric` @ `b2f058d` (frozen v1.0.0)
- `nsolland/valo-reht` @ `c86a965` (v1.1 candidate — the real REHT, sole
  authorization boundary; the pack injects it, it owns no authorization logic)

No dependency on open branches.

## Layout

```
src/valo_trades_pack/
├── domain.py      # trades domain types (strings/contracts over FF types)
├── catalog.py     # ServiceDefinition + EV_CHARGER_INSTALLATION
├── pricebook.py   # deterministic Price Book
├── credentials.py # credential requirements + trade credential check
├── workorder.py   # WorkOrder state machine (transitions via Functions)
├── functions.py   # pack-specific Functions (CLASSIFY_TRADE_SERVICE, ...)
├── golden.py      # EV_CHARGER_JOB FunctionGraph + compile
├── shadow.py      # shadow/simulation mode + economics
├── exceptions.py  # structured exception model + owner-attention
├── trace.py       # end-to-end execution trace + replay
├── viewmodel.py   # minimal Operator view model (BusinessSummary, ...)
examples/          # golden path + 7 negative demonstrators
tests/             # 25+ scenarios, property, governance, architecture
```

## Conventions

- Python `>=3.11`. FF contracts are frozen pydantic, `extra="forbid"`.
- WorkOrder transitions are events through Functions/Workflow ISA.
- Deterministic Price Book: LLM may interpret scope; it never decides the final
  price.
- Numbers in economics/shadow reports are computed from the scenario, never
  hardcoded.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ../valo-kernel --no-deps
.venv/bin/pip install -e ../valo-workflow-isa --no-deps
.venv/bin/pip install -e ../valo-function-fabric --no-deps
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests examples
.venv/bin/python -m compileall -q src tests examples
```

CI fetches the three pinned anchors and runs compileall + ruff + pytest
(demonstrators run as tests) on every push/PR.

## Branch discipline

Never work on `main` directly. Create a branch per change, then open a PR.
Keep the working tree clean before starting.
