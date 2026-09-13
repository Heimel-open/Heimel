# AGENTS.md — valo-public-pack

## What this is

`valo-public-pack` is the **second vertical proof** of the VALO architecture:
a public-sector application process run over the same generic core as the
commercial electrician job.

```text
VALO Kernel -> Workflow ISA -> Function Fabric -> Public Pack
```

The goal is to prove VALO can run a public case process (søknad -> vedtak ->
underretning -> klagefrist -> avslutning) **without owning the authority**.

Canonical rule:

```text
Ingen offentlig agentisk handling uten eksplisitt hjemmel og kompetanse.
```

## Non-negotiable invariants

- **Forvaltningen beholder myndigheten.** The system orchestrates and controls
  execution; it never makes authority a model property. The Public Pack has no
  authority engine.
- **No public action without legal basis + competence.** `ISSUE_DECISION` is
  world-changing and requires LegalBasis + Competence + DecisionBasis +
  required evidence + rights impact + purpose, through Workflow ISA -> Action
  Contract -> REHT -> RACS -> execution -> Veritas -> BARO -> Kernel.
- **Legal basis is first-class; competence is first-class; delegation is
  narrower-scope-only** and never survives revocation or parent expiry.
- **Representation is verified, never prompt-based.** No "jeg representerer
  moren min".
- **Evidence is not a fact.** Evidence RECEIVED -> VERIFIED -> ADMITTED; facts
  carry provenance back to evidence. Conflicted critical facts block unsafe
  decisions (ELIGIBILITY = UNKNOWN/REQUIRES_REVIEW, never forced binary).
- **Habilitet can block a decision maker.** DISQUALIFIED blocks decision
  execution.
- **Decision issued != decision delivered.** Notification states SENT/
  DELIVERED/ACKNOWLEDGED/FAILED; appeal deadlines start from the defined event,
  not from send success.
- **No agent grants rights directly.** `grant_right()` without Function/
  Workflow/REHT is rejected; rights effect is explicit
  (RIGHT_GRANTED/DENIED/CHANGED/NO_RIGHT_EFFECT).
- **Purpose binding.** Data/evidence from one case type cannot be reused for an
  unrelated action without permitted purpose.
- **The deterministic Public admissibility check runs at the PRE-EXECUTION
  boundary** (fresh execution context), BEFORE REHT/Gateway: EVERY requested
  Case transition (REGISTERED, READY_FOR_REVIEW, UNDER_REVIEW,
  READY_FOR_DECISION, NOTIFIED, APPEAL_PERIOD, FINAL, CLOSED, ...) is checked
  for admissibility from the CURRENT Kernel state, and the rights-impacting
  invariant is re-derived for DECIDED — all before the Gateway can act. No
  external Case transition and no real-world effect can happen for a
  transition the invariant later rejects. The same checks are repeated in
  `append_event` as defense-in-depth. Kernel still does not authorize; REHT is
  still the only authorization boundary.
- **A legal basis must be RELEVANT, not merely present.** The LEGAL_BASIS
  authority must be active AND bound to the decision maker (principal), cover
  the case (scope) AND cover the case's service (constraints.service). An
  active legal basis for an unrelated case or service makes nothing decidable.
- **The REHT adapter is a test double outside the pack.** `reference/reht.py`
  implements the canonical REHT contract for the demonstrators to run against;
  it is NOT the real REHT. The pack owns no authorize() logic.
- **No legal LLM authority.** The LLM can retrieve/summarize/propose; it cannot
  alone declare legal basis authoritative, grant competence, authorize a
  decision, or change a right.
- **No public-specific leakage into Kernel/ISA.** The exact same core Functions
  as the Trades Pack are reused (no forks).

## Dependency anchors

Pinned merge SHAs in `repo-manifest.yaml`:
- `valo-kernel` @ `108f770`
- `valo-workflow-isa` @ `2ccb25f`
- `valo-function-fabric` @ `b2f058d`

No dependency on open branches.

## Layout

```
src/valo_public_pack/
├── domain.py      # public domain types + case states + structured exceptions
├── legal.py       # LegalBasis, Competence, Delegation
├── case.py        # Case model + guarded state machine
├── integrity.py   # conflict-of-interest, purpose binding, equal-treatment
├── functions.py   # public-specific Functions + registry (reusing FF stdlib)
├── golden.py      # PROCESS_PUBLIC_APPLICATION graph + engine
├── shadow.py      # shadow simulation + economics
├── trace.py       # provenance + explain + replay
├── viewmodel.py   # public view model (CaseSummary, DeadlineRisk, ...)
examples/          # positive golden path + 10 negative demonstrators
tests/             # 30+ scenarios, property, architecture, reuse proof
```

## Conventions

- Python `>=3.11`. FF contracts frozen pydantic, `extra="forbid"`.
- Case transitions are events through Functions/Workflow ISA; no direct status
  write.
- Legal basis/competence are data, never role descriptions in prompts.
- Numbers in shadow/economics are computed, never hardcoded.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ../valo-kernel --no-deps
.venv/bin/pip install -e ../valo-workflow-isa --no-deps
.venv/bin/pip install -e ../valo-function-fabric --no-deps
.venv/bin/pip install -e ../valo-trades-pack --no-deps
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests examples
.venv/bin/python -m compileall -q src tests examples
```

CI fetches the four pinned anchors and runs compileall + ruff + pytest on every
push/PR.

## Branch discipline

Never work on `main` directly. Create a branch per change, then open a PR.
Keep the working tree clean before starting.
