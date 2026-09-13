# Build Order — Health Work OS / MediVox feature-parity target

Date: 2026-08-10
Status: ready for implementation

## Work anchor

- control repo: `nsolland/valo-operator`
- canonical control base: `main@1cb22f66fd9b47141270a3fa32fa130a79a64a74`
- active branch: `agent/medivox-health-work-os`
- active PR: `#7`
- owner/claim: Work OS health delivery
- owned control files: `docs/MEDIVOX_HEALTH_WORK_OS_ADOPTION.md`, this build order, README reference
- target new domain repo: `nsolland/valo-health-pack`
- dependencies:
  - `nsolland/valo-kernel@b03d1469195e599c2896de7347f39b9c841c7c9a`
  - `nsolland/valo-workflow-isa@2ccb25f2513394e22d176e2aa05a31a031f862b9`
  - `nsolland/valo-function-fabric@0c464961b7fcd50cc6a6aff87bbcb0e8746d5dfc`
  - `nsolland/valo-reht@dea6730fed804892018657f9e8d503cf681b7bad`
  - existing Operator runtime, Gateway/Veritas/BARO path and Frontline contracts
  - existing `valo-platform` voice transcription substrate and governed shadow/receipt runtime

## Delivery goal

Deliver the minimum complete Health Work OS slice that can perform the same class of operational work publicly described by MediVox without creating a clinical-decision authority inside the AI layer:

```text
patient / clinician voice
  -> live channel
  -> transcript + provenance
  -> CandidateRecord or CandidateAction
  -> identity / relationship / purpose / current health-workflow state
  -> exact registered Function
  -> domain admissibility
  -> REHT
  -> external health-system effect
  -> independent observation
  -> receipt / outcome
```

Initial parity target:

1. clinician conversation -> structured clinical-note draft -> clinician review -> governed record commit;
2. patient phone interaction -> appointment lookup / booking / reschedule / cancellation;
3. patient phone interaction -> prescription-renewal request capture and routing -> clinician decision -> patient notification;
4. common read-only administrative questions from governed knowledge;
5. no autonomous diagnosis, prescribing or clinical authority inferred from model output.

Direct electronic prescribing is not required for the first parity release. If a commissioned target system later supports an already-authorized prescription effect, it is added as a separate registered Function behind explicit professional authority and fresh REHT clearance.

## What already exists — reuse, do not rebuild

### Operator / Work OS

Existing `FrontlineEnvelope`, `CandidateOperation` and `bind_candidate_operation()` already provide provider-neutral text/photo/voice intake and compile consequential proposals only into the canonical `OperatorRequest`. Channel identity carries no authority.

Existing Operator already provides registered Function dispatch, fresh session validation, REHT, deterministic binding, Gateway execution, independent Veritas observation, BARO outcome and evidence receipts.

### Telephony / communication groundwork

Existing Work OS commercial provider configuration already supports provider-neutral `voice`, `sms` and `email` outbound notification edges and a Twilio-shaped external proof.

Existing DIAL adoption defines the missing provider-neutral telephony-channel boundary and correctly treats voice/SMS/WhatsApp as transport only. It is currently an implementation candidate, not the complete inbound conversational runtime.

### Voice transcription

`valo-platform` already has:

- `voice/whisper_client.py` for audio -> transcript;
- `voice/transcription_engine.py` for language/quality/intake processing;
- voice API routes and voice documentation.

Reuse this as an ASR substrate through a provider-neutral adapter. Do not make it health authority or clinical truth.

Important remediation: the current Whisper adapter manufactures a confidence score from transcript length because the upstream response does not supply one. That synthetic value must never be used as health-workflow confidence, identity confidence, clinical confidence or an execution threshold. Where provider confidence is unavailable, record it as unavailable/unknown and use explicit evidence/clarification rules.

The current intent detector is generic business keyword routing. Do not reuse it as clinical intent semantics.

### Kernel

Kernel already owns generic entity, identity, relationship, purpose, authority/delegation, evidence, time and event contracts. WorldPack extensibility is enforceable and namespaced.

Health-specific entities/events therefore belong in a Health WorldPack/domain pack. Do not add patient/clinical semantics to Kernel core.

### Function / workflow / authorization

Function Fabric already supplies the governed typed-function model and provider-neutral tool catalog. Workflow ISA supplies deterministic workflow execution. REHT already fail-closes on freshness, exact principal/capability and full action-contract binding.

Do not create a health authorization engine.

### Candidate mutation / human review

