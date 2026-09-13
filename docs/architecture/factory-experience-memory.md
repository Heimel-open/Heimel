# Factory Experience Memory

Status: implemented
Owner: execution worker

## Decision

VALO Factory has a provider-neutral Experience Memory boundary for retrieving prior agent work across sessions and providers.

```text
Claude / Codex / Antigravity / Copilot / other harness
  -> local session history
  -> optional retrieval adapter (Déjà Vu first)
  -> canonical ExperienceRecord
  -> freshness + supersession + evidence-binding assessment
  -> bounded context injection
  -> Discovery / Execution / Judgment
  -> current code/tests/policy/receipts remain authoritative evidence
  -> REHT remains final authorization boundary
```

Experience memory is not a source of authority and is not automatically a source of truth. A transcript records what an agent previously observed, proposed or believed. It may be wrong, stale or superseded.

## Canonical contract

`schemas/experience-memory-record.schema.json` binds recalled experience to:

- adapter and provider identity;
- originating session;
- source and content digests;
- observation time;
- repository;
- commit / PR / test / receipt / decision / file references when available;
- explicit validity window and supersession state;
- `authority_effect = none`.

`lib/experience_memory.py` classifies recalled records as:

- `corroborated_context` — current repository plus artifact/evidence binding;
- `raw_context` — transcript-only context requiring independent verification;
- `cross_repo_context` — reusable context from another repository, still requiring verification;
- `stale` — explicit freshness window has expired, not injected;
- `superseded` — replaced by a later record, not injected.

No state maps to ALLOW or any other execution authorization.

## Déjà Vu adapter

Déjà Vu is the first optional adapter because it can index coding-agent session history retroactively, expose recall through MCP, correlate sessions with files through `blame`, support cross-agent handoff, and keep the index local.

VALO adopts those retrieval patterns without making Déjà Vu a required runtime dependency. The adapter may be replaced without changing the canonical Experience Memory record.

The adapter boundary intentionally does not depend on Déjà Vu's internal transcript storage format. A thin caller extracts a recall/blame result and normalizes it through `deja_vu_record(...)`.

## Blame and decision reconstruction

```text
file
  -> sessions that touched/discussed it
  -> recalled decision context
  -> Git SHA / PR
  -> tests
  -> Veritas / provider receipts
  -> current judgment
```

This permits decision reconstruction without treating discussion history as canonical code provenance.

## Privacy and receipts

Canonical recall receipts persist digests of the query and injected context, not the raw query or raw recalled transcript. Provider-side redaction is useful defense in depth but does not replace VALO data-handling policy.

## Invariants

1. Memory never creates, preserves, revives or widens mandate or permission.
2. Stale or superseded memory is not injected as active context.
3. Cross-repository memory requires independent verification.
4. Transcript-only memory is labelled as raw context.
5. Git, tests, policy, receipts and current observed state outrank remembered narrative.
6. Retrieval-provider success is not evidence that the recalled conclusion is correct.
7. Judgment should prefer current evidence and, for high-impact work, independent provider review.
8. REHT remains the sole final runtime authorization boundary for consequence-bearing execution.

## External design signal

Déjà Vu documentation:
- https://vshulcz.github.io/deja-vu/
- https://vshulcz.github.io/deja-vu/guide/getting-started.html
- https://vshulcz.github.io/deja-vu/guide/benchmarks.html

External benchmark numbers are provider evidence about retrieval quality, not VALO acceptance criteria. Factory acceptance is defined by VALO's own conformance, retrieval, stale/supersession and evidence-binding tests.
