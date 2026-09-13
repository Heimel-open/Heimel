# AI Work OS ↔ Factory OS integration

Issue: `nsolland/valo-factory#56`  
Date: 2026-08-08  
Status: canonical relationship

Related:
- `nsolland/valo-operator#3` — Shapes/PeopleOS adoption into AI Work OS
- `nsolland/valo-factory#44` — universal BuildOrderV1 intake
- `nsolland/valo-factory#40` — governed self-improving factory evidence loop
- `danielmiessler/LifeOS` — external Work OS / general-purpose harness design signal

## Decision

AI Work OS is a first-class product target of VALO Factory OS.

Factory OS does not become the Work OS runtime, an HRIS, a business application or a new authority layer. It is the software factory that builds, verifies, promotes and evolves the capabilities that the Work OS exposes.

The operational Work OS surface remains `nsolland/valo-operator` plus domain packs, Function Fabric, Workflow ISA and provider adapters.

Canonical relationship:

```text
intent / research / product signal
  -> adoption decision
  -> BuildOrderV1
  -> VALO Factory OS
       -> isolated Writer/worker
       -> deterministic tests
       -> independent Reviewer/QC
       -> bounded correction / Learner proposal
       -> merge candidate
  -> versioned Work OS artifact
       -> read-only view / agent behavior / adapter
       -> domain-pack contract / registered Function
       -> Workflow ISA program
  -> valo-operator operational surface
  -> fresh runtime context
  -> REHT
  -> Gateway / execution
  -> Veritas / BARO / Kernel
```

Factory authority and runtime authority remain separate.

## What the factory may produce for Work OS

Factory missions may build and evolve:

- Work OS read-only views and projections;
- agent behaviors and role definitions;
- bounded skills and capabilities;
- domain-pack state machines and admissibility rules;
- registered Function definitions;
- Workflow ISA programs;
- provider-neutral adapters and connector mappings;
- UI/API surfaces around Operator contracts;
- deterministic tests and scenario fixtures;
- evaluation suites, negative proofs and receipts;
- migration and compatibility artifacts;
- generated operational tools compiled from natural-language specifications.

Each output is versioned, reviewed and evidenced. None grants runtime authority merely because Factory OS produced or merged it.

## Natural-language Work OS capability generation

Adopt the useful Shapes-style product expectation that a user can describe an operational tool, workflow or view in natural language.

The factory path is:

```text
natural-language requirement
  -> specification / candidate capability
  -> BuildOrderV1
  -> bounded implementation mission
  -> tests + independent review
  -> versioned artifact
```

Compilation target depends on effect:

- read-only requirement -> Operator view/query contract or adapter projection;
- domain workflow -> domain-pack transition + Function definition + Workflow ISA;
- effectful action -> registered Function with typed inputs/outputs, effect type, risk class, authority requirement, postconditions, idempotency and evidence requirements;
- agent behavior -> governed behavior artifact with explicit scope, owner and evaluation criteria.

Natural-language generation can propose code and contracts. It cannot create mandate, permission, clearance or execution authority.

## PeopleOps / Shapes example

The Shapes adoption in `valo-operator#3` is the first concrete Work OS domain example for this relationship.

A PeopleOps capability such as onboarding, offboarding, role change or compensation workflow should be built as:

```text
PeopleOps requirement
  -> BuildOrderV1
  -> Factory mission
  -> PeopleOps pack / adapter / registered Function
  -> tests including adverse-action and stale-context negatives
  -> independent QC
  -> merge + artifact/version receipt
  -> Operator discovery/runtime surface
  -> REHT for each exact consequential action
```

Factory OS may build the function that changes compensation. It may never authorize a compensation change at runtime.

## Factory/Work OS separation

### Factory OS owns

- build-order intake;
- repository and base-SHA resolution;
- claims and file ownership;
- isolated implementation contexts;
- Writer/worker execution;
- deterministic testing;
- independent review/QC;
- bounded correction rounds;
- merge-candidate production;
- build/provenance receipts;
- artifact promotion according to factory policy.

### Work OS owns

Through Operator and domain components:

- stable operational API/discovery surface;
- live business context;
- domain state and domain transitions;
- registered executable Functions;
- interaction with external providers;
- runtime execution requests and results.

### REHT owns

- final authorization of the exact consequence-bearing runtime action.

Neither Factory OS nor Work OS may create a second authorization boundary.

## Artifact promotion rule

A merged factory artifact is eligible for deployment, not automatically active or authorized.

Promotion must preserve explicit identity and version binding across:

```text
source requirement
-> build_order_id
-> repo + canonical base SHA
-> worker attempt
-> test evidence
-> independent review
-> merge SHA
-> artifact/version digest
-> deployment target
```

Runtime execution then separately binds:

```text
principal
+ mandate
+ current context
+ exact Function/version
+ exact payload/target
+ policy/evidence
-> REHT decision
```

Build-time approval is never reusable as runtime clearance.

## Self-improvement boundary

The existing Factory Learner may observe failures, test results, reviews and post-merge outcomes and propose Work OS improvements.

It may produce a new Observation or BuildOrder proposal. It may not:

