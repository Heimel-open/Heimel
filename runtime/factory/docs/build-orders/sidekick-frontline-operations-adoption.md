# Build order — Sidekick frontline operations adoption

Date: 2026-08-08
Status: adopted / implementation target

Work anchor:
- repo: `nsolland/valo-factory`
- canonical base-SHA: `cb935db4abd610f85b2e3319ea887599bf14d208`
- branch: `feat/sidekick-frontline-factory`
- draft PR: `#63`
- owner: execution worker
- owned files: this build order, `config/ecosystem-adoptions.json`, `tests/test_ecosystem_adoptions.py`
- dependencies: AI Work OS ↔ Factory OS integration, BuildOrderV1, independent QC, provider-neutral adapters

Sources:
- https://www.ycombinator.com/companies/textsidekick
- https://www.linkedin.com/posts/justinso1_sidekick-yc-s26-is-an-ai-agent-that-handles-ugcPost-7491448574627504128-Dhz5

## Decision

Adopt Sidekick as a design signal for the kind of operational capability VALO Factory OS must be able to build for AI Work OS: low-friction frontline text/photo/voice intake, governed knowledge access, escalation, work-order/candidate-operation generation, integration with existing systems and capture of field knowledge.

Do not make Sidekick a required dependency, copy its internal architecture, or allow a frontline agent to self-modify production behavior directly from conversations.

The canonical relationship remains:

```text
frontline operational signal
  -> Work OS normalized interaction / evidence
  -> observed gap, failure, repeated task or capability request
  -> Observation / BuildOrderV1
  -> VALO Factory OS
       -> bounded Writer/worker
       -> deterministic tests
       -> independent Reviewer/QC
       -> merge candidate
  -> versioned Work OS artifact
       -> channel adapter / knowledge rule / domain pack / registered Function / Workflow ISA
  -> valo-operator
  -> fresh runtime context
  -> REHT
  -> Gateway / execution target
  -> Veritas / BARO / Kernel
```

Factory OS builds and improves the capability. It never grants the capability runtime authority.

## Observed Sidekick product signal

The useful product expectations are:
- workers can interact through ordinary text instead of learning a new application;
- photo and voice are first-class operational input;
- answers use company documents and local operating knowledge;
- uncertainty can escalate to a manager;
- work orders can be created and routed from the interaction;
- the agent can synchronize with systems the business already runs;
- industrial systems including PLC/SCADA can be integration surfaces;
- experienced-worker knowledge can be captured for future use.

VALO adopts these expectations under stronger provenance, admissibility, execution and authority boundaries.

## Factory capabilities to build

### 1. Provider-neutral frontline channel adapters

Factory missions may generate and maintain adapters for SMS, voice, photo, chat, kiosk or equivalent frontline channels.

Adapters may normalize:
- channel event shape;
- media/artifact references;
- locale and transcript metadata;
- stable channel identity reference;
- thread/correlation identity;
- delivery and observation state.

Adapters may not map channel identity directly to execution authority.

### 2. Governed knowledge-access capabilities

Factory may build retrieval, projection and knowledge-admission artifacts that allow Work OS to answer frontline questions.

Required properties:
- provenance-bound sources;
- explicit source/version/time;
- freshness policy;
- contradiction handling;
- abstention/escalation when evidence is insufficient;
- separation between historical evidence and current admissible guidance.

A human answer captured during escalation enters as a knowledge candidate. It is not promoted to canonical truth by the conversational agent itself.

### 3. Candidate work and registered Functions

Factory may build workflows that translate a frontline interaction into candidate operational work such as:
- create maintenance work order;
- assign or route a task;
- request inspection;
- update inventory state;
- notify a responsible role;
- propose an industrial control action.

Every consequence-bearing path must compile to a registered Function with typed inputs/outputs, risk/effect metadata, postconditions, idempotency and evidence requirements.

The conversational layer cannot invent these properties at runtime.

### 4. Existing-system adapters

Factory should prefer integration with installed systems over forcing replacement.

Potential targets include:
- CMMS;
- ERP;
- ticketing/service systems;
- messaging;
- inventory;
- industrial telemetry;
- PLC/SCADA/device gateways.

Provider credentials are execution transport capability only. They never become a Factory or Work OS authorization source.

For industrial write surfaces, the produced artifact must preserve fresh REHT or micro-REHT at the actual consequence boundary.

### 5. Frontline evidence becomes factory learning input

Repeated questions, failed answers, escalations, work-order outcomes and observed execution failures are valuable Factory inputs.

They may become:
- digest-bound regression fixtures;
- missing-capability observations;
- candidate BuildOrderV1 requests;
- domain-pack test cases;
- knowledge-freshness failures;
- adapter conformance cases;
- negative execution proofs.

They do not directly mutate production behavior.

The self-improvement path is:

```text
frontline outcome / failure / escalation
  -> evidence package
  -> Observation
  -> BuildOrder proposal
  -> bounded implementation
  -> deterministic tests
  -> independent review
  -> merge candidate
  -> deployment eligibility
```

No conversation can silently rewrite a production workflow, SOP, policy, Function or authority rule.

## Factory acceptance gates

For a frontline Work OS artifact, Factory QC must prove as applicable:

1. text/photo/voice normalization is provider-neutral;
2. media is digest/provenance bound before use as evidence;
3. channel identity cannot create or widen runtime authority;
4. read answers retain source/version/freshness evidence;
5. insufficient or contradictory knowledge can abstain/escalate;
6. captured manager/worker answers remain knowledge candidates until admitted;
7. generated work routes only through registered Functions;
8. generated tools cannot downgrade effect/risk/authority metadata;
9. external system credentials contain no authorization logic;
10. PLC/SCADA writes cannot bypass fresh REHT/micro-REHT;
11. DENY/REJECT produces zero external effect;
12. retry is idempotent for consequence-bearing operations;
13. external success without observed postcondition is not verified success;
14. frontline failure evidence can produce a regression fixture or BuildOrder proposal without self-modifying production;
15. Writer/worker cannot self-attest the fix;
16. independent QC is required before promotion.

## Placement

`valo-operator` owns the Work OS frontline contracts and runtime projection.

`valo-factory` owns building, testing, reviewing and promoting the adapters, domain artifacts, Functions and workflows that implement the capability.

`valo-gateway` remains the natural provider/channel execution edge where a concrete connector is required.

Knowledge admission remains a context/evidence concern.

REHT remains the sole final authorization boundary for consequence-bearing runtime execution.

## Dependency policy

Sidekick is not a required dependency.

Adopt the pattern natively and provider-neutrally. A future Sidekick integration, if commercially useful and technically conformant, is just another adapter/provider behind VALO boundaries.

## Canonical invariant

```text
Frontline interactions may reveal what should be built or requested.
Factory OS builds and verifies the capability.
Work OS exposes the capability.
REHT decides whether the exact consequential action may happen now.
Observed outcomes feed evidence back into the next factory cycle.
```
