# AGENTS.md - Tofoo- agent operating guide

> Machine-readable orientation for AI agents lives in `llms.txt`.
> Human/agent protocol overview lives in `CLAUDE.md`.
> This file is the **agent task contract**: how to work in this repo without
> breaking research epistemic discipline.

## Repository identity

- Stable ID: `valo.tofoo`
- Canonical name: **Tofoo-** (research track)
- Role: independent research track for the Phi-law / LIM framework.
- Normative status: **informative research**. Not runtime source of truth.
- URL: https://github.com/nsolland/Tofoo-

## What this repo is

Tofoo- is a research program. It owns hypotheses, mathematical definitions,
empirical observations, falsification criteria and explicitly marked
implementation claims. Research findings may inform the operational
architecture only through an explicit adoption record in `nsolland/Index`.

## Hard boundaries (do not cross)

- Tofoo does NOT define VAIG / REHT / RACS / Core runtime behavior.
- Do NOT present a hypothesis as a validated result.
- Do NOT present M4 (empirical) as M5 (independently replicated).
- Do NOT mark unverified constants, universal-law claims or cross-domain
  analogies as anything other than hypotheses.
- Do NOT place proprietary operational calibration in public-facing material
  unless it is already marked and linked as evidence.
- Every claim needs a reproducible evidence link and explicit limitations.
- This repository is not the runtime source of truth for VALO execution.

## Epistemic status discipline (mandatory)

Every research claim carries exactly one epistemic status:

| Status | Rule |
|---|---|
| hypothesis | testable proposition; may be wrong |
| mathematical_definition | formally stated; links to the derivation |
| empirical_observation | measurement; links to the measuring artifact |
| validated_result | verified within the stated architecture; state the scope |
| falsification_criterion | the condition that would refute the claim |
| implementation_claim | code exists and behaves as stated; still informative, not a scientific result |

Cross-reference `CLAIM_REGISTRY.md` (maturity), `experiments/experiment_registry.md`
(status) and `docs/theories/tofoo_falsification_backlog.md` (falsification).

## Metadata contract (this profile)

This repository adopts the canonical AI-first profile (nsolland/Index#338):

- `repo-manifest.yaml` - authoritative machine-readable contract
- `publiccode.yml` - publiccode standard metadata
- `llms.txt` - AI-first entry point
- `AGENTS.md` - this file
- `scripts/validate_repo_profile.py` - repository-local validator
- `.github/workflows/repo-profile.yml` - CI validation

These files MUST stay mutually consistent. CI validates the profile.

## Branch / PR discipline

- Work branches use a descriptive prefix (e.g. `hermes/<topic>`).
- One issue = one branch = one PR targeting `main`.
- Never force-push a claimed branch.
- Run `python3 scripts/validate_repo_profile.py` before committing profile changes.

## Commands

```bash
# Run the repository profile validator
python3 scripts/validate_repo_profile.py

# Run the test suite
python3 -m pytest tests/test_docpack.py -q
```

## Non-claims

- Not a runtime; not an execution authority; not a policy owner.
- Not a substitute for VALO architecture documents in `nsolland/Index`.
- Colab notebooks are demos, not validated production artifacts.

## License

MIT (LICENSE file absent in repo; declared in `repo-manifest.yaml` and `publiccode.yml`).

## Portfolio verification governance (VALO-AVG-1)

This repository MUST follow the canonical policy owned by `nsolland/Index` at `governance/agent-verification-governance.md`.

- Policy version: `1.2.0`
- Local Antigravity rule: `.gemini/rules/agent-verification-governance.md`

No producing agent may independently attest its own delivery. Same-session subagents are `INTERNAL_REVIEW`. Remote GitHub state controls SHA, branch, diff, PR, merge, and hosted-check claims. Missing external evidence is `UNVERIFIED`. Local environment failures are not repository or portfolio failures. Historical tests are not current green. Stale claims must be derived from PR and merge lifecycle. `ACTIVE_BLOCKER` requires a named active delivery that is currently and reproducibly blocked.

Repository-local instructions may specialize this policy but MUST NOT weaken it.