- change runtime policy directly;
- activate a Function by itself;
- expand an agent mandate;
- change REHT authority semantics;
- self-attest its own improvement;
- bypass Writer/Tester/Reviewer separation.

This preserves the factory's self-improvement loop while preventing self-authorizing software.

## LifeOS pattern adoption

LifeOS is adopted as a design signal, not as a runtime dependency or authority source. The useful pattern is a Work OS that continuously compares an explicit Current State with an explicit Ideal State and uses bounded AI capabilities to reduce the verified gap.

Canonical VALO mapping:

```text
Current State
  -> evidence-backed operational snapshot
Ideal State
  -> explicit desired outcome + acceptance criteria
Gap
  -> candidate work / capability / workflow change
Discover / Harvest
  -> evidence + adoption proposal
Build
  -> BuildOrderV1 -> Factory mission
Judge
  -> independent Reviewer/QC, preferably cross-provider for high-impact work
Promote
  -> versioned artifact, never runtime authority
Operate
  -> Operator -> fresh context -> REHT -> execution
Verify
  -> Veritas/BARO observed outcome
Learn
  -> Observation / memory / new BuildOrder proposal
```

Adopt these patterns across Work OS and Factory OS:

- `Current State -> Ideal State` as an explicit convergence contract. Desired state must be testable or observable; "done" cannot be inferred from workflow completion alone.
- persistent work memory for prior decisions, observations, failures, learnings and artifact references. Memory is context/evidence, never mandate, clearance or permission.
- capability-aware routing before dispatch. The orchestrator selects from available, conformant providers/capabilities rather than assuming one model or vendor.
- independent judgment for consequential or high-impact work. Reviewer/Judgment should prefer a different provider/model family from the Writer/Execution provider when available, reducing correlated self-attestation failure.
- Harvest-style discovery: ingest an external source, extract candidate concepts, compare them with canonical VALO architecture, classify them as already-covered / partial / new, and emit an adoption proposal with exact owner repo and dependency placement.
- `VERIFY -> LEARN` after execution. Learning requires observed outcome evidence; a provider success response or completed workflow is insufficient.
- self-improvement only through the governed factory loop. Learning may change future context or propose a new BuildOrder; it cannot rewrite production policy, activate capabilities or expand authority directly.

Do not adopt LifeOS semantics that collapse orchestration, execution, judgment and authority into one agent identity. VALO keeps role separation and the REHT boundary intact.

## Persuasion-resistant judgment

Empirical work on sycophantic AI shows that interventions can reduce how appealing or credible users find a model without reliably reducing the model's persuasive effect. Awareness of influence is therefore not equivalent to independence from influence.

Source: `arXiv:2607.25166` and Peter Slattery's 2026-08-08 summary of the result.

Factory and Work OS adopt the following consequence:

```text
awareness != independence
human review != independent control when the reviewer is inside the same influence loop
persuasiveness != evidence quality
confidence != authority
```

For consequential judgment:

- reviewers must evaluate artifacts against explicit evidence, tests, contracts and acceptance criteria rather than the persuasiveness of model output;
- judgment should be structurally separated from execution and should prefer a different provider/model family for high-impact work when available;
- reviewer context should minimize unnecessary exposure to the writer's persuasive rationale before primary evidence inspection;
- a human approval signal is not treated as an independent control merely because a human clicked approve;
- runtime authorization remains based on mandate, scope, current context, evidence and policy, never on model confidence or persuasive force.

Canonical principle:

`Awareness is not authorization. Human oversight cannot be treated as an independent control when the human decision-maker is itself inside the model's influence loop.`

## Required Work OS factory proofs

For Work OS artifacts, Factory CI/QC should prove as applicable:

1. generated tools cannot invent or downgrade effect/risk/authority metadata;
2. domain-pack logic cannot bypass Operator/REHT for consequence-bearing actions;
3. provider adapters contain transport/schema mapping only, never authorization logic;
4. read-only views remain read-only;
5. changed Function/version/payload/target invalidates stale runtime clearance;
6. DENY/REJECT paths produce zero external effect;
7. retries preserve idempotency for consequential effects;
8. external success without observed postcondition is not treated as verified success;
9. Worker/Writer cannot approve or merge its own artifact;
10. a merged artifact has a reconstructible build/provenance receipt;
11. runtime authority is evaluated fresh after deployment;
12. the same Factory OS pipeline can build Work OS capabilities for multiple domain packs without architecture changes;
13. Current State and Ideal State are explicit and their convergence is verified from evidence rather than inferred from workflow completion;
14. persistent memory cannot create or revive mandate, permission or runtime clearance;
15. high-impact Writer/Reviewer provider independence is enforced when the configured provider set allows it;
16. Harvest/adoption output is a proposal or BuildOrder input and cannot mutate canonical architecture directly;
17. consequential review cannot rely on model persuasiveness, confidence or human awareness of influence as substitutes for evidence-based independent judgment.

## Canonical invariant

```text
Factory OS builds what the Work OS can do.
Work OS exposes what can be requested.
REHT decides what may actually happen now.
Veritas/BARO proves what actually happened.
Learning proposes what should change next.
```

This relationship is additive. It creates no new top-level VALO layer and no new authority source.
