# VALO Workflow ISA

The **typed, deterministic workflow instruction set** of the VALO architecture.
Society functions compile down to executable graphs over this ISA. The runtime
owns flow; VALO Kernel owns authoritative world state; REHT is the sole
authorization boundary.

```text
Goal -> Function Graph -> Workflow Graph -> Workflow ISA
     -> Action Contract -> REHT -> RACS -> Gateway -> Real World
     -> Veritas -> BARO -> Kernel Event
```

Canonical rule: the agent can plan and compile. The agent cannot invent
execution semantics.

## What this is

- **Five node classes**: `READ`, `COMPUTE`, `DECIDE`, `WAIT`, `WRITE`.
- **Explicit control flow**: `SEQ`, `PARALLEL`, `BRANCH`, `JOIN`, `LOOP`,
  `WAIT`, `TIMEOUT`, `RETRY`, `COMPENSATE`, `CALL`, `RETURN`, `HALT`. No
  implicit control flow, no arbitrary agent loops.
- **Typed composition**: `Verified<T>`, `Admitted<T>`, `Authorized<T>`,
  `Reserved<T>`, `Confirmed<T>`. The compiler rejects weaker-typed input into
  stronger requirements (e.g. `TRANSFER_FUNDS` cannot consume
  `Candidate<Recipient>`).
- **Static compilation before execution**: a graph cannot run until the
  compiler proves reachability, producers, outputs, authorization boundaries,
  termination and type compatibility. Fail closed.
- **Deterministic runtime**: an in-memory reference runtime with a durable
  backend contract (Temporal can back it later). Node scheduling never changes
  the result of independent parallel branches.

## Boundaries

- No WRITE without the REHT port. No fake REHT inside the runtime.
- Probabilistic output can never be a direct WRITE.
- HALT is terminal.
- Workflow ISA never holds a mutable WorldState and never touches storage —
  only typed Kernel queries via the Kernel port.

## Dependency anchor

Depends on `nsolland/valo-kernel` at the pinned merge SHA recorded in
`repo-manifest.yaml`. Kernel contracts are consumed through the Kernel port;
the adapter imports `valo_kernel` lazily.

## Install & verify

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ../valo-kernel --no-deps   # dependency anchor (local)
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests examples
```

The five demonstrators in `examples/` prove resource reservation concurrency,
revoked authority, the probabilistic boundary, external-success-vs-verified-
effect, and retry/idempotency.
