# Wave 1 Hardening Work Anchor — Function Fabric

- Repository: `nsolland/valo-function-fabric`
- Canonical base: `93ea5e5ce40d826d272476505e829929ecca8a14`
- Pinned dependency anchors:
  - `nsolland/valo-kernel`: `edf39cc914843e763c4385c0024d775c7458e1e8`
  - `nsolland/valo-workflow-isa`: `6e5b3633f17bdb150fb2b6118a44b4186d4926ba`
- Branch: `agent/hardening-wave1-function-fabric`
- Owner/claim: AGY producer on behalf of Njål; independent QC performed by Hermes verifier.
- Owned files:
  - `src/valo_function_fabric/compiler/compiler.py`
  - `src/valo_function_fabric/compiler/governance.py`
  - `src/valo_function_fabric/compiler/typecheck.py`
  - `src/valo_function_fabric/contracts/graph.py`
  - `src/valo_function_fabric/workspace.py`
  - `repo-manifest.yaml`
  - `.github/workflows/ci.yml`
  - `pyproject.toml`
  - `examples/demonstrator_4_payment.py`
  - `tests/adversarial/test_adversarial.py`
  - `tests/compiler/test_governance_extended.py`
  - `tests/helpers.py`
  - `tests/test_workspace_plan.py`

Founder decision: Function Fabric is a deterministic programming language layer for Workflow ISA programs. Hardened against substitution, version drift, stale compiled graphs, function widening, parameter injection, intermediate state contamination, and hidden effect paths.
