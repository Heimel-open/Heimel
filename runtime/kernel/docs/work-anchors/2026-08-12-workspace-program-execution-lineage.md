# Workspace program execution lineage work anchor

- Repository: `nsolland/valo-kernel`
- Canonical base: `de11d3ee64e298b014f74498fe3ea16f5d1badbd`
- Branch: `agent/workspace-program-execution-lineage`
- Delivery: carry the WorkspaceSpec program reference and digest into the exact WorkspaceExecutionBinding consumed by REHT
- Owned files: workspace contract/binder, focused test and architecture table
- Non-goals: authorization, execution, worker behavior or program compilation

Invariant: execution lineage must not lose the compiled-program binding established before the worker ran.