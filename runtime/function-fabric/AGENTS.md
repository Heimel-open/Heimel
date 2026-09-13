# AGENTS.md — valo-function-fabric

## What this is

`valo-function-fabric` turns Workflow ISA into a programming language for real
functions. A **Function is a program**: a versioned, type-safe, compilable,
testable program built from Workflow ISA. It is not an agent prompt, not a tool
call, not a Python function with hidden execution.

```text
Goal -> Function Graph -> Function Definitions -> compile -> Workflow Graphs
     -> Workflow ISA Runtime -> Action Contract -> REHT -> RACS -> Gateway
     -> Real World -> Veritas -> BARO -> Kernel World State
```

Agents may later select and compose Functions. Function Fabric defines what the
functions actually mean.

## Non-negotiable invariants

- **Functions are programs.** Versioned, typed, compiled. No hidden execution.
- **No direct execution.** Function Fabric never executes `/execute`; execution
  goes through the Workflow ISA runtime. WRITE flows Workflow ISA -> REHT.
- **Governance monotonicity (canonical).** When Functions compose: risk(parent)
  >= max(risk(children)); effects(parent) ⊇ union(effects(children));
  authority/evidence/purpose requirements never weaken. Parent may tighten,
  never hide child risk.
- **Golden invariant.** No Function can cause an effect absent from its declared
  effect set. No composition can reduce child governance requirements.
- **No implicit type promotion.** asserted != verified, inferred != confirmed,
  received != admitted, approved != authorized, sent != delivered,
  executed != effect_verified. Strength only rises through explicit
  strengthening Functions.
- **Lossless lowering.** Every governance refinement lowers losslessly into the
  Workflow ISA contract (capability-set, all refinements carried). Never a
  single projected refinement, never `any` for a governance refinement. Only
  opaque domain constructors (no governance refinement) lower to `any`.
- **No self-modification.** Registry mutation is a separate governed
  development/change-management path; runtime/agents never register or mutate
  Functions mid-execution.
- **Version pinning.** Compilation pins every Function version; registry
  snapshots are immutable; later registry changes never affect compiled
  execution.
- **Business truth stays in Kernel.** Function runtime state (node completed/
  waiting/failed) is not World State. No business truth in the Function Fabric
  database.
- **Workspace plans are non-authoritative.** Function Fabric may lower pinned
  Function governance into Kernel `WorkspaceSpec`, but never project state,
  grant authority, issue clearance or execute. Capability targets must be
  explicit and the per-capability effect union must equal the declared
  Function effect set.

## Dependency anchors

Depends on `nsolland/valo-kernel` and `nsolland/valo-workflow-isa` at the
pinned merge SHAs in `repo-manifest.yaml`. Do NOT copy Kernel or Workflow ISA
contracts into this repo. If an interface is missing, open a minimal contract
PR in the owner repo — never a local variant. Compile output must be valid
under the Workflow ISA validator.

## Layout

```
src/valo_function_fabric/
├── contracts/    # function.py, graph.py, registry.py, pack.py (frozen, extra="forbid")
├── types/        # refs.py, strength.py (Raw..VerifiedEffect)
├── registry/     # store.py, snapshot.py, dependency.py, upgrade.py
├── compiler/     # compiler.py, resolver.py, typecheck.py, effects.py, governance.py
├── simulation/   # simulator.py, explain.py
├── stdlib/       # identity/evidence/authority/resource/communication/finance/lifecycle/control
├── packs/        # base.py (pack format + country-pack extension point)
├── workspace.py  # pinned Function -> non-authoritative Kernel WorkspaceSpec
examples/          # 4 demonstrators
tests/             # contracts/compiler/composition/governance/property/adversarial/demonstrators
```

## Conventions

- Python `>=3.11`, pydantic `>=2.6`. Contracts frozen with `extra="forbid"`.
- Determinism: hashes are canonical (sorted JSON, `separators=(",",":")`).
- Function identity is machine-readable (`valo.finance.pay@1.0.0`), never a
  display name.
- Pure vs effectful functions stay sharply separated; business state is never
  Function Fabric state.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ../valo-workflow-isa --no-deps
.venv/bin/pip install -e ../valo-kernel --no-deps
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests examples
.venv/bin/python -m compileall -q src tests examples
```

CI fetches both pinned anchors and runs compileall + ruff + pytest (including
demonstrators as tests) on every push/PR.

## Branch discipline

Never work on `main` directly. Create a branch per change, then open a PR.
Keep the working tree clean before starting.
