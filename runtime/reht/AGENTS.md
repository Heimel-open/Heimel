# AGENTS.md — valo-reht

## What this is

The real REHT, packaged as the sole runtime authorization/effect-boundary core.
Kernel is the only authoritative upstream runtime dependency.

```text
Kernel authoritative execution context
        -> REHT
             fresh identity / authority / scope / purpose / constraints / state
             exact action + consequence binding
             ALLOW | STEP_UP | DENY
             permit / clearance when ALLOW
        -> effect adapter / commit
        -> outcome evidence
        -> Kernel
```

Everything else is subordinate:
- reasoning, planning and simulation remain outside execution governance;
- VAIG/BARO/semantic/behavioral/model diagnostics are observer evidence only;
- RACS is a deterministic decision/binding representation, not an authority owner;
- Gateway is mechanical effect enforcement, not an authority owner;
- Veritas/outcome capture is evidence, not an authority owner;
- external harnesses, providers and packs are optional adapters, never core dependencies.

## Non-negotiable invariants

- **Two authoritative cores only.** Kernel owns operative state. REHT owns runtime authorization. No third component may own authority or operative state.
- **Generic.** No domain names or pack-specific rules in REHT. Exact action policy/constraints arrive as data bound to the consequence proposal.
- **Kernel is the only canonical runtime dependency.** REHT consumes a fresh sealed Kernel execution context. Boundary contracts owned by REHT live in REHT.
- **Governed Workspace is evidence, not authority.** Workspace conformance, Kernel origin proofs and lineage bindings may fail closed when stale, tampered or mismatched, but cannot mint authority.
- **Deterministic authorization semantics.** Same verified context, exact action contract and authorization instant produce the same authorization result.
- **Fail closed at consequence.** Missing identity, authority, freshness, scope, purpose, constraints, valid state or binding cannot produce ALLOW.
- **No governance of thought.** Internal reasoning, exploration, simulation, recommendation and telemetry cannot be blocked merely for their content. Governance starts when a transition can create protected or external consequence.
- **Observer evidence is not authority.** No semantic, behavioral, confidence, model-judge or drift score can itself grant or revoke handlingsrett unless an explicit consequence-bound policy makes that evidence material.
- **Kernel does not authorize; REHT does not own state.**
- **RACS/Gateway/Veritas do not authorize.** Any retained implementations are internal/subordinate effect-boundary functions or external adapters.

## Mandatory local-task completion protocol

This applies to every local coding, test, migration, audit or experiment order unless the order explicitly defines a stricter destination.

A local task is **not finished** when the command stops or the tests turn green. The worker must make the result remotely visible and self-report completion.

When the task is complete:
1. run the agreed cheapest sufficient local validation;
2. commit all intended changes on the assigned work branch;
3. push the completed branch to `origin`;
4. persist the final result in the repository at the destination named by the order (work anchor, evidence file, issue/PR report, or equivalent);
5. update the active PR with the same final status when a PR exists;
6. report start SHA, final SHA, commits, changed files, validation commands/results/runtime, and blockers;
7. finish with exactly one explicit state: `STATUS: FERDIG` or `STATUS: IKKE FERDIG — <concrete blocker>`;
8. never merge unless the order explicitly authorizes merge.

If the task produces no code change, the result must still be persisted in the named repository artifact/issue/PR location and pushed or posted so it is remotely visible.

Do not end a local task with terminal-only output. Do not require a human to physically inspect the machine to discover whether the task finished.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ../valo-kernel --no-deps
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m compileall -q src tests
```
