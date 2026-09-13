# Execution Assurance Pilot v1

Status: **packaged pilot candidate**  
Product state: **PILOT_OFFER**  
Platform underneath: VALO  
Authorization primitive: REHT

## What the buyer gets

One existing consequence-bearing workflow is observed at its final action boundary without changing how the customer executes it.

The pilot records the exact candidate action plus identity, current authority, purpose, relevant state, policy/constraints and the customer's real human/system outcome. It then shows, with correlated evidence:

- what REHT/VALO would have considered admissible, inadmissible, indeterminate or step-up-worthy;
- where the system and the customer's actual decision agree or disagree;
- where evidence or authority was missing/stale;
- which policy changes would have changed the result under deterministic replay;
- what the measured latency and instrumentation coverage are.

**Shadow mode cannot block, clear or execute anything.** The customer's existing system remains authoritative.

## Narrow entry point

Choose exactly:

```text
one tenant
+ one environment
+ one workflow
+ one subject/agent class
+ one consequence-bearing action class
+ one final integration boundary
```

Examples include one bounded purchase approval, refund, publication, deployment, access change, customer communication or machine-control class. The pilot contract is deliberately domain-neutral; the customer's first workflow supplies the concrete action contract.

## Pilot flow

```text
customer workflow
      ↓
exact candidate action at final boundary
      ├──────────────→ existing customer execution (unchanged in SHADOW)
      │
      └→ evidence/context envelope
            ↓
         SHADOW evaluation
         (non-authoritative)
            ↓
  ShadowEvaluation / replay / agreement
            ↓
       pilot metrics report
```

Only after separate evidence-backed approval may the same bounded subject/action class progress:

```text
SHADOW → RECOMMEND → ENFORCE
```

No skips. No automatic promotion. ENFORCE requires the canonical existing mode-promotion case, independent approver, mandate, evidence summary, rollback plan/trigger, validity window and receipt reference.

## What this is not

The pilot does not:

- replace the customer's IAM;
- replace the customer's workflow engine or system of record;
- migrate all policies;
- require a particular LLM/provider;
- grant an agent more authority;
- make VAIG an authorizer;
- make an insurance/evidence layer an authorizer;
- create a new VALO primitive;
- make VALO or REHT a standalone commercial product by declaration.

The purchasable thing here is the **bounded Execution Assurance Pilot outcome**.

## Canonical runtime ownership

This repository packages; it does not copy runtime logic.

| Component | Canonical owner | Pilot role |
|---|---|---|
| Shadow runtime | `nsolland/valo-platform` | observe/replay/agreement + mode semantics |
| REHT | `nsolland/valo-reht` | sole authorization boundary if ENFORCE is later approved |
| RACS | `nsolland/Racs` | deterministic decision contract binding |
| Gateway | `nsolland/valo-gateway` | approved effect/enforcement boundary |
| Veritas | `nsolland/Veritas` | execution/effect receipt evidence |
| VAIG | `nsolland/VAIG` | optional evaluation/risk signals; never authority |

Before a deployment bundle exists, all included runtime components must be pinned to immutable exact source SHAs (and image digests where containers are used). `pilot.yaml` intentionally leaves `artifact_ref` empty while this is only a reusable pilot template.

## Evidence required per observed action

Minimum:

- proposed action;
- actor identity;
- fresh authority state;
- purpose;
- relevant resource/world state;
- policy/constraints;
- actual human/system action or later outcome;
- tenant/task/action correlation.

Missing evidence remains missing. It is not converted into permission or falsity.

## Metrics

The template requires measurement of:

- in-scope action coverage;
- evidence completeness;
- agreement/mismatch;
- escalation misses/false escalations;
- decision latency;
- shadow external-effect count;
- uncorrelated records;
- unknown/insufficient-evidence rate.

The template intentionally does **not** invent universal target percentages for agreement or latency. Customer-specific targets are established from the workflow, risk and shadow baseline.

Hard invariants do exist:

- shadow external effects = **0**;
- shadow clearances issued = **0**;
- uninstrumented actions are reported, not hidden;
- tenant/task/action correlation is mandatory for usable evidence.

## Integration steps

See [`INTEGRATION_CHECKLIST.md`](INTEGRATION_CHECKLIST.md).

At a high level:

1. select the one workflow/action class;
2. define the exact action envelope and correlation IDs;
3. map identity/authority/purpose/state/policy evidence sources;
4. attach a passive observer immediately before the existing effect boundary;
5. run SHADOW and collect enough real observations for a stable baseline;
6. review gaps/mismatches/unknowns with the customer;
7. stop, continue shadow, or prepare a separately approved promotion case.

## Validation

Candidate contract:

```bash
python3 scripts/validate-execution-assurance-pilot \
  --pilot pilots/execution-assurance-v1/pilot.yaml
```

Deployment-ready contract additionally requires immutable component pins:

```bash
python3 scripts/validate-execution-assurance-pilot \
  --pilot customer-pilot.yaml \
  --deployable
```

A generic unpinned template **must fail** `--deployable`. That is intentional.

## Commercial exit criterion

A pilot is ready to offer when:

- a customer can identify one bounded workflow/action class;
- the observer can be attached without changing customer execution;
- required evidence sources and correlation can be mapped;
- package/runtime versions can be pinned;
- rollback is simply observer removal in SHADOW;
- the customer agrees what evidence/outcomes will constitute a useful result.

That is a sellable pilot boundary. It is not a claim that the whole VALO stack is a finished suite.
