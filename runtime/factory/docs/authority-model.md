# VALO Factory — Authority Model

## Single human authority
Njål (`nsolland`) is the SOLE human authority for the control plane. There is
no collaborator, no extra GitHub identity, and no bot standing in as a fake
independent reviewer. GitHub does not allow a PR author to approve their own PR;
requiring a human review would therefore deadlock the repo. Authority is instead
granted by an EXPLICIT, manual workflow run — not by a code-review stand-in.

## Control-plane credential separation (person vs agent channel)
GitHub distinguishes capabilities by permission scope:
- Creating branches / opening & updating PRs  -> `Pull requests: write`
- Merging (PR merge API)                        -> `Contents: write`
- Running workflow_dispatch (the human authority check)
                                                    -> `Actions: write`

The agent credential holds ONLY `Pull requests: write` (+ `Contents: write` for
branch pushes). It does NOT hold `Actions: write`, so it CANNOT start the
`VALO Human Authority / control-plane` workflow. That workflow can only be run
by Njål through the GitHub UI (`workflow_dispatch`), with `github.actor ==
"nsolland"`. This is the server-side boundary that prevents merge before Njål
has authorized: the ruleset requires the check to be green, and only Njål can
produce it.

## Human authority gate
Workflow: `.github/workflows/human_authority.yml`
Produces the ONLY `VALO Human Authority / control-plane` check-run.
- triggered by `workflow_dispatch` (manual, by Njål); never by PR code.
- runs from protected `main` only; never checks out or executes PR code.
- `permissions: contents: read` (cannot mutate code or start other write workflows).
- accepts ONLY `github.actor == "nsolland"`.
- binds to exact PR number, head-SHA, base-SHA (= main), and a policy-SHA
  (hash of the protected control-plane implementation on main:
  `.github/workflows`, `config`, `schemas`, `bin`, `docs/authority-model.md`).
- expires if head or base changes after issuance (merge-controller revalidates).
- NEVER produced by Worker, QC, or merge-controller.

## Class C (self-authority forbidden)
Any change to: `.github/workflows/**`, `config/**`, `schemas/**`, `bin/**`,
authority/policy docs, or the control plane itself — is automatically Class C:
- automatic Class C classification (no label games),
- automatic-merge forbidden,
- QC (unprivileged CI) must be green,
- `VALO Human Authority / control-plane` must be green (issued by Njål).
Njål merges manually (or authorizes an exact SHA). If head/base changes after
authorization, re-authorization is required.

## Merge-controller (lives in valo-platform, not here)
The merge-controller resides in `nsolland/valo-platform`'s protected default
branch (a dedicated GitHub App with merge-only scope is an alternative). It:
- NEVER checks out or runs PR code,
- requires the exact trusted QC + human-authority check-runs,
- requires head-SHA / base-SHA / policy-SHA agreement,
- requires exactly ONE risk class (rejects missing/multiple/unknown),
- reads the risk class from the trusted attestation, never from a PR label,
- REJECTS Class C (control-plane changes go through Njål directly),
- revalidates all required checks immediately before merge,
- NEVER operates against `valo-factory`,
- NEVER uses `--auto` while auto-merge is disabled.

## Modes
- NORMAL: full autonomous write runs permitted (subject to all gates).
- MAINTENANCE: no new write runs; queued drained; active stopped at safe checkpoint.
- INCIDENT_HOLD: as MAINTENANCE + highest alert; human must re-authorize.
- SHADOW: analysis only — detect/classify/simulate/QC/local-run; no push/PR/merge/label/remote.
