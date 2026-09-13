# Superlog repair adapter

The Factory adopts the Superlog incident-repair pattern as an external repair-agent adapter, not as an authority layer.

Canonical flow:

`alert -> evidence/telemetry -> investigation -> root cause -> patch proposal -> Factory validation/evaluation -> REHT authorization for consequential action -> execution gateway -> Veritas receipt`

The adapter may consume alert and trace references from observability systems, repository/context references, and external investigation output. It normalizes those inputs into a `RepairProposal` owned by the Factory.

The adapter may investigate and propose a patch. It must reject requests to merge, deploy, or mutate production data. External proposals that contain consequential requested actions are classified `REHT_REQUIRED`; the adapter itself never turns that state into an allow decision.

This preserves the architectural distinction between repair capability and execution authority. A repair agent can be correct about root cause and still lack standing, scope, freshness, or authorization to change the running system.
