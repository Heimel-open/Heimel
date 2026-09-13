# MediVox health-workflow pattern adoption into AI Work OS

Date: 2026-08-09
Status: canonical pattern adoption / health-domain implementation target

Work anchor:
- repo: `nsolland/valo-operator`
- canonical base-SHA: `1cb22f66fd9b47141270a3fa32fa130a79a64a74`
- branch: `agent/medivox-health-work-os`
- owner: Codex
- owned files: this adoption document and the README adoption reference
- dependencies: Operator API, registered Functions, Function Fabric, Workflow ISA, Kernel identity/authority/relationship/purpose/evidence contracts, REHT, Gateway, Veritas and BARO

Sources:
- https://medivox.ai/
- https://medivox.ai/en/faq/
- https://medivox.ai/en/the-general-practitioner-and-the-difficult-conversation/
- https://medivox.ai/en/clinical-pharmacist-medication-reconciliation/

Source status: external product and market signal. Public product claims were observed on 2026-08-09 and are not independent proof of implementation quality, security, clinical safety or runtime behavior.

## Decision

Adopt the useful MediVox pattern into AI Work OS: natural-language clinical and administrative interactions become provenance-bound candidate records or candidate actions; AI may transcribe, structure, classify and route them; consequence-bearing actions remain distinct registered Functions; fresh identity, relationship, purpose, authority and domain state are evaluated before execution; the actual downstream effect is independently verified.

MediVox is not a runtime dependency, authority source, policy engine, clinical decision engine or new VALO layer. A future Health Operations Pack may own health-domain semantics without adding clinical logic to Operator.

## Signal

MediVox currently presents two materially different surfaces:

1. Documentation support: speech is converted into structured draft notes. MediVox states that the professional reviews, corrects and approves the draft and that the product does not make clinical judgments.
2. Digital phone secretary: the public home page says the AI service handles appointment booking, prescription renewal and common questions.

The important Work OS signal is the transition from `AI proposes/records` to `AI may trigger a real-world workflow`.

A phrase such as `renew my prescription` must never collapse request understanding, clinical decision, authority and execution into one model action.

## Canonical Work OS flow

```text
patient / clinician speech or text
  -> provider-neutral intake adapter
  -> immutable interaction artifact + provenance
  -> AI transcription / extraction / intent classification
  -> CandidateRecord or CandidateAction
  -> identity + relationship + purpose + domain-state evaluation
  -> exact proposed effect + required evidence
  -> human/domain review when required
  -> registered Function
  -> Function Fabric
  -> Workflow ISA
  -> fresh execution context
  -> REHT
  -> Gateway / health-system connector
  -> scheduling / messaging / EHR / prescription-request target
  -> Veritas observation
  -> BARO comparison
  -> Kernel event + learning proposal
```

AI may understand and prepare the request. It does not obtain authority from the conversation itself.

## Adopted patterns

### 1. Clinical documentation is candidate state before record state

Transcription and generated notes enter Work OS as `CandidateRecord`, not as committed clinical truth.

A candidate record should bind, as applicable:

- source interaction reference and digest;
- observation time;
- speaker/participant claims and confidence;
- transcription/model/tool version;
- generated structure and exact proposed record diff;
- source spans or evidence references;
- unresolved ambiguity and contradictions;
- reviewer identity and attestation;
- approved candidate digest;
- destination and expected postcondition.

A generated note being fluent, complete or medically plausible cannot substitute for professional approval where the workflow requires it.

### 2. A patient request is not an authorized instruction

Natural-language intent produces a `CandidateAction`.

`Book an appointment`, `cancel my appointment`, `renew my prescription`, `send this to my doctor` and similar requests differ in effect, authority, risk and required evidence. They must be resolved to distinct registered Functions rather than a generic assistant `execute` call.

The request is evidence of intent. It is not evidence that the caller is the relevant patient, has authority to act for another person, or that the requested action is clinically or operationally admissible.

### 3. Identity and relationship are first-class execution context

Before consequence-bearing execution, Work OS should resolve the minimum required identity and relationship context from fresh evidence.

Examples include:

- patient acting for self;
- guardian or representative acting for another person;
- clinician acting within an organizational role;
- administrative worker acting within delegated scope.

A verified login, phone number, caller ID or remembered prior interaction may contribute evidence. None alone creates authority beyond the relevant current mandate.

### 4. `Prescription renewal` is decomposed, never treated as one effect

The public phrase `renews prescriptions` is operationally ambiguous. Work OS must decompose it into explicit effects such as:

```text
CAPTURE_RENEWAL_REQUEST
ROUTE_RENEWAL_REQUEST
REQUEST_CLINICAL_REVIEW
RECORD_CLINICIAN_DECISION
EXECUTE_AUTHORIZED_PRESCRIPTION_ACTION
NOTIFY_PATIENT_OF_OUTCOME
```

These are not equivalent.

An AI phone agent may be allowed to capture and route a request without being allowed to make the clinical decision or execute a prescription action. Clinical authority must remain explicit, current and bound to the exact effect.

### 5. Administrative and clinical effects remain separate