`valo-platform` document mutation already separates READ / PROPOSE / APPLY / COMMIT / REVERT / PUBLISH, binds human acceptance to an exact proposal and rejects stale mutations.

Reuse this pattern for clinical-note candidate -> approved record transition rather than creating a second generic document-approval mechanism.

### Safety escalation

The existing dual-path safety escalation engine already supports deterministic escalation floors, probabilistic assessment that cannot lower the floor, stale-state invalidation and exact-state human approval.

Reuse the generic mechanism for clinician-owned health escalation rules. Do not embed diagnosis or model-only clinical triage authority in it.

### Shadow / receipts

The governed runtime already supports shadow execution with zero external effect, canonical action/decision/receipt lineage and minimum-disclosure surface projections.

Health must enter live execution through this existing shadow gate, not via a separate pilot path.

## Confirmed gaps

1. No `valo-health-pack` exists.
2. No registered health Function set exists in Function Fabric/domain packs.
3. No health CandidateRecord/CandidateAction domain contracts exist in executable code.
4. No patient/guardian/clinician relationship resolution is bound into health-domain admissibility.
5. No appointment lifecycle/domain state exists.
6. No prescription-renewal workflow decomposition exists in runtime code.
7. Existing voice support is file/request transcription, not a complete inbound real-time phone conversation runtime.
8. Existing generic voice adapter is primarily an outbound notification edge, not full duplex telephony/session control.
9. No TTS/voice-response adapter was found in the active repos.
10. No EHR/scheduling/prescription-workflow adapter exists with independent observed-state verification.
11. Existing transcription confidence is unsuitable as health evidence because it is synthesized from transcript length.
12. No health-specific minimum-disclosure/PHI receipt contract or retention boundary exists.
13. No end-to-end health acceptance proof currently shows voice -> exact health action -> REHT -> external effect -> independent verification.

These are the active delivery gaps. Generic agent runtime, execution authorization, workflow, function, receipt and evidence infrastructure are not gaps.

# Implementation order

## HWO-1 — Health Operations Pack core

Repo: create `nsolland/valo-health-pack`.

Build a domain pack over Kernel -> Workflow ISA -> Function Fabric -> REHT. It is not a new architecture layer.

### Contracts

Add frozen/versioned contracts with deterministic digests:

- `HealthParticipantRefV1`
- `PatientContextV1`
- `HealthRelationshipEvidenceV1`
- `EncounterRefV1`
- `HealthConversationRefV1`
- `CandidateClinicalRecordV1`
- `CandidateHealthActionV1`
- `ClinicalReviewAttestationV1`
- `AppointmentStateV1`
- `PrescriptionRenewalRequestV1`
- `HealthEffectObservationV1`

Keep raw audio and raw clinical text out of generic Kernel events and generic receipts. Store references/digests and minimum necessary metadata there; sensitive content remains behind the health evidence/data boundary.

### Health WorldPack

Register namespaced health entity/event types through existing Kernel WorldPack support, for example:

- `health.patient_ref`
- `health.encounter`
- `health.appointment`
- `health.renewal_request`
- `health.clinical_record_ref`
- `health.communication`

Kernel core remains unchanged.

### Registered Functions

Implement distinct typed Functions. Minimum set:

```text
HEALTH_CREATE_NOTE_DRAFT
HEALTH_APPROVE_NOTE_DRAFT
HEALTH_COMMIT_CLINICAL_NOTE

HEALTH_LOOKUP_APPOINTMENT_AVAILABILITY
HEALTH_BOOK_APPOINTMENT
HEALTH_RESCHEDULE_APPOINTMENT
HEALTH_CANCEL_APPOINTMENT

HEALTH_CAPTURE_RENEWAL_REQUEST
HEALTH_ROUTE_RENEWAL_REQUEST
HEALTH_REQUEST_CLINICAL_REVIEW
HEALTH_RECORD_CLINICIAN_DECISION
HEALTH_NOTIFY_PATIENT
```

Reserve but do not enable by default:

```text
HEALTH_EXECUTE_AUTHORIZED_PRESCRIPTION_ACTION
```

That Function requires an explicit commissioned prescription target, professional authority, exact decision binding and independent effect observation.

### Domain admissibility

Implement fail-closed checks for:

- participant/patient correlation;
- acting-for-self vs representative/guardian relationship;
- clinician/administrator delegated scope;
- purpose;
- current appointment/renewal/record state;
- freshness/version;
- exact candidate digest;
- required professional review;
- destination scope;
- replay/idempotency.

No domain rule may mint a REHT permit.

## HWO-2 — Voice and telephony bridge

