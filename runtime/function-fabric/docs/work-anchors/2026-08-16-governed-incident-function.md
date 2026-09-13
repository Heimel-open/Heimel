# Work anchor — Governed incident function

- Active delivery: compile a generic governed incident-response Function from existing Workflow ISA primitives.
- Repository: `nsolland/valo-function-fabric`
- Canonical base SHA: `6d1cd194a5b1751f92a9cdf416e567ef0e79848f`
- Branch: `feat/governed-incident-function`
- Owner/claim: ChatGPT producer on behalf of Njål; independent verification required.
- Owned files:
  - `docs/work-anchors/2026-08-16-governed-incident-function.md`
  - `src/valo_function_fabric/incident.py`
  - `tests/test_governed_incident_function.py`
- Dependencies:
  - `nsolland/valo-workflow-isa@6e5b3633f17bdb150fb2b6118a44b4186d4926ba` for current primitives.
  - Kernel/BARO/Veritas incident extensions are downstream contracts, not required to compile this graph.
- Boundary: no new ISA primitive and no hidden execution. Remediation must pass PREPARE_ACTION -> REHT-backed WRITE -> execution -> post-state verification.
