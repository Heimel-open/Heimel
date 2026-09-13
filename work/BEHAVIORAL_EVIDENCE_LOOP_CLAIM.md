# Behavioral Evidence Loop Core Claim

- Repo: `nsolland/valo-factory`
- Canonical base SHA: `2c92bb727edb3dfc5cd883e9b6a6706ef300f5a6`
- Branch: `feat/behavioral-evidence-loop-core`
- Owner: `nsolland`
- Active delivery: provider-neutral behavioral evidence loop binding observations and findings to an exact action digest, external reht authorization, Veritas-backed execution receipt, measured outcome and controlled learning
- Owned files:
  - `lib/behavioral_evidence_loop.py`
  - `tests/test_behavioral_evidence_loop.py`
  - `docs/architecture/behavioral-evidence-loop.md`
  - `work/BEHAVIORAL_EVIDENCE_LOOP_CLAIM.md`
- Dependencies:
  - existing Factory evidence and evaluation path
  - provider adapters including Sentry and LogRocket
  - reht for consequence-bearing authorization
  - external execution PEP
  - Veritas receipt persistence
  - dataset admission before behavioral evidence can enter model training
- Scope rule: behavioral sources and coding agents remain evidence, analysis and proposal providers only. They cannot create authority, reuse stale authority, execute a different payload, self-verify outcome or admit their own training data.
