# Swan GTM signal-to-action pattern adoption into AI Work OS

Date: 2026-08-10
Status: canonical pattern adoption / future GTM Operations Pack target

Work anchor:
- repo: `nsolland/valo-operator`
- canonical base-SHA: `7e6fd3cd899e2f9f25bd97efb187bd58c757ba88`
- branch: `feat/swan-gtm-signal-action-adoption`
- draft PR: `#17`
- issue: `#16`
- owner: ChatGPT
- owned files: this adoption document, `.claims/swan-gtm-signal-action-adoption.md`, README adoption reference
- dependencies: Operator API, registered Functions, Function Fabric, Workflow ISA, Kernel identity/authority/purpose/evidence state, REHT, Gateway, Veritas and BARO

Source:
- https://www.getswan.com/

Source status: external product and market signal observed 2026-08-10. Public product claims are not independent proof of implementation quality, security, correctness or runtime behavior.

## Decision

Adopt the useful Swan pattern into AI Work OS as a generic, provider-neutral `Signal -> Research -> CandidateAction -> governed execution -> verified effect` primitive.

Swan is not a runtime dependency, authority source, policy engine or new VALO layer. The pattern belongs in Work OS above the existing Operator / Function Fabric / Workflow ISA / REHT / Gateway / Veritas chain.

The LinkedIn signal pattern is generalized: LinkedIn is one signal provider among many, not a special architecture path.

## Canonical flow

```text
external/internal signal
  -> provider-neutral signal adapter
  -> immutable SignalEvent + provenance
  -> enrichment / research / entity resolution
  -> qualification / relevance assessment
  -> CandidateAction
  -> registered Function + typed inputs
  -> Function Fabric
  -> Workflow ISA
  -> fresh execution context
  -> REHT
  -> provider-neutral execution adapter
  -> CRM / email / LinkedIn / calendar / other GTM system
  -> Veritas observation
  -> BARO comparison
  -> Kernel event + learning proposal
```

AI may discover, enrich, rank, summarize and propose. It does not gain authority because a signal exists or because a model considers an action commercially useful.

## Canonical signal families

The same `SignalEvent` primitive should support at least:

- LinkedIn profile views, engagement, role changes and company changes;
- website intent and form/activity signals;
- CRM stage, stale-deal, closed-won and closed-lost events;
- email replies, non-replies and thread state;
- meeting creation, completion and follow-up state;
- funding, hiring, leadership and other company events;
- product-usage and customer-health signals where available;
- explicit operator-created signals.

Every signal should bind source, subject/entity references, observation time, provenance, tenant, confidence where relevant, and raw evidence reference/digest.

## Adopted patterns

### 1. Signal is evidence, not instruction

A profile view, website visit, job change, funding event or stale opportunity can justify research or a proposal. It cannot itself authorize outreach, CRM mutation, sequence enrollment or any other consequence-bearing action.

```text
signal observed != intent inferred != action useful != action authorized
```

### 2. Research and enrichment produce candidate state

Enrichment may resolve company, person, role, account, opportunity, relationship, prior contact and relevant context. Results remain provenance-bound evidence or candidate state until accepted into the relevant workflow.

Conflicting or stale enrichment must remain explicit rather than silently overwriting known state.

### 3. Qualification remains separate from execution

Models may score relevance, fit, urgency, buying intent, lookalike similarity, deal risk or next-best action. These scores are advisory evidence.

They may route or prioritize work, but they do not grant execution authority.

### 4. Every outbound or mutating action is a distinct registered Function

A future GTM Operations Pack should use explicit functions rather than a generic `do_sales_action` capability. Candidate function families include:

```text
GTM_CREATE_PROSPECT
GTM_CREATE_CRM_TASK
GTM_UPDATE_CRM_RECORD
GTM_CREATE_SEQUENCE
GTM_ENROLL_SEQUENCE
GTM_SEND_EMAIL
GTM_SEND_LINKEDIN_MESSAGE
GTM_CREATE_MEETING_BRIEF
GTM_CREATE_FOLLOWUP
GTM_MARK_DEAL_RISK
```

Each Function owns typed inputs, effect class, authority requirement, destination scope, idempotency behavior and expected postcondition.

### 5. `Closed won -> find lookalikes` becomes a governed discovery loop

Closed-won accounts may seed similarity search and account discovery. The output is a candidate prospect set with evidence for why each candidate matched.

Similarity never becomes automatic permission to contact a person or alter a CRM record.

### 6. `Closed lost -> learn` becomes an evidence loop

Closed-lost outcomes may generate competitor intelligence, objection patterns, qualification corrections and re-engagement candidates.

Learning can improve research, ranking and proposed workflows. It cannot mutate live authority, policy or outreach permissions.

