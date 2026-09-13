# Workspace temporal execution lineage work anchor

- Repository: `nsolland/valo-kernel`
- Canonical base: `328bfef1454ff055a6392497ce6e7d84c09f4b1c`
- Branch: `agent/workspace-temporal-execution-lineage`
- Delivery: retain tenant, expiry, projection position and conformance time through the exact WorkspaceExecutionBinding consumed by REHT
- Owned files: workspace contract/binder, execution-context checks, focused tests and architecture table
- Non-goals: authorization, execution, worker behavior or program compilation

Invariant: a conformed action cannot cross tenant, outlive its workspace, predate its governed projection, or lose temporal lineage before fresh authorization.
