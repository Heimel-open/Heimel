# Sidekick frontline operations adoption into AI Work OS

Date: 2026-08-08
Status: adopted / implementation target

Work anchor:
- repo: `nsolland/valo-operator`
- canonical base-SHA: `5815302e3fad7d5a3c0a33008e402b36c4e4edb0`
- branch: `feat/sidekick-frontline-work-os`
- draft PR: `#5`
- owner: execution worker
- owned files: this adoption document, `src/valo_operator/frontline.py`, `tests/test_frontline.py`, package exports
- dependencies: Operator API, registered Functions, Function Fabric, Workflow ISA, REHT, Gateway, Veritas

Sources:
- https://www.ycombinator.com/companies/textsidekick
- https://www.linkedin.com/posts/justinso1_sidekick-yc-s26-is-an-ai-agent-that-handles-ugcPost-7491448574627504128-Dhz5

## Decision

Adopt the useful Sidekick product pattern into AI Work OS: the operational system must reach frontline workers through channels they already use, accept text/photo/voice input, answer from governed organizational knowledge, create candidate operational work, route it into existing systems and capture field knowledge for later reuse.

Do not copy Sidekick's product architecture, make SMS a privileged identity source, let model confidence authorize work, or let captured human answers become timeless truth.

The VALO split remains:

```text
frontline text / photo / voice
  -> provider-neutral channel adapter
  -> FrontlineEnvelope
  -> context + knowledge retrieval / agent reasoning
  -> answer OR escalation OR CandidateOperation
  -> registered Function
  -> Function Fabric
  -> Workflow ISA
  -> fresh execution context
  -> REHT
  -> Gateway / CMMS / ERP / PLC / SCADA / other target
  -> Veritas / BARO / Kernel
```

Channel access is not execution authority.

## What is adopted

### 1. Zero-friction frontline intake

AI Work OS should support operational intake without requiring every worker to learn a new application. SMS, voice, photo, chat, kiosk and future channels normalize into one provider-neutral `FrontlineEnvelope`.

The envelope carries:
- stable interaction identity;
- channel identity/reference;
- modality;
- timestamp;
- locale;
- text and/or digest-bound artifact references.

It deliberately carries no mandate, permit or execution authority.

`channel_actor_ref` is evidence for correlation and later identity resolution. A phone number, chat identity or device session is never sufficient by itself to authorize a consequential action.

### 2. Answer, escalate or propose work

The frontline agent may:
- answer a read-only question from admissible organizational knowledge;
- ask for missing context;
- escalate to a manager or specialist;
- prepare and route a candidate operation;
- capture a candidate knowledge item for later admission.

The agent must have a legitimate abstention/escalation path. Confidence alone is not a safe threshold for consequential work.

### 3. Work-order and operational writes become CandidateOperation

Creating a work order, changing priority, assigning work, mutating an ERP record, sending a material notification or touching industrial control state is an effectful operation.

The frontline layer therefore emits `CandidateOperation`, which can reference only an already registered Function plus typed inputs. It cannot supply or override:
- effect type;
- risk class;
- authority requirement;
- permission;
- REHT decision;
- permit;
- postconditions;
- idempotency policy.

`bind_candidate_operation()` compiles this proposal into the existing `OperatorRequest`. Execution then follows the canonical Operator path.

A conversational agent may decide what it wants to request. It does not decide whether the request may happen.

### 4. Existing operational systems remain systems of execution

Adopt Sidekick's useful integration expectation: Work OS should pull from and write to the systems customers already run rather than requiring replacement first.

Examples:
- CMMS / work-order systems;
- ERP / inventory systems;
- ticketing and service systems;
- messaging and notification systems;
- industrial telemetry;
- PLC / SCADA interfaces where a governed adapter exists.

Read access supplies provenance-bound context. Write access is always downstream of registered Function semantics and fresh REHT clearance.

A provider API token, PLC credential, SCADA session or source-system permission is transport capability, not VALO authority.

### 5. Tribal knowledge becomes governed knowledge candidates

Sidekick's capture of veteran knowledge is valuable, but AI Work OS must not implement "someone answered once, therefore this is true forever".

`KnowledgeCandidate` therefore requires:
- source interaction;
- source actor reference;
- statement;
- provenance references;
- observation time;
- explicit freshness boundary;
- verification status.

The object has `authority_effect = none`.

A manager response can become useful organizational knowledge only through the knowledge/admissibility layer. Provenance, corroboration, policy ownership, contradictions and freshness determine whether it may be reused.

Expired knowledge may still remain as historical evidence. It cannot silently revive as current guidance.

### 6. Industrial boundary

For industrial environments, the architecture is:

```text
worker / sensor / operator
  -> text / voice / photo / local UI
  -> frontline agent
  -> candidate instruction or operation
  -> current plant context
  -> registered Function / domain rule
  -> REHT or micro-REHT at the relevant execution boundary
  -> mechanical gateway
  -> PLC / SCADA / device / CMMS
  -> observed postcondition + Veritas receipt
```

A correct SOP answer and an authorized machine action are different things. The first may be informational. The second requires explicit runtime authority and verified execution state.

## Implementation in valo-operator

`src/valo_operator/frontline.py` adds three bounded contracts:

- `FrontlineEnvelope` — text/photo/voice normalization with evidence-only channel identity;
- `KnowledgeCandidate` — provenance- and freshness-bound captured organizational knowledge;
- `CandidateOperation` — a proposed consequential action bound to a registered Function and fresh REHT.

The module contains no provider SDK, no direct execution adapter and no second authorization boundary.

## Required negative proofs

The frontline Work OS path is not complete unless tests prove:

1. channel identity does not become an `OperatorSession` or permit;
2. photo/voice inputs require artifact provenance;
3. captured knowledge requires provenance and freshness;
4. a manager response has no authority effect by itself;
5. a candidate operation cannot disable fresh REHT;
6. a candidate operation cannot inject authority/effect/risk overrides;
7. an operational write compiles only to a registered Function request;
8. DENY/REJECT yields zero downstream effect;
9. provider credentials never substitute for runtime authorization;
10. PLC/SCADA integration does not bypass the same execution boundary;
11. retries preserve idempotency for consequential work;
12. external success without observed postcondition is not treated as verified success.

## Canonical invariant

```text
The frontline channel makes Work OS reachable.
Knowledge makes it informed.
The registered Function defines what is being requested.
REHT decides whether the exact consequential action may happen now.
Veritas records what actually happened.
```

Sidekick is adopted as a product and interaction design signal, not as an authority source or required runtime dependency.
