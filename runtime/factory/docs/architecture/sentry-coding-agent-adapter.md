# Sentry coding-agent adapter

Sentry is adopted as an external observability and incident-repair adapter for VALO Software Factory. It is not an authority source and does not create a new architecture layer.

## Flow

```text
production failure
  -> Sentry issue/event/trace evidence
  -> SentryCodingAgentAdapter
  -> Seer / replaceable coding-agent handoff (for example Cursor)
  -> patch / PR proposal
  -> Factory validation and evaluation
  -> REHT before consequential execution
  -> merge/deploy through governed execution path
  -> Sentry post-deploy evidence
  -> outcome verification
  -> Veritas receipt
```

## Sentry API binding

The adapter models Sentry's Seer Issue Fix endpoint:

`POST /api/0/organizations/{organization_id_or_slug}/issues/{issue_id}/autofix/`

For coding-agent handoff, the current Sentry API exposes `step=coding_agent_handoff` and accepts either a coding-agent `integration_id` or supported provider identity. The adapter only builds this request; network execution and credentials remain outside the adapter.

The default stopping point is `code_changes`. `open_pr` may be requested, but merge, deploy, and data mutation are never authorized by this adapter.

Reference: https://docs.sentry.io/api/seer/start-seer-issue-fix/

## Authority boundary

Allowed adapter capabilities:

- normalize Sentry incident evidence
- request root-cause / coding-agent work
- normalize patch and validation references
- request PR creation as a proposal workflow
- evaluate post-deploy recurrence evidence

Forbidden adapter capabilities:

- authorize or perform merge
- authorize or perform deploy
- mutate production data
- convert Sentry/Seer/Cursor confidence into execution authority
- claim success without post-deploy evidence

Consequential actions remain behind REHT. Veritas records the governed execution and outcome evidence.

## Provider replacement

Cursor is a replaceable coding-agent provider behind the adapter contract. Sentry may also hand work to other supported coding agents. Provider choice changes implementation capability, not authority.

## Outcome verification

Post-deploy verification distinguishes:

- `verified_no_recurrence`: the issue had a non-zero baseline and no events occurred during the verification window
- `still_recurring`: events continue after deployment
- `regression`: recurrence increased relative to baseline
- `insufficient_evidence`: there was no non-zero baseline to establish improvement

This prevents the factory from treating a merged PR or successful deployment as proof that the production problem is solved.
