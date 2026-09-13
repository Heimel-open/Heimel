# VALO Function Fabric

Turns Workflow ISA into a programming language for real functions.

```text
Goal -> Function Graph -> Function Definitions -> compile -> Workflow Graphs
     -> Governed Workspace Plan -> Kernel projection -> candidate conformance
     -> Workflow ISA Runtime -> Action Contract -> REHT -> RACS -> Gateway
     -> Real World -> Veritas -> BARO -> Kernel World State
```

**A Function is a program.** Versioned, typed, compilable, testable — never an
agent prompt, never a hidden tool call.

## What this layer provides

- **Function Definition** — frozen contract: identity, types, workflow_ref,
  preconditions/postconditions, effects, risk class, autonomy profile,
  authority/evidence/rights/purpose requirements, jurisdiction, reversibility,
  idempotency.
- **Registry** — canonical, versioned, snapshotable. `register/resolve/get/
  list_versions/dependencies/validate/deprecate`. No runtime self-modification.
- **Function Graph** — compose Functions with SEQUENCE/PARALLEL/BRANCH/JOIN/
  LOOP/CALL; compiles to Workflow ISA (no second runtime).
- **Compiler** — resolve pinned versions, type check (no implicit promotion),
  expand, verify effects (golden invariant) and governance monotonicity, then
  emit a valid, deterministic WorkflowGraph with pinned version hashes.
- **Standard library** — the first 20 functions (VERIFY_IDENTITY, VERIFY_
  EVIDENCE, CHECK_ELIGIBILITY, CHECK_AUTHORITY, REQUEST_EVIDENCE, MATCH_/RESERVE_/
  ALLOCATE_RESOURCE, SCHEDULE, PRICE, APPROVE, NOTIFY, INVOICE, PAY, REFUND,
  REGISTER, ONBOARD, OFFBOARD, INSPECT, REMEDIATE).
- **Simulation & Explain** — deterministic, no external writes.
- **Packs** — domain + country extension points that can tighten, never weaken,
  core governance.
- **Programmable substrates** — one canonical external-capability contract can
  project machine-manifest, CLI, MCP and skill descriptors without creating
  alternate authorization paths.
- **Governed Workspace lowering** — binds an immutable registry snapshot,
  Function definition and registered Workflow graph to a Kernel
  `WorkspaceSpec`. Capability targets are explicit, effects are lossless, and
  the plan creates no authority or execution path.

## Governance monotonicity (canonical)

When Functions compose: `risk(parent) >= max(risk(children))`,
`effects(parent) ⊇ union(effects(children))`, and authority/evidence/purpose
requirements never weaken. A parent can tighten; it can never hide child risk.

The same rule now holds at the worker boundary: the Function determines the
program entering a governed space, while Kernel independently determines the
current bounded reality available to it. See
`docs/governed-workspace-lowering.md`.

## Dynamic capability boundary

**Capability may be generated dynamically. Authority may not.**

Agents may synthesize code, compose primitives, derive new procedures, or create
new candidate capabilities at runtime. That generation does not create rights,
authority, scope, credentials, execution paths, or permission to produce an
external effect. Any consequence-bearing operation must still enter the same
canonical Action Contract -> REHT -> RACS -> Gateway path and be authorized
against fresh authoritative state at consequence time.

Generated capability therefore remains subordinate to the governed workspace:
its effect target must be explicit, its execution bounded to the authorized
resource/scope, and its actual effect captured as evidence. Budgets, phase or
mode gates, host/resource pinning, and concurrency limits are useful containment
constraints, but they are constraints rather than authority and cannot replace
REHT. A generated tool may become more capable without becoming more empowered.

This also preserves provenance across dynamic composition: candidate procedure ->
authorized action -> executed effect -> verification evidence. Dynamic generation
must not create an unobserved side channel around `NO_DIRECT_EFFECT_PATH`.

## Programmable business substrates

`valo_function_fabric.substrates` models agent-operable business systems as
external execution substrates. A capability is declared once with its provider
route, operation class, risk, authority scope, external effects and stability.
Function Fabric can then project the same capability to manifest, CLI, MCP and
skill metadata.

Every external capability is REHT-gated. Every mutation requires downstream
effect verification. Financial, production, experimental and R3+ operations
require step-up. Credentials are represented only by secret-location references;
secret values are not part of the capability or generated manifest.

Whop is the first reference substrate because its CLI is explicitly
non-interactive for scripts and AI agents, exposes `whop --llms`, can register
MCP and generate skills, and reaches real business state including catalog,
pricing, money movement, paid acquisition and production deployment. The Whop
binding is metadata only: it does not store `WHOP_API_KEY`, call Whop directly,
or bypass the normal VAIG -> REHT -> execution -> Veritas/BARO chain.

Source of truth for the reference binding:
`https://docs.whop.com/developer/cli`. The transfer capability is marked
EXPERIMENTAL because Whop documents Transfers in its Experimental API reference.

## Dependency anchors

- `nsolland/valo-kernel` @ `773660a`
- `nsolland/valo-workflow-isa` @ `7f92e96`

Recorded in `repo-manifest.yaml`; CI installs both pinned anchors. Workflow ISA
carries the full runtime refinement vocabulary (multi-refinement capability
sets), so Function Fabric lowers types losslessly — no projected refinements,
no governance refinement downgraded to `any`.

## Install & verify

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ../valo-workflow-isa --no-deps
.venv/bin/pip install -e ../valo-kernel --no-deps
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests examples
```

The four demonstrators prove the same core primitives (VERIFY_IDENTITY,
APPROVE, NOTIFY) are reused without a fork across electrician booking, public
application processing, employee onboarding, and payment.