### 7. Pipeline monitoring produces proposals, not silent mutations

Stale opportunities, missing follow-up, stage drift, weak engagement or missing stakeholders may produce `CandidateAction` objects.

A model can recommend the next action. The exact CRM or communication mutation still resolves to a registered Function and passes through the execution boundary.

### 8. Meeting signals feed preparation and follow-up through the same primitive

A new meeting can trigger research, account/person context assembly and a candidate briefing. Meeting completion can trigger candidate follow-up actions.

Read-only briefing generation and consequence-bearing external actions remain separate effects.

### 9. Provider adapters stay mechanical

LinkedIn, CRM, enrichment, email, calendar and website-intent providers are adapters, not governance components.

Adapters may own authentication, transport, provider payload mapping, provider idempotency fields and observed-state mapping. They may not decide whether an action is allowed.

The same Operator contract should be able to drive different CRM, enrichment and communication providers through configuration or adapter replacement.

### 10. Downstream reality must be verified

`HTTP 200`, `message queued`, `CRM request accepted` or `workflow completed` is not proof of the intended effect.

Where the provider permits observation, Veritas should read the resulting state back. BARO compares that state with the authorized postcondition.

```text
request sent != message delivered
request accepted != CRM state changed
sequence call succeeded != prospect enrolled
meeting API succeeded != meeting exists in expected state
```

Unknown and pending outcomes remain explicit.

### 11. Idempotency and exact-action binding are mandatory

Retries must not duplicate messages, contacts, tasks, sequence enrollment or CRM mutations.

An authorization for one exact message/action/destination cannot be reused after material content, recipient, destination, scope or state changes.

### 12. Cross-channel orchestration does not create cross-channel authority

Access to CRM does not imply permission to email. Access to email does not imply permission to message on LinkedIn. Access to enrichment data does not imply permission to write it into system-of-record state.

Each effect is evaluated under its own actor, purpose, scope, destination and current authority.

## Candidate contract

A future GTM pack should introduce a versioned candidate contract equivalent to:

```text
GTMActionIntentV1
- signal_refs / evidence_refs
- subject entity/account/person/opportunity
- actor + identity context
- purpose
- proposed registered Function
- typed proposed inputs
- destination/provider
- expected pre-state/version
- expected postcondition
- risk / value metadata
- validity window
- idempotency key
- provenance
```

This is candidate intent only. It is not a permit and must not bypass registered Function semantics or REHT.

## Placement

The reusable architecture is:

```text
AI Work OS / Operator
  -> GTM Operations Pack (future domain semantics)
  -> registered Function
  -> Function Fabric
  -> Workflow ISA
  -> fresh execution context
  -> REHT
  -> Gateway/provider adapter
  -> Veritas
  -> BARO
  -> Kernel
```

Signal adapters and execution adapters remain provider-neutral edges. The GTM pack owns GTM-domain contracts and admissibility. Operator remains generic. REHT remains the sole final authorization boundary.

## Required negative proofs for an executable GTM pack

An executable implementation is incomplete until tests prove:

1. A signal cannot itself grant authority.
2. Model confidence, fit score, intent score or lookalike score cannot authorize an external effect.
3. A read-only enrichment connector cannot be escalated into write authority.
4. CRM access cannot imply email or LinkedIn send authority.
5. Changed recipient, message, destination or material action content invalidates stale authorization.
6. Revoked or expired authority produces zero new external effect.
7. DENY/REJECT produces zero provider mutation.
8. Connector credentials cannot create business authority.
9. HTTP/API success without observed postcondition is not `EffectVerified`.
10. Unknown execution outcome remains UNKNOWN and is not blindly retried.
11. Retry is idempotent and cannot duplicate outreach, tasks, records or sequence enrollment.
12. The same Operator contract can drive at least two providers for a channel without moving authorization into the adapter.
13. Learning from won/lost outcomes cannot mutate live authority or policy.
14. Cross-channel orchestration cannot reuse authority from one channel for another.

## Priority

P1: canonicalize the generic Signal -> CandidateAction pattern in Work OS. This document does that.

P2: when a concrete GTM build is requested, implement a narrow GTM Operations Pack using the candidate contract and explicit Functions above.

P3: add concrete CRM/email/LinkedIn/enrichment adapters only against real endpoint contracts and credentials, keeping them mechanical and provider-neutral.

## Canonical invariant

```text
A signal may cause the system to look.
Research may cause the system to propose.
Only a registered, currently authorized action may cause the outside world to change.
Veritas proves whether that change actually happened.
```

Swan is adopted as a GTM product/workflow signal and pattern library, not copied as architecture and not treated as an authority source.