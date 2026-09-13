# Producer Audit: Wave 1 Hardening — valo-function-fabric

## Baseline & Boundaries
- **Target Repository**: `nsolland/valo-function-fabric`
- **Canonical Base Commit**: `93ea5e5ce40d826d272476505e829929ecca8a14`
- **Pinned Dependency Anchors**:
  - `nsolland/valo-kernel@edf39cc914843e763c4385c0024d775c7458e1e8`
  - `nsolland/valo-workflow-isa@6e5b3633f17bdb150fb2b6118a44b4186d4926ba`
- **Branch**: `agent/hardening-wave1-function-fabric`
- **Producer**: AGY Producer on behalf of Njål

---

## Hardening Surface Analysis & Closed Vulnerabilities

### 1. Governance Monotonicity: Capability Matching with Empty Child Scope
- **Vulnerability**: In `_authority_covered()`, when a child authority requirement had an empty scope (`scope=[]`), it bypassed parent capability matching entirely and returned `True` even if the parent declared zero requirements for that capability.
- **Fix**: Required strict matching on `capability` before evaluating scope superset rules. A parent must explicitly declare the capability.

### 2. Multi-Node Leaf Workflow State Isolation (Substitution & Graph Assembly)
- **Vulnerability**: `_rename_node()` only prefixed entry and terminal node inputs/outputs. Internal intermediate nodes retained un-prefixed variable names, causing cross-call variable collision and state contamination when multiple instances of a multi-node leaf function were composed into a graph.
- **Fix**: Prefixed all internal intermediate node inputs and outputs with `f"{prefix}.{ref.name}"`, isolating intra-function state while preserving typed external bindings.

### 3. Strict Parameter & Type Binding Integrity (Function Widening / Parameter Injection)
- **Vulnerability**: `check_call_bindings()` only checked the primary input name, allowing extraneous input/output bindings in `FunctionCall` without validation.
- **Fix**: Validated that all keys in `call.input_bindings` and `call.output_bindings` strictly match the declared input/output parameter names of the target `FunctionDefinition`, failing closed on extraneous bindings.

### 4. Graph Structural Reachability & Terminal States
- **Vulnerability**: `FunctionGraph` allowed empty `terminal_nodes`, and disconnected/unreachable nodes were silently assembled into the workflow.
- **Fix**:
  - Required non-empty `terminal_nodes` in `FunctionGraph` validation.
  - Implemented `check_graph_reachability()` in `compile_function_graph()` ensuring all nodes are reachable from `entry_nodes` and can reach at least one `terminal_node`.

### 5. Stale Compiled Graph & Substitution Protection
- **Enhancement**: Added `verify_provenance()` method on `CompiledFunction` verifying that `function_graph_hash`, `compiled_graph_hash`, and `registry_snapshot_hash` match the respective structures and snapshot seal.

### 6. Workspace Plan Snapshot & Hidden Effect Integrity
- **Enhancement**: Enhanced `_validate_snapshot()` in `workspace.py` to verify that workflow graphs in snapshots carry no undeclared effects compared to the function's declared effect set.

### 7. Modernized Dependencies & Environment
- Aligned `demonstrator_4_payment.py` with `valo-workflow-isa` v1.0.0+ (RACS as deterministic contract).
- Updated `repo-manifest.yaml` and `.github/workflows/ci.yml` with pinned Kernel and Workflow ISA merge SHAs.

---

## Test & Verification Summary
- Full test suite: **120/120 PASS** in ~2.6s.
- `compileall` (src, tests, examples): clean.
- `ruff check .`: clean.
