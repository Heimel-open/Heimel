# VALO Factory — Incident Response

## INCIDENT_HOLD
Triggered by: human command, watchdog detection of mode-tamper, GitHub API
unreachable, SQLite corruption, or any fail-closed event.
Effect: no new write runs; queued drained; active runs stopped at safe
checkpoint; highest alert to human. Factory cannot leave INCIDENT_HOLD without
explicit human `valoctl enter` with --force.

## Emergency merge procedure (exception only)
Documented, requires TWO humans (break-glass):
1. Human A issues `valoctl enter MAINTENANCE --force --reason "EMERGENCY"`.
2. Human B performs the merge via GitHub UI with the emergency admin override
   (ruleset `bypass_actors` allows a named emergency team, audited).
3. Post-incident: restore branch protection, file incident report.

## Forensic evidence
Preserve dirty state; never checkout/reset/restore/clean/commit/push during an
incident. Copy evidence outside the repo (~/.hermes/evidence/) with SHA-256.

## Watchdog
Strictly read-only. Observes and reports. Never remediates. If it detects a
fault, it emits NEEDS_HUMAN — it does NOT repair.
