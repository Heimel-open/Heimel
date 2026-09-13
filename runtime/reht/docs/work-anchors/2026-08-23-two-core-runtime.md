# Work anchor — two-core runtime consolidation

Date: 2026-08-23
Owner: Njål / active consolidation

Repository: `nsolland/valo-reht`
Canonical base SHA: `5e5bcdfac2a8dc7d3676ca10141ea4c73112d2e6`
Branch: `refactor/two-core-runtime`

Primary objective: reduce the authoritative VALO runtime to exactly two core owners:

1. `valo-kernel` — authoritative operative state and deterministic state admission.
2. `valo-reht` — sole runtime authorization/effect boundary.

Everything else is subordinate and must be either:
- an internal non-authoritative helper inside one of the two cores;
- an optional observer/adapter with no authority effect; or
- retired from the runtime dependency graph.

First owned files:
- `src/valo_reht/contracts.py`
- `src/valo_reht/reht.py`
- `repo-manifest.yaml`
- `AGENTS.md`
- `.github/workflows/ci.yml`
- `README.md`

Immediate dependency to remove: `valo-workflow-isa`. REHT currently imports only `DecisionResult` and `RehtPort`; these are small boundary types and belong locally in REHT if REHT is the sole authorization component.

Kernel remains the only canonical runtime dependency.

VAIG/BARO/semantic/behavioral/model diagnostics are observers only. They may produce evidence but never authority or execution clearance.

RACS/Gateway/Veritas remain useful execution-boundary concepts. They should not require separate authoritative repositories in the final runtime shape; their minimal deterministic contracts/enforcement/evidence functions can live under REHT or at its immediate effect adapter boundary.

## Mandatory completion protocol

All consolidation work stays on `refactor/two-core-runtime`. `main` remains the frozen control baseline.

When the local work is finished and the required local validation is green, the worker MUST complete all of the following before declaring the task done:

1. Commit every intended code/documentation change to `refactor/two-core-runtime`.
2. Push the completed commits to the remote branch.
3. Do not merge the PR.
4. Write the final validation result into the repository, not only into terminal/chat output.
5. Update PR #37 with the same final status so the remote review surface reflects the actual local result.

The repository final record MUST include:
- start SHA and final SHA;
- commits created;
- files changed;
- runtime dependencies removed;
- runtime dependencies retained and why;
- observer/evidence components removed from the authorization path;
- targeted smoke/REHT test counts and runtime;
- full local pytest result if smoke validation is green;
- any material blocker or integrity regression;
- explicit final statement: `AUTHORITATIVE RUNTIME = KERNEL + REHT` or `NOT YET — <blocker>`.

A local green result that has not been committed, pushed and recorded in the repo/PR is NOT considered complete.

No GitHub Actions, external compute, benchmark/stress rerun, or merge is implied by this completion protocol. Expensive validation still requires a separate cost/benefit decision.
