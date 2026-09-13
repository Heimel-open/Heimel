# Shared AI Collaboration Context

**Repository:** `Valo-Research-Geoup/valo-v5-core`  
**Purpose:** shared working context for ChatGPT, Claude, Copilot, Kimi and human contributors.

This file is the handoff contract between AI assistants. Read it before changing code.

---

## Current cleanup objective

The repository is being cleaned up without destroying the valid product variants.

The central decision:

```text
Sidecar, MCP and HTTP Proxy are not duplicates.
They are deployment modes around one shared VAIG Core.
```

Do not collapse the product modes into one service. Consolidate the shared governance logic instead.

---

## Anti-context-loss rule

This repository has previously lost work because AI assistants continued after losing context or inferred architecture from partial files.

Therefore:

```text
If context is incomplete, stop changing runtime code.
Read context first. Then document. Then patch narrowly.
```

Never perform broad rewrites from memory.

---

## Scan-is-not-read rule

Scanning is not reading.

The following are not sufficient grounds for code changes:

- repository listing
- filename search
- grep-style keyword hit
- README-only review
- commit message review
- partial file snippet
- inferred architecture from directory names
- prior memory from another assistant session

Before coding, an assistant must read the relevant files end-to-end enough to explain:

1. what the file does,
2. what calls it,
3. what it calls,
4. what behavior must be preserved,
5. what exact line/routine is being changed.

If this cannot be answered, do not code. Write an analysis note instead.

Allowed workflow:

```text
READ -> TRACE -> EXPLAIN -> PLAN -> PATCH -> TEST -> HANDOFF
```

Forbidden workflow:

```text
SCAN -> ASSUME -> CODE
```

---

## Mandatory read order

Before changing architecture, governance logic, naming, UI labels or runtime flow, read in this order:

```text
1. context.md
2. docs/PRODUCT_MODES.md
3. docs/UI_SEMANTICS.md
4. docs/ARCHITECTURE.md
5. docs/analysis/valo_research_group_complete_analysis.md
```

If one of these files is missing, create a finding under `docs/analysis/` instead of guessing.

---

## Product model

VAIG has four product/deployment modes:

1. **VAIG Core**
   - shared governance logic
   - levels, decisions, policy, distrust, WORM, audit receipt, schemas

2. **HTTP Proxy Mode**
   - transparent wrapper in front of any HTTP LLM backend
   - low-friction integration and demo path

3. **Sidecar Mode**
   - stateful enterprise runtime
   - source/session tracking, admin reset, audit tail, deployment config

4. **MCP Mode**
   - exposes VAIG as tools for AI assistants via Model Context Protocol
   - tool interface, not a proxy and not the core

5. **VALO L1 Guardian Mode**
   - optional high-assurance Rust/TLA+ gate
   - mandatory only for high-risk / industrial deployments

See `docs/PRODUCT_MODES.md` for the canonical explanation.

---

## UI semantics

Human-facing safety levels use a VU-meter / traffic-light model.

Canonical UI sequence:

```text
CLEAR -> WATCH -> FRICTION -> COUNCIL -> LOCK
```

Canonical color sequence:

```text
Green -> Blue/Green -> Yellow -> Orange -> Red
```

These are display labels, not replacements for canonical machine/audit codes.

See:

```text
docs/UI_SEMANTICS.md
```

---

## Non-negotiable boundaries

### 1. Do not modify frozen L1 logic casually

Treat the L1 Guardian and formal verification assets as protected.

Do not change:

```text
l1-guardian/src/validation_logic.rs
formal-verification/
```

unless the formal spec, implementation and test vectors are updated together.

### 2. Do not create another policy engine

Before adding new policy logic, check whether it belongs in:

```text
packages/vaig-core/
```

If that package does not exist yet, create it before adding another duplicate implementation.

### 3. Do not hardcode new thresholds inside adapters

Adapters may expose values, receive values and render results. They must not become independent governance engines.

Bad pattern:

```text
adapters/mcp/server.py owns its own L0-L4 thresholds
adapters/http-proxy/gate.py owns its own policy mapping
deployments/sidecar/policy.py owns a separate decision model
```

Good pattern:

```text
adapter -> imports VAIG Core -> renders/forwards result
```

### 4. Do not rename product concepts ad hoc

Use the canonical terms:

| Concept | Canonical examples |
|---|---|
| Distrust level | `L0_TRUSTED`, `L1_MONITOR`, `L2_WARN`, `L3_DEFER`, `L4_HALT` |
| UI label | `CLEAR`, `WATCH`, `FRICTION`, `COUNCIL`, `LOCK` |
| Governance decision | `ALLOW`, `MODIFY`, `DEFER`, `DENY`, `HALT`, `STEP_UP` |
| Transport outcome | `FORWARDED`, `BLOCKED`, `DEFERRED`, `FAILED` |
| L1 outcome | `ALLOW`, `DEGRADED`, `HALT`, `LOGFULLHALT` |

These are related but not the same thing.

---

## Context-loss safety protocol

### Before any non-trivial edit

An assistant must be able to answer these five questions before editing:

1. Which product mode is affected: Core, HTTP Proxy, Sidecar, MCP or L1?
2. Is this adapter-specific behavior or shared governance logic?
3. Which canonical document controls this decision?
4. Which tests protect the behavior?
5. What is the smallest safe change?

If the answer is unclear, create an analysis note instead of editing code.

### Before coding from search results

Search results may identify files, but they do not authorize changes.

Before changing a file found by search, read the full relevant file or the full relevant function/class plus its callers. Then record the intended change in the commit message or handoff note.

### Before broad refactor

Broad refactor requires a written plan under:

```text
docs/analysis/refactor_plan_YYYY-MM-DD.md
```

The plan must include:

- files touched
- behavior preserved
- behavior changed
- migration path
- rollback path
- required tests

### After any meaningful edit

Update or create a handoff note under:

```text
docs/analysis/ai_handoff_YYYY-MM-DD.md
```

The note must state:

- what changed
- why it changed
- what was intentionally not changed
- which assumptions were used
- what the next assistant must read first

---

## Current known architecture drift

The codebase currently contains multiple overlapping implementations of:

- distrust engines
- WORM audit logs
- policy mappings
- naming systems for levels and outcomes
- bridge loading logic

Cleanup should remove duplication at the governance-core level while preserving deployment surfaces.

---

## Preferred target structure

```text
packages/
  vaig-core/
    vaig_core/
      levels.py
      decisions.py
      distrust.py
      policy.py
      worm.py
      receipt.py
      scout.py
      schemas/

  valo-l1-guardian/
    src/
    formal-verification/

  valo-bridge/
    python/
      transport.py
      bridge.py
      factory.py

adapters/
  http-proxy/
  mcp/

deployments/
  sidecar/

docs/
  PRODUCT_MODES.md
  UI_SEMANTICS.md
  ARCHITECTURE.md
  SECURITY_MODEL.md
  AUDIT_RECEIPT.md
```

This is a target structure, not permission to mass-move files without tests.

---

## Safe work order

1. Add documentation and context files.
2. Extract pure constants/enums first.
3. Add tests around current behavior.
4. Extract WORM/audit schema.
5. Refactor MCP to use core.
6. Refactor HTTP Proxy to use core.
7. Refactor Sidecar to use core while preserving stateful source/session behavior.
8. Only then move/rename directories.

---

## Required tests before behavior changes

At minimum:

```text
test_levels_mapping.py
test_policy_engine.py
test_distrust_engine.py
test_worm_chain.py
test_receipt_schema.py
test_proxy_halt.py
test_proxy_defer.py
test_sidecar_reset.py
test_mcp_tools.py
test_l1_bridge_frame.py
```

Cross-mode invariant:

```text
same governance input -> same governance decision
```

This must hold across MCP, HTTP Proxy and Sidecar.

---

## Assistant coordination rules

For ChatGPT, Claude, Copilot or another AI assistant:

1. Read this file first.
2. Follow the mandatory read order before architecture or runtime edits.
3. Check `docs/PRODUCT_MODES.md` before interpreting repo layout.
4. Check `docs/UI_SEMANTICS.md` before changing UI labels, status words or colors.
5. Do not assume duplicate-looking files are useless; first determine whether they are adapter-specific or core duplication.
6. Do not delete or rewrite working variants without leaving a migration note.
7. Prefer small commits with clear intent.
8. Do not silently change governance semantics.
9. When uncertain, add a note under `docs/analysis/` instead of changing runtime code.
10. Do not continue from stale memory; reread context after a long gap.
11. Preserve existing work unless the user explicitly approves replacement.
12. Never mass-format files as part of a logic change.
13. Do not code from scan results. Read the relevant code path first.
14. If only a scan was performed, the only allowed output is analysis or a read plan.

---

## Kimi role boundary

Kimi is allowed as a restricted analysis and coding assistant only.

Allowed:

- read code
- analyze code paths
- identify bugs
- propose small isolated patches
- write tests
- add comments that explain existing code
- produce findings under `docs/analysis/`

Not allowed without explicit human approval:

- rewrite narrative documents
- rewrite product positioning
- rename core concepts
- change governance semantics
- move directories
- mass-format files
- collapse Sidecar, MCP and HTTP Proxy into one service
- edit `docs/PRODUCT_MODES.md` as product authority
- edit `docs/UI_SEMANTICS.md` as UI authority
- edit `l1-guardian/src/validation_logic.rs`
- edit `formal-verification/`

Kimi-specific rule:

```text
Kimi may inspect and patch locally, but must not reorganize the architecture.
```

If Kimi finds an issue, the preferred output is:

```text
docs/analysis/kimi_findings_YYYY-MM-DD.md
```

not a broad rewrite.

---

## Loss-prevention rule

When the assistant is about to overwrite, move, delete, rename or consolidate files, it must first create a loss-prevention note under:

```text
docs/analysis/loss_prevention_YYYY-MM-DD.md
```

The note must list:

- files at risk
- reason for change
- preservation strategy
- rollback strategy

No broad destructive cleanup without this note.

---

## Current ChatGPT handoff note

ChatGPT reviewed the repo layout and corrected the initial assumption that Sidecar, MCP and HTTP Proxy were mere duplicates.

Updated understanding:

- **Sidecar** = stateful enterprise runtime.
- **MCP** = AI-assistant tool interface.
- **HTTP Proxy / Wrapper** = transparent low-friction integration layer.
- **VAIG Core** = shared governance engine that should be extracted.
- **VALO L1 Guardian** = optional high-assurance verified gate, protected from casual edits.
- **UI semantics** = VU-meter and traffic-light labels: CLEAR, WATCH, FRICTION, COUNCIL, LOCK.

Files added by ChatGPT cleanup pass:

```text
docs/PRODUCT_MODES.md
docs/UI_SEMANTICS.md
context.md
```

Recommended next action:

```text
create packages/vaig-core with canonical levels, decisions, UI labels, policy and schema definitions before refactoring adapters
```