Owner repo: `nsolland/valo-operator` for normalized channel/Operator bridge; reuse `valo-platform` ASR behind adapter contracts.

### Inbound session contract

Implement provider-neutral:

- `VoiceSessionEnvelopeV1`
- `VoiceTurnEvidenceV1`
- `AudioArtifactRefV1`
- `TranscriptEvidenceV1`
- `VoiceResponseCandidateV1`
- `CommunicationChannelAdapter`

Normalize inbound provider events into existing `FrontlineEnvelope` plus health conversation references.

Provider call IDs, caller claims and phone numbers are evidence/correlation only.

### ASR adapter

Wrap existing Whisper client behind `SpeechToTextAdapter`.

Requirements:

- provider replaceable;
- no fabricated confidence;
- transcript bound to source audio digest, provider/model/version and timestamps;
- language explicit;
- uncertainty/unknown supported;
- interruption/partial-turn handling represented explicitly;
- no health intent authority emitted by ASR.

### TTS adapter

Add provider-neutral `TextToSpeechAdapter` with at least one commissioned implementation or deterministic test double.

TTS is rendering only. Patient-specific disclosure or consequential communication must come from a cleared communication Function before synthesis/send.

### Telephony adapter

Implement one real provider adapter only after the provider contract is available; keep Dial/Twilio/other providers replaceable.

Required behavior:

- inbound call/session lifecycle;
- media/turn ingestion;
- outbound response delivery;
- call end/timeout/error semantics;
- provider event IDs;
- replay protection;
- no direct health-system mutation.

## HWO-3 — Clinical documentation parity

Build the clinician flow first because it has the narrowest execution surface.

```text
audio
 -> transcript evidence
 -> structured CandidateClinicalRecord
 -> exact diff
 -> clinician review
 -> ClinicalReviewAttestation bound to candidate digest
 -> HEALTH_COMMIT_CLINICAL_NOTE
 -> REHT
 -> EHR adapter
 -> Veritas observation
```

Rules:

- transcript is evidence, not record truth;
- generated note is candidate state;
- clinician approval is bound to exact content/digest;
- any material edit after approval requires new approval;
- provider API success is not record-commit proof;
- no model confidence can substitute for clinician review where review is required.

## HWO-4 — Digital phone secretary: appointments

Implement the first autonomous administrative effect.

Flow:

```text
voice -> intent candidate -> identity/relationship resolution
 -> current appointment/availability state
 -> exact Function
 -> REHT
 -> scheduling adapter
 -> Veritas state observation
 -> patient confirmation
```

Supported effects:

- lookup availability;
- book;
- reschedule;
- cancel.

Every mutation uses an idempotency key and expected before-state/version. Retry after timeout must first observe target state before any re-send.

Unknown identity or acting-for-another relationship must fail closed to clarification/step-up rather than expose patient-specific schedule information.

## HWO-5 — Prescription-renewal workflow

Implement renewal as a workflow, not one model capability.

Required chain:

```text
HEALTH_CAPTURE_RENEWAL_REQUEST
 -> HEALTH_ROUTE_RENEWAL_REQUEST
 -> HEALTH_REQUEST_CLINICAL_REVIEW
 -> HEALTH_RECORD_CLINICIAN_DECISION
 -> HEALTH_NOTIFY_PATIENT
```

The phone agent may capture and route. It must not infer prescribing authority from the caller, prior prescriptions, model output or clinician-like language.

If later enabling `HEALTH_EXECUTE_AUTHORIZED_PRESCRIPTION_ACTION`, require:

- exact patient/medication/action scope;
- fresh professional authority;
- exact clinician decision digest;
- target system and destination scope;
- current state/freshness;
- short-lived REHT permit bound to the full action contract;
- independent downstream observation.

## HWO-6 — Health-system adapter and observation kit

Do not start with vendor-specific business logic.

Create provider-neutral adapter contracts for:

- scheduling;
- clinical-record commit;
- renewal-request routing;
- patient notification;
- optional later prescription execution.

For acceptance, build TWO standalone vendor-shaped test services with different protocols/configurations. The same Health Pack Function and Operator path must drive both without health authority entering an adapter.

Each adapter separates:

```text
send/apply transport
!=
observe target state
```

Veritas must independently read the target state. BARO compares observed state against the exact authorized postcondition.

## HWO-7 — Privacy, disclosure and receipt minimization

Health data requires a stricter evidence projection than ordinary Work OS traffic.

Implement:

