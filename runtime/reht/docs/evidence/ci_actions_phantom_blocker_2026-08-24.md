# CI Actions phantom workflow blocker — 2026-08-24

## Symptom

Every GitHub Actions run on `nsolland/valo-reht` fails with `startup_failure`
and 0 jobs, including:
- push to main
- pull_request
- re-runs of previously-green SHAs
- even a brand-new minimal `workflow_dispatch` probe

GitHub reports "This run likely failed because of a workflow file issue", but
`actionlint` validates every workflow file clean and the files are byte-identical
to the last green run (2026-08-22).

## Root cause (GitHub-side, not repo-side)

A ghost workflow registration exists in GitHub's Actions backend:

- workflow_id: `340399655`
- path: `BuildFailed` (no such file exists in git)
- state: `deleted`
- created: 2026-08-23T05:52:31Z (exactly when failures began)
- every push/PR run references this phantom id (`path: "BuildFailed"`)
- absent from the workflows list; `disable` -> 403; `delete` -> 404

This matches a documented GitHub bug seen in at least two independent cases
(community discussions, Mar 2026 and Jul 2026) with the identical
`path: "BuildFailed"` / `state: "deleted"` signature.

## What was tried and ruled out

- `actionlint` on all workflow files -> clean
- full `python -m pytest` locally -> green (248 passed, 1 skipped)
- disable/re-enable workflow via API
- cosmetic ci.yml change (concurrency) -> new run still references phantom
- rename ci.yml -> ci-main.yml -> new active entity (341187348), but push
  events STILL reference phantom 340399655
- deleted all 114 runs tied to the phantom id -> registration lookup 404s,
  then re-materializes on the next event
- reverted all experimental workflow changes; main is back to canonical
  ci.yml / act001 / assurance-release-gate

Per the confirmed community cases, the only thing that stops the failures is
removing ALL workflow files (which disables CI), and even that is not a fix.

## Resolution required

GitHub Support must purge workflow registration `340399655` from the backend
for `nsolland/valo-reht`. No repo-side action can remove it.

## Local status (what we control)

- PR #37 (two-core runtime) merged: `75f8b9d`
- Local test suite: `248 passed, 1 skipped`
- Local two-core regression + latency + concurrency evidence: green
- The CI red state is a GitHub-side phantom, NOT a repo regression
