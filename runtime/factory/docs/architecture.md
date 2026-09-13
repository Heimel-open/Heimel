# VALO Factory — Architecture

Control plane for autonomous, governed PR merging. Replaces the legacy
swarm/foreman model with a policy-driven, exception-only pipeline.

## Components (bin/)
- `valoctl` — global mode token (NORMAL / MAINTENANCE / INCIDENT_HOLD / SHADOW).
  Single source of truth for whether write/remote actions are permitted.
- `valo-git` — agent shim: refuses direct repo mutation unless write_allowed
  AND the primary-repo pre-commit guard is satisfied.
- `valo-run` — creates isolated, leased worktrees (never the primary repo).
- `valo-claim` — SQLite-backed claim leases; mirrors to GitHub only under NORMAL.
- `valo-orchestrator` — single state machine. Owns claims + run state.
  `tick` drains under non-NORMAL; `shadow` runs synthetic analysis cycles.
- `valo-qc` — machine-readable QC gates; emits head-SHA-bound attestation.
- `valo-classify` — risk classes A/B/C (canonical machine-readable output).
- `valo-merge` — merge-controller; merges ONLY with valid attestation + green CI.
- `valo-watchdog` — strictly read-only; observes + reports; never remediates.
- `valo-report` — exception-only human panel.

## Enforcement layers (defense in depth)
1. **Server-side (authoritative):** branch protection on both repos requires PR,
   blocks force-push/branch-deletion, requires up-to-date branch, green CI, and a
   valid QC attestation status check bound to exact head-SHA. No admin/app bypass
   except a documented emergency procedure.
2. **Identity separation:** Worker / QC / Merge run as separate GitHub identities
   (separate fine-grained PATs) and, where possible, separate OS users/containers.
   No single process holds all three credentials.
3. **Local shims + hooks (defense in depth, NOT authoritative):** valo-git,
   primary-repo pre-commit guard, valoctl mode-fence. These narrow the blast
   radius but are bypassable if an agent runs raw git/gh — hence layer 1+2.

## State (never versioned)
claims.db, orchestrator.db, runs.db, state.json, active leases, tokens.

See authority-model.md, operations.md, incident-response.md.
Commissioning evidence: ~/.hermes/evidence/commissioning/COMMISSIONING_REPORT.md