Appointment lookup, appointment booking, cancellation, message routing, record drafting, clinical assessment and prescription-related actions must not share one broad capability simply because they originate in one conversation.

Each registered Function should define:

- typed inputs and outputs;
- effect class and risk;
- actor and authority requirement;
- identity/relationship evidence requirement;
- purpose and destination scope;
- current-state requirements;
- idempotency behavior;
- expected postcondition;
- escalation/step-up behavior;
- evidence and receipt requirements.

### 6. Need to Ask / Need to Acquire applies to health workflows

Missing information should not cause broad data access.

The agent may identify the minimum information needed to continue and request it through a governed path. It must not expand itself from conversation access into general patient-record, medication, scheduling or organizational access.

Only the minimum approved answer or evidence object should return to the requesting workflow.

### 7. Human approval binds to the exact candidate or action

Where professional approval is required, approval must bind to the exact record candidate or action digest, actor, patient/context, purpose, destination, effect and validity window.

A material change after approval invalidates the approval for execution.

A UI click or authenticated session records who acted. It does not replace fresh execution-boundary authority evaluation.

### 8. Conversation confidence is evidence, not permission

Intent confidence, transcription quality, extracted entities and model certainty may support routing or trigger clarification.

They cannot grant authority.

Low-confidence or contradictory identity, medication, patient, appointment or requested-effect data should produce clarification, abstention or governed step-up rather than speculative execution.

### 9. Downstream reality must be observed independently

A successful model response, API response or workflow-complete state is not proof of the intended health-system effect.

Veritas must observe the relevant downstream state where the integration permits it. BARO compares that state with the authorized postcondition.

The canonical distinction remains:

```text
intent understood != request accepted != action authorized != request sent != downstream state changed != desired effect verified
```

Unknown, pending, conflicting and partially applied outcomes remain explicit.

### 10. Learning cannot convert prior success into future authority

Work OS may learn that a workflow, template, routing choice or clarification strategy worked well.

It may not learn that because a clinician approved a similar action yesterday, the agent is authorized to perform it today. Fresh state and authority always win over memory.

## Health domain placement

A future `Health Operations Pack` may own:

- patient/participant and encounter domain contracts;
- appointment and communication lifecycle semantics;
- CandidateRecord and CandidateAction schemas;
- health-specific admissibility rules;
- required identity/relationship evidence;
- professional-review requirements;
- prescription-request workflow decomposition;
- record/publish Functions and expected postconditions.

Provider adapters may normalize EHR, scheduling, telephony, messaging or prescription-workflow protocols. They own authentication, payload mapping, transport, idempotency mechanism and observed-state mapping only.

Operator stays generic. REHT stays the sole final authorization boundary for consequence-bearing execution.

## Work OS reuse beyond health

The MediVox-derived primitive applies anywhere natural language can cross into operational effect:

```text
conversation
  -> interpreted intent
  -> candidate record/action
  -> exact effect decomposition
  -> identity/relationship/purpose evidence
  -> bounded approval/authority
  -> authorized execution
  -> independently verified effect
```

This is reusable for finance, public services, customer support, workforce operations, insurance and regulated service workflows.

## Required negative proofs

A Health Operations Pack or equivalent implementation is incomplete until tests prove:

1. Speech/text content cannot grant authority.
2. Caller ID, phone ownership or remembered identity cannot alone authorize a protected action.
3. AI-generated clinical documentation cannot silently become committed record state.
4. Changed note/action content invalidates stale approval.
5. Intent-confidence or completeness scores cannot substitute for authority or admissibility.
6. `renew prescription` cannot map directly to a generic execution capability.
7. Capture/route/request-review/clinical-decision/execution remain distinct effects.
8. A worker without patient-record access cannot acquire broad record access through `need` alone.
9. Revoked or expired clinical/administrative authority produces zero new external effect.
10. DENY/REJECT produces zero downstream mutation.
11. Connector credentials cannot create clinical or business authority.
12. HTTP/API success without observed postcondition is not EffectVerified.
13. Unknown execution outcome remains UNKNOWN and is not retried blindly.
14. Retry is idempotent and cannot duplicate booking, messaging or other effects.
15. The same Operator contract can drive at least two health-system adapters without moving authorization into the adapter.

## Priority

P1: adopt CandidateRecord/CandidateAction, exact effect decomposition, identity/relationship/purpose context, digest-bound approval and independently verified downstream effect as canonical Work OS behavior.

P2: implement a narrow Health Operations Pack when a concrete health pilot or demonstrator requires executable semantics. Start with low-clinical-risk administrative flows plus documentation approval; keep prescription execution separated behind explicit professional authority.

P3: defer direct MediVox/EHR/prescription-system adapters until endpoint contracts, credentials, target ownership, legal/clinical responsibility and a real proof environment exist.

## Canonical invariant

```text
AI may listen, transcribe, understand and prepare.
The domain pack defines the valid record or operational change.
The responsible actor approves or supplies the required authority for the exact effect.
REHT decides whether that exact effect may happen now.
The connector applies only the cleared mutation.
Veritas proves what actually happened downstream.
```

MediVox is adopted as a product and operational-control signal, not copied as architecture and not treated as evidence of clinical authority.