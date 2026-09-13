# VALO Factory — Operations

## Install (from this repo)

    make install

Copies `bin/*` to `~/.valo/bin/` (or `$VALO_HOME/bin`), symlinks to
`~/.local/bin/`, installs the provider-neutral worker launcher, and verifies
the mode token.

## Credential isolation

Production duty separation remains:

- worker: changes the isolated worktree only; no push, PR creation, QC or merge;
- orchestrator: may commit/push/create the candidate PR only after the current
  `valoctl` write gate;
- QC: reads the exact PR head and emits a head-SHA-bound attestation;
- merge controller: may merge only an A/B candidate with current mode, current
  head, green CI and a valid QC attestation.

The coding worker is launched through `valo-agent-provider`. Provider/model
selection is capability configuration, not authority.

    export VALO_FACTORY_WORKER_PROVIDER=openai_codex
    export VALO_FACTORY_WORKER_TIMEOUT=1800

Supported provider IDs are listed by:

    valo-agent-provider providers

Provider login or entitlement never grants execution authority.

## Modes

NORMAL is the post-hold state and is entered by exiting the current hold:

    valoctl exit --reason "Founder removed ON_HOLD"
    valoctl check

Other explicit modes:

    valoctl enter MAINTENANCE --force --reason "..."
    valoctl enter INCIDENT_HOLD --force --reason "..."
    valoctl enter SHADOW --force --reason "..."

`valoctl enter NORMAL` is not a valid command.

## Shadow inspection

    valo-orchestrator shadow

Shadow is read-only. It does not claim, push, create/close PRs, merge or mutate
GitHub labels.

## NORMAL dispatcher chain

One `valo-orchestrator tick` executes at most one candidate transaction:

    discover unclaimed issue
      -> current mode gate
      -> claim
      -> valo-run isolated worktree at origin/main
      -> provider-neutral coding worker
      -> verify worker did not commit or push
      -> stage + orchestrator commit
      -> current mode gate
      -> push candidate branch
      -> current mode gate
      -> PR with explicit --head/--base
      -> classify
      -> independent valo-qc against exact head/base SHA
      -> append-only durable receipt
      -> A/B: current mode gate -> valo-merge -> require {"merged": true}
         OR C/BLOCKED: NEEDS_HUMAN
      -> local cleanup
      -> claim release only while the remote-write gate remains open

The worker prompt is written outside the worktree and removed after the run.
Placeholder `tick-*.md` or contract-only commits are not valid deliveries.
A successful provider call must leave a real repository change.

Orchestrator run state is persisted in `~/.valo/orchestrator.db`.
Receipts are appended and fsynced at
`~/.valo/receipts/valo_factory_receipts.jsonl`.

Tests:

    python3 tests/test_dispatcher_chain.py

The suite covers provider dispatch, current-base worktrees, explicit PR refs,
worker self-commit/self-push rejection, QC BLOCKED, Class C, merge JSON
verification, durable receipts and cleanup.

## 24/7 operation

Scheduling does not add authority. Do not enable the production timer until one
real end-to-end tick has passed worker -> PR -> QC -> receipt -> merge/NEEDS_HUMAN
without manual repair.

Install units:

    make install-systemd
    sudo systemctl daemon-reload

After the end-to-end gate is green:

    sudo systemctl enable --now valo-factory-tick.timer
    sudo systemctl enable --now valo-factory-health.timer

Production tick runs `valo-orchestrator tick`; health inspection is read-only.
Alert delivery uses `valo-deliver` and remains exception-only.

Class C changes still require the human authority gate. No timer, model,
provider, worker, QC process or merge controller may broaden its own authority.
