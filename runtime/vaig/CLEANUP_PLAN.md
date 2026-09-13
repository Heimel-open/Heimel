# VAIG Repo Cleanup Plan

Status: active cleanup plan  
Mode: scope freeze / packaging / submission engineering

This plan converts the repo from accumulated research context into controlled packages.

## 1. Objective

Stop adding theory.

Create a clean separation between:

- runtime
- protocol
- EU submission
- pilot package
- test evidence
- research archive

## 2. New top-level control files

These files now control the repo narrative:

- `SYSTEM_MAP.md` — authoritative concept and boundary map
- `SUBMISSION_PACKAGE.md` — EU-facing package control
- `PILOT_PACKAGE.md` — partner/pilot package control
- `TEST_EVIDENCE.md` — evidence and readiness map
- `CLEANUP_PLAN.md` — this checklist

## 3. Immediate cleanup sequence

### Step 1 — Readme correction

Update `README.md` so it points to:

- `SYSTEM_MAP.md`
- `PILOT_PACKAGE.md`
- `SUBMISSION_PACKAGE.md`
- `TEST_EVIDENCE.md`

Keep README short.

README should say:

```text
VALO is the architecture.
VAIG is the runtime.
VACS / ACS is the protocol.
RRP turns refusal into a governable state.
Receipt makes the chain auditable.
```

### Step 2 — EU folder cleanup

Reduce EU-facing material to a clean package:

- `docs/eu_submission/00_submission_package.md`
- `docs/eu_submission/01_executive_summary.md`
- `docs/eu_submission/02_eu_mapping.md`
- `docs/eu_submission/03_refusal_object_example.md`
- `docs/eu_submission/04_article6_consultation_response.md`
- `docs/eu_submission/05_sources_and_links.md`

No BARO, Tofoo, universal equation, investor language or product claims in EU package.

### Step 3 — Pilot folder

Create:

- `docs/pilot/00_pilot_package.md`
- `docs/pilot/01_partner_brief.md`
- `docs/pilot/02_workflow_template.md`
- `docs/pilot/03_sample_receipt.md`
- `docs/pilot/04_governance_report_template.md`

Pilot must be one workflow, not the full universe.

### Step 4 — Protocol cleanup

Clarify naming:

- ACS = Agent Control Standard
- VACS = VALO profile / implementation of ACS
- SSIP = implementation interface-surface standardization, not the main protocol

Add inside `vacs/`:

- `vacs/PROFILE.md`
- `vacs/README.md` cleanup
- `vacs/MAPPING_TO_VAIG.md`

### Step 5 — Level collision cleanup

Prevent L0-L4 confusion.

Rules:

- Use `D0-D4` or `distrust L0-L4` for VAIG distrust levels.
- Use `ACS-L0` to `ACS-L4` for ACS stack layers.
- Use `legacy runtime L1-L8` for historical runtime stack.

### Step 6 — Research archive

Move or mark as archive:

- Phi-law material
- universal equation material
- Tofoo narrative material
- crypto/on-chain roadmap unless explicitly needed
- swarm authority unless directly pilot relevant
- speculative sovereign-AI essays

Target folder:

`docs/research_archive/`

These may be valuable, but they must not pollute pilot or submission packaging.

### Step 7 — Test run evidence

Run tests and create:

`docs/test_runs/YYYY-MM-DD-vaig-core.md`

Record:

- command
- environment
- commit SHA
- pass/fail counts
- failing tests
- interpretation
- claim boundary

## 4. Claims allowed after cleanup

Allowed:

- VAIG is a testable runtime governance stack for agentic AI.
- VAIG contains a pre-intent evidence gate.
- RRP models refusal as a governable transition.
- ACS / VACS provides a packet and receipt protocol seed.
- The EU package frames execution-path mediation and Authority Visibility.
- The pilot package can test one bounded workflow.

Not allowed:

- VAIG is fully production-certified.
- VAIG guarantees EU AI Act compliance.
- VAIG guarantees insurance acceptance.
- ACS / VACS is already an adopted market standard.
- BARO predicts crises.
- Tofoo belongs in technical or EU core.

## 5. Frank / Svein rule

Do not show raw repo.

Show only:

- one-page company/pilot brief
- pilot package summary
- controlled architecture map
- sample receipt
- clear ask

Ask:

- pilot workflow
- company structure
- IP boundary
- advisor / investor / pilot role

## 6. EU rule

EU submission gets concept-level governance contribution only.

No operational internals beyond what is needed to understand:

- execution-path mediation
- Refusal Object
- Authority Visibility
- transition legitimacy
- auditability and accountability preservation

## 7. Freeze rule

Until first pilot package and EU package are clean:

- no new names
- no new theory
- no new constants
- no new architecture layers
- no public repo exposure
- no partner access to full private repo

## 8. Next concrete commits

1. Update `README.md` to link the control files.
2. Add `docs/eu_submission/00_submission_package.md` derived from `SUBMISSION_PACKAGE.md`.
3. Add `docs/pilot/00_pilot_package.md` derived from `PILOT_PACKAGE.md`.
4. Add `vacs/PROFILE.md`.
5. Add `docs/test_runs/` after test execution.
