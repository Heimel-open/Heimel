# Agent Instructions

## Repository-local context

Before editing, read the repository manifest, README, claim registry, current branch state, and any nearer `AGENTS.md` file applicable to the target path. Repository-local source and contracts remain authoritative for implementation details.

## Portfolio verification governance (VALO-AVG-1)

This repository MUST follow the canonical policy owned by `nsolland/Index` at `governance/agent-verification-governance.md`.

- Policy version: `1.0.0`
- Normative body SHA-256: `f73ae98032007203584283248beca22d154f8a9e358ed48ccf72e90d27480e6d`
- Local Antigravity rule: `.gemini/rules/agent-verification-governance.md`

No producing agent may independently attest its own delivery. Same-session subagents are `INTERNAL_REVIEW`. Remote GitHub state controls SHA, branch, diff, PR, merge, and hosted-check claims. Missing external evidence is `UNVERIFIED`. Local environment failures are not repository or portfolio failures. Historical tests are not current green. Stale claims must be derived from PR and merge lifecycle. `ACTIVE_BLOCKER` requires a named active delivery that is currently and reproducibly blocked.

Repository-local instructions may specialize this policy but MUST NOT weaken it.