- sensitive-field classification for health payloads;
- minimum-disclosure surface receipts;
- content digest/reference instead of raw transcript/note in generic receipt paths;
- explicit purpose and audience/destination binding;
- configurable retention/deletion references for raw audio and transcript artifacts;
- log redaction tests;
- no secret/token/raw patient payload in exception text;
- access to sensitive artifacts separated from execution authority.

Reuse the existing minimum-disclosure receipt projection pattern rather than creating a second receipt system.

## HWO-8 — Shadow-to-live acceptance gate

Use the existing governed shadow runtime.

### Shadow proof

Run the complete flows with zero external effect:

- note draft -> proposed commit;
- book appointment;
- cancel/reschedule;
- renewal capture/routing;
- clinician decision notification.

Shadow must produce the same canonical action digest, REHT decision semantics and receipt lineage expected by live execution while proving `SHADOW_NO_EXTERNAL_EFFECT`.

### Live proof

Live is allowed only after all negative proofs below are green against standalone external services and at least one commissioned real integration is available.

# Required negative proofs

1. Phone number/caller ID cannot create patient identity or authority.
2. Conversation text cannot create authority.
3. ASR confidence cannot authorize or suppress step-up.
4. Synthetic transcript confidence is rejected as health authority/evidence quality.
5. Generated note cannot become committed record state without the required exact approval.
6. Any material note change invalidates stale approval.
7. `renew prescription` cannot map directly to prescription execution.
8. Capture, route, clinical review, decision and execution remain separate effects.
9. A patient request cannot create clinician authority.
10. Representative/guardian uncertainty cannot silently fall back to self authority.
11. Read access to health data cannot become write authority.
12. Connector credentials cannot grant clinical or administrative authority.
13. DENY/REJECT produces zero external mutation.
14. Revocation after planning and before execution produces zero new effect.
15. Changed patient, destination, appointment, medication or payload invalidates prior clearance.
16. Timeout/unknown result remains UNKNOWN; no blind retry.
17. Booking/reschedule/cancel retries cannot duplicate effects.
18. HTTP/provider success without observed target state is not EffectVerified.
19. External manual drift is surfaced and not silently overwritten.
20. Raw transcript/audio/clinical text does not leak into generic receipts/logs.
21. TTS cannot speak a patient-specific consequential response that was not cleared for that recipient/context.
22. Shadow mode cannot call any external mutation path.
23. Same Health Function can use two provider protocols without changing REHT/domain authority semantics.
24. Health Pack contains no `authorize`, `permit`, `grant_authority` or alternate execution-boundary implementation.

# Definition of first usable parity release

The release is complete when a demonstrator can show, end-to-end:

### Clinician

```text
real recorded conversation
 -> transcript
 -> structured note draft
 -> clinician edits/approves exact draft
 -> governed commit
 -> independent read-back proving target record state
```

### Patient appointment

```text
real phone call
 -> conversational intake
 -> identity/relationship gate
 -> availability
 -> booking/reschedule/cancel request
 -> REHT
 -> external scheduling effect
 -> independent read-back
 -> spoken confirmation
```

### Prescription renewal

```text
real phone call
 -> renewal request captured
 -> routed to clinician
 -> clinician decision recorded
 -> patient notified
```

No autonomous prescribing claim is made by this release.

# Non-goals

- no new OS;
- no new authorization engine;
- no replacement for Kernel, Function Fabric, Workflow ISA, REHT, Operator, Veritas or BARO;
- no diagnosis engine;
- no model-owned clinical triage authority;
- no direct vendor logic in Health Pack;
- no claim of medical-grade accuracy or clinical safety from the existing generic voice stack without separate evidence;
- no storing raw PHI in generic Kernel/receipt surfaces merely for convenience.

# Direct execution sequence

1. Merge/adopt PR #7, then create `nsolland/valo-health-pack` and deliver HWO-1 with domain contracts, WorldPack, registered Functions and negative tests.
2. In parallel, deliver HWO-2 telephony/ASR/TTS bridge and HWO-6 provider-neutral health adapter test kit because their owned files do not need to overlap Health Pack core.
3. Integrate HWO-3 -> HWO-4 -> HWO-5 through the real Operator/REHT path, then apply HWO-7 privacy gates and HWO-8 shadow/live acceptance proof before claiming operational parity.

## Completion invariant

```text
The model can understand the conversation.
The Health Pack defines the valid health-workflow effect.
Current identity, relationship, purpose, state and professional authority constrain it.
REHT decides whether that exact effect may happen now.
The adapter performs only the cleared effect.
Veritas proves what the external health system actually holds.
```
