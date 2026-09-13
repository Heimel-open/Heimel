# Portfolio-to-Factory Build Intake

Status: **F0 implemented**  
Contract: `schemas/portfolio_build_profile_v1.schema.json`  
Compiler: `lib/portfolio_intake.py`  
CLI: `bin/valo-portfolio-compile`

## Purpose

Factory OS must build products faster than it creates architecture. It therefore accepts a **validated Portfolio Build Profile**, not an unclassified idea, chat transcript or vague product request.

```text
Idea / signal
→ Idebank identity
→ portfolio placement
→ primitive gate
→ commodity reuse plan
→ PortfolioBuildProfileV1
→ deterministic F0 compiler
→ bounded BuildOrderV1 per target repo
→ existing Factory intake / authority / QC controls
→ PR / QC / merge / release evidence
```

The profile is classification and build-planning data. It does not grant authority to write, merge, deploy, publish, spend or execute any consequence-bearing action.

## Separation of concerns

- `nsolland/Index` owns portfolio architecture and class semantics.
- `nsolland/idebank` owns idea identity and idea-decision linkage.
- `nsolland/valo-factory` owns build orchestration.
- canonical technical repositories own their own contracts and implementations.
- runtime consequence still traverses the normal VALO/reht execution-governance path.

## Required intake

A profile must identify:

- idea and concept version;
- portfolio map version;
- exact lowercase 40-hex source SHA;
- portfolio class and product family;
- target repository/repositories;
- desired delivery stage;
- primitive-gate result;
- reuse decision for commodity infrastructure categories;
- objective and acceptance criteria;
- a delimited build scope;
- evidence references;
- risk class;
- idempotency key;
- independent QC and receipt requirements.

## Primitive gate

Default result is reuse.

A build must not create a new core/runtime primitive because a product request is inconvenient to express.

`NEW_PRIMITIVE_ESTABLISHED` requires positive evidence plus explicit owner, migration reference and conformance reference. `NOT_ESTABLISHED` belongs upstream and is not valid build authorization.

## Commodity-first rule

Each build profile must make an explicit decision for:

1. model/inference;
2. rendering/media;
3. auth/identity transport;
4. scheduling/queues;
5. storage/database;
6. connectors/API clients;
7. UI framework;
8. deployment/runtime;
9. observability.

Each category is `REUSE`, `NOT_NEEDED` or `CUSTOM_REQUIRED`.

`CUSTOM_REQUIRED` requires evidence. “We can build it ourselves” is not evidence of need.

## Compilation into BuildOrderV1

`lib/portfolio_intake.py` validates the profile and compiles **one BuildOrderV1 per target repository**.

Portfolio data maps to build constraints:

- target repository → `target_repo`;
- objective → `objective`;
- acceptance criteria → `acceptance_criteria`;
- dependencies and scoped paths → corresponding BuildOrder fields;
- risk class, primitive decision, versions, exact source SHA and reuse decisions → `risk_hints`;
- profile/source/version/SHA lineage → compile receipt.

Authenticated command data remains separate:

- `principal`;
- `issued_via`;
- `authority`;
- `authority_basis`;
- command `source_ref`;
- issuance/expiry time;
- optional canonical base SHA.

**The PortfolioBuildProfile cannot populate those fields.** `BuildOrderV1.source_ref` is the authenticated command/control-plane source reference, not the idea source. The separate compile receipt binds the portfolio `source_ref` and exact portfolio source SHA.

## Compile receipt

A successful compile emits `portfolio-build-compile-receipt.v1` containing:

- profile id;
- concept version;
- map version;
- portfolio source ref + exact source SHA;
- authority-context source ref;
- canonical profile SHA-256 digest;
- target repos;
- deterministic build-order ids;
- receipt hash;
- `authority_effect: none`.

This receipt proves what was compiled. It does not authorize execution.

## CLI

```bash
valo-portfolio-compile profile.json authority-context.json --output compiled.json
```

Exit status:

- `0`: deterministic compilation succeeded;
- `2`: invalid input or not build-ready.

The command performs **no repository mutation**.

## One-shot application default

For a normal P4 application the expected path is:

```text
thin product UX
+ reusable workflows/functions
+ replaceable commodity models/APIs
+ existing storage/auth/scheduler/connectors
+ VALO governance only at consequence boundaries
= ship
```

Do not create a new evaluator, agent framework, model stack, scheduler, database abstraction or governance layer unless the build profile proves the existing capability is inadequate.

## Failure semantics

Factory intake fails closed for:

- missing target repo;
- missing concept/map version or exact source SHA;
- missing acceptance criteria;
- missing/dangerously broad scope;
- missing primitive-gate result;
- incomplete reuse plan;
- `CUSTOM_REQUIRED` without evidence;
- request for a new primitive without established owner/migration/conformance evidence;
- portfolio class `P6_LEGACY_ARCHIVE`;
- missing authenticated authority-context metadata;
- attempt to disable independent QC or receipt production.

Failure means **not build-ready**, not rejection of the idea.

## Gate progression

F0 is complete when this compiler is green in full Factory CI and merged.

Only then does F1 begin: reusable thin-app scaffolding, eight one-shot Factory profiles, commodity provider slots, smoke/e2e contracts and release/version/SHA/receipt binding.
