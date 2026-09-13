# AGENTS.md — valo-workflow-isa

## What this is

`valo-workflow-isa` is the **typed, deterministic workflow instruction set** of
the VALO architecture. Society functions compile down to executable graphs over
this ISA. The runtime owns flow; VALO Kernel owns authoritative world state;
REHT is the sole authorization boundary.

```text
Goal -> Function Graph -> Workflow Graph -> Workflow ISA
     -> Action Contract -> REHT -> RACS -> Gateway -> Real World
     -> Veritas -> BARO -> Kernel Event
```

Canonical rule: the agent may plan and compile. The agent may NOT invent
execution semantics.

## Non-negotiable invariants

- **Flow is explicit.** No implicit control flow. Every edge is explicit;
  SEQ/PARALLEL/BRANCH/JOIN/LOOP/WAIT/TIMEOUT/RETRY/COMPENSATE/CALL/RETURN/HALT.
  No arbitrary agent loop.
- **Five node classes only.** READ, COMPUTE, DECIDE, WAIT, WRITE. Anything else
  is a compile error.
- **No WRITE without an authorization boundary.** WRITE nodes must declare an
  effect and flow through the REHT port. There is no fake REHT inside the
  workflow runtime — ports are the boundary.
- **Probabilistic output can never be a direct WRITE.** Probabilistic nodes
  must be DETERMINISTIC/PROBABILISTIC and must declare
  model/model_version/confidence/source_context. Compiler rejects
  probabilistic -> WRITE edges.
- **Typed composition.** Verified<T>, Admitted<T>, Authorized<T>, Reserved<T>,
  Confirmed<T>. A graph can only consume types it requires; the compiler
  rejects weaker-typed input into stronger requirements.
- **Compile before run.** A graph cannot start until the static compiler proves
  reachability, producers, outputs, boundaries, termination and type
  compatibility. Fail closed.
- **HALT is terminal.** Nothing continues past HALT.
- **Branch paths are explicit.** Alternative (non-selected) branch arms are
  marked `SKIPPED`; a workflow COMPLETES when the selected path reaches a valid
  terminal, never by requiring every alternative terminal to run.
- **Refinements are orthogonal, not a strength ladder.** `Verified`, `Admitted`,
  `Authorized`, `Reserved`, `Confirmed` are separate annotations. There is no
  implicit promotion (`Authorized<T>` is not `Verified<T>`; `Confirmed<T>` is
  not `Authorized<T>`). Strength only rises through explicit nodes.
- **Gateway success is not effect verified.** `execution.success == False`
  never emits EFFECT_VERIFIED and never produces an authoritative Kernel
  effect event.
- **RACS is a deterministic decision contract, not a component.** The binding
  is derived deterministically from the REHT decision (pure, no state, no I/O).
  There is no active component between REHT and execution: REHT is the sole
  authorization boundary; DENY fails closed with zero Gateway executions.
- **No direct storage / no mutable WorldState.** Workflow ISA talks to Kernel
  only through typed Kernel queries via the Kernel port. It never touches
  storage and never holds a mutable WorldState.

## Layout

```
src/valo_workflow_isa/
├── contracts/    # frozen pydantic contracts (node, graph, edges, policies, events)
├── opcodes/      # the 18 primitive workflow opcodes
├── types/        # wrapper type system (Verified<T> ...) + compatibility
├── effects/      # effect type system + write-effect validation
├── graph/        # graph invariants (reachability, cycles, producers)
├── compiler/     # static compiler/validator (fail-closed)
├── runtime/      # durable in-memory reference runtime (instance, engine, context)
├── events/       # workflow event log
├── ports/        # Kernel/REHT/RACS/Gateway/Veritas/BARO/backend interfaces
├── stdlib/       # handlers for the 18 primitive opcodes
tests/
├── unit/ compiler/ runtime/ property/ adversarial/
examples/          # the five demonstrators
```

## Dependency anchor

`valo-kernel` (merged) is the dependency; its contracts are referenced through
the Kernel port. The kernel adapter imports `valo_kernel` lazily. Workflow ISA
never copies kernel state ownership. Anchor SHA in `repo-manifest.yaml`.

## Conventions

- Python `>=3.11`, pydantic `>=2.6`.
- Contracts: frozen `pydantic.BaseModel` with `extra="forbid"`, lifecycle
  validators.
- Determinism: hash inputs are canonical (sorted JSON, `separators=(",",":")`).
- No comments unless they carry intent the code does not.
- Runtime is deterministic: node scheduling order never changes the result of
  independent parallel branches.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
# dependency anchor (local dev):
.venv/bin/pip install -e ../valo-kernel --no-deps
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests examples
.venv/bin/python -m compileall -q src tests examples
```

CI (`.github/workflows/ci.yml`) installs the pinned valo-kernel anchor, then
runs compileall + ruff + pytest on every push/PR.

## Branch discipline

Never work on `main` directly. Create a branch per change, then open a PR.
Keep the working tree clean before starting.
