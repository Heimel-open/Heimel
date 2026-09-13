# Portfolio Factory Backlog

Status: canonical current backlog for Portfolio Operating Model integration  
Updated: 2026-08-20  
Upstream architecture: `nsolland/Index/architecture/portfolio-operating-model-v2.md`

## Completed foundation

| Capability | Owner | Current state | Evidence / boundary |
|---|---|---|---|
| Portfolio Build Profile | Factory | **F0 IMPLEMENTED** | `schemas/portfolio_build_profile_v1.schema.json`, `lib/portfolio_intake.py`, `bin/valo-portfolio-compile`, `tests/test_portfolio_intake.py` |
| F0 deterministic compiler | Factory | **IMPLEMENTED** | validated `PortfolioBuildProfileV1 → bounded BuildOrderV1`; profile cannot self-create authority |
| Primitive/reuse gate | Index + Factory | **IMPLEMENTED IN F0** | reuse-first validation; unsupported custom capability/new primitive fails closed |
| Eight one-shot profiles | Factory | **F1 IMPLEMENTED** | `config/one_shot_profiles.json`; 77 mapped records route through eight reusable profiles |
| Reusable thin-app scaffold | Factory | **F1 IMPLEMENTED** | `lib/one_shot_scaffold.py`, `bin/valo-one-shot-scaffold` |
| Product smoke contract | Factory | **IMPLEMENTED** | every generated candidate carries dependency-free `smoke_test.py` |
| Exact release binding | Factory | **IMPLEMENTED** | `bind_release(...)` binds target SHA + portfolio SHA + profile digest + artifact digest |
| Local F0→F1 release-candidate path | Factory | **IMPLEMENTED** | one CLI can compile, scaffold, smoke and create `release-binding.json`; no push/deploy authority |

These capabilities are no longer backlog items. Do not reopen them as generic architecture work without a concrete defect.

## P0 — prove the lane on real portfolio input

The remaining P0 is evidence, not another framework.

```text
one current Idebank mission
→ current canonical portfolio placement
→ PortfolioBuildProfileV1
→ authenticated bounded authority context
→ F0 compile
→ F1 selected profile
→ materialized thin app
→ generated smoke PASS
→ exact target SHA release binding
→ independent QC / normal release-deploy path
```

Exit condition:

- use a real current Idebank mission rather than a test-only fixture;
- preserve exact source/map/concept SHA lineage;
- no new runtime primitive;
- generated product path satisfies its bounded acceptance criteria;
- release candidate has exact target SHA and deterministic artifact digest;
- deployment/publish, if performed, remains separately governed and receipted.

Until that real run exists, Factory is `VALIDATING`, not `PRODUCTIZED` or `OPERATING` as a portfolio product factory.

## P1 — throughput and reusable capability evidence

After the first real run:

| Capability | Intent |
|---|---|
| Mission-to-release throughput metric | measure elapsed work and failure points from approved mission to bound candidate |
| Commodity capability catalog quality | record where defaults work and where evidence-backed custom capability is actually needed |
| Connector-pack reuse | prefer existing auth/storage/scheduling/publishing/media/payment adapters before custom build |
| Release/deploy evidence | bind generated candidate to normal repository QC, release and deployment receipts |
| Product smoke/e2e profile | validate the actual user path, including correct stop/defer where consequences exist |

Repeated use — not design preference — determines what becomes reusable shared machinery.

## P2 — learning loop

| Capability | Intent |
|---|---|
| Verified outcome ingest | consume release/runtime outcome evidence without treating receipt as business outcome |
| Expected-vs-actual analysis | compare cost, reliability, user outcome and assumptions |
| Idebank evidence backfeed | mutate/combine/park ideas based on evidence, not aesthetic judgement |
| Reuse telemetry | identify common application capabilities worth promoting into shared modules/packs |

## External dependencies owned elsewhere

Factory must not duplicate these because it needs them for a product run:

- repository inventory/gap reconciliation → `nsolland/Index`;
- idea/mission identity and routing → `nsolland/idebank`;
- repository/product lifecycle state → `nsolland/Index`;
- runtime execution authorization → canonical VALO/reht owners;
- external deployment credentials/effect → separately governed deployment boundary.

## Do not build

Unless a primitive gate positively establishes need, Factory must not create another:

- generic agent runtime;
- generic evaluator;
- model router when an existing router/provider abstraction works;
- scheduler/queue abstraction;
- storage abstraction;
- standalone governance service duplicating VALO/reht;
- repository solely because a concept has a name.

## Definition of build-ready

A portfolio item becomes `BUILD_READY` only when:

1. idea identity is stable;
2. target product/capability/repository is explicit;
3. concept version and map version are pinned;
4. primitive gate is resolved;
5. reuse plan is complete;
6. acceptance criteria are testable;
7. required evidence exists or missing evidence is an explicit research dependency;
8. risk class is assigned;
9. a `PortfolioBuildProfileV1` validates;
10. authenticated command/authority flow can issue bounded `BuildOrderV1` work.

Everything else remains upstream. Factory must not compensate for ambiguity by inventing architecture.
