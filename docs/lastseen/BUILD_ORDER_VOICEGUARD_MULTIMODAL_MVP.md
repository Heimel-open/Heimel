# Build Order: VoiceGuard Multimodal MVP

Status: BUILD ORDER — READY FOR IMPLEMENTATION
Owner: ChatGPT implementation worker
Repository: `nsolland/valo-edge`
Canonical base: `0e4a2fc055defbea9cb6543a2f86282e20d0296f`
Branch: `feat/voiceguard-multimodal-build-order`
Dependency: existing LastSeen camera alpha, LastSeen query surface, micro-REHT edge pattern, Veritas receipts, Aurora-Lens evidence admission adapter contract

## Goal

Build a narrow demo showing voice and camera as the first multimodal gate into a governed execution pipeline.

The MVP must prove that voice and camera are not trusted as execution authority. They produce identity, liveness, object, scene and context evidence. Execution remains governed by Aurora-Lens, VAIG, REHT, RACS, Gateway and Veritas.

Canonical pipeline:

```text
Human
  ↓
Voice + Camera
  ↓
Voice Identity Gate + Visual Context Gate
  ↓
Identity & Context Fusion
  ↓
Conversation State
  ↓
Intent Engine / Planner
  ↓
Aurora-Lens Evidence Admission
  ↓
VAIG Risk Evaluation
  ↓
REHT Execution Authorization
  ↓
RACS Deterministic Decision
  ↓
Gateway / Tool Adapter
  ↓
External System or Local Action
  ↓
Veritas Receipt
```

## Non-negotiable boundaries

- Voice is the first identity gate, not the authorization boundary.
- Camera is the first visual context gate, not the authorization boundary.
- REHT remains the only execution authorization boundary.
- RACS only expresses the deterministic decision.
- Gateway only executes an already-cleared action.
- Veritas records all attempts, blocks, step-ups and executions.
- Aurora-Lens may stop a flow before VAIG/REHT if evidence standing is insufficient.
- No cloud dependency is allowed for the local LastSeen path.
- No general face recognition or third-party person tracking in MVP.
- User/operator visual identity may be modelled only as an enrolled local liveness/confidence signal.
- Any uncertain identity, liveness, object, recipient, document or authority state must fail closed or step up.

## Build slices

### Slice 1 — Voice ingress contract

Add deterministic contracts for voice-originated instructions:

- `VoiceUtterance`
- `SpeakerEvidence`
- `VoiceLivenessEvidence`
- `VoiceSessionEvidence`
- `VoiceIntentCandidate`

Acceptance:

- A voice command can be represented without executing anything.
- Speaker confidence and liveness are evidence fields only.
- Low confidence or failed liveness cannot produce an executable action.
- Tests cover trusted voice, low-confidence voice, synthetic/spoof risk and broken session continuity.

### Slice 2 — Camera context fusion

Extend the existing LastSeen camera path into a generic visual context signal:

- object evidence
- scene evidence
- OCR/document evidence
- enrolled-operator liveness/confidence evidence
- frame/source provenance

Acceptance:

- The MVP can describe what the user is looking at.
- The MVP can attach visual evidence to an intent.
- Existing person exclusion and local crop safety remain intact.
- Visual evidence cannot authorize execution by itself.

### Slice 3 — Identity & context fusion

Create a fusion layer that combines:

- voice identity confidence
- voice liveness
- trusted device/session continuity
- visual context
- LastSeen object memory
- optional enrolled-operator liveness/confidence

Acceptance:

- Fusion returns an evidence package, not an authorization decision.
- Conflicting voice/camera/session evidence returns `INSUFFICIENT_EVIDENCE` or `STEP_UP_REQUIRED`.
- All fusion outputs include provenance and deterministic replay data.

### Slice 4 — Aurora-Lens adapter

Add a thin adapter boundary for evidence standing before VAIG:

- `ADMIT`
- `NON_ADMIT`
- `INSUFFICIENT_EVIDENCE`
- contradiction list
- unresolved references
- missing provenance

Acceptance:

- A document/contract flow can stop before VAIG/REHT if Aurora-Lens rejects evidential standing.
- REHT is not bypassed when Aurora-Lens admits the evidence.
- Tests cover missing attachment, ambiguous customer, unresolved document reference and clean admissible evidence.

### Slice 5 — Governed action scenarios

Implement four deterministic demo scenarios:

1. LastSeen query
   - User asks: `Where are my glasses?`
   - Output: local answer and observation/query receipt.
   - No REHT execution clearance needed unless an external action is requested.

2. Low-risk business action
   - User says: `Send the contract to Acme.`
   - Camera/OCR identifies contract context.
   - Aurora admits evidence.
   - VAIG risk is low.
   - REHT clears.
   - RACS returns `ALLOW`.
   - Gateway simulates send.
   - Veritas records receipt.

3. High-risk financial action
   - User says: `Transfer five million to the new account.`
   - Identity may be high-confidence.
   - VAIG marks high risk.
   - REHT requires step-up.
   - RACS returns `STEP_UP`.
   - Gateway does not execute.
   - Veritas records blocked attempt and step-up requirement.

4. Destructive action
   - User says: `Delete all customer data.`
   - VAIG marks critical/destructive risk.
   - REHT denies.
   - RACS returns `DENY`.
   - Gateway does not execute.
   - Veritas records denial.

Acceptance:

- Each scenario has replayable fixtures.
- Each scenario produces a receipt chain.
- No scenario calls a real external system.
- The demo clearly shows where the action stopped or why it executed.

### Slice 6 — Demo UI / timeline

Build a local UI or CLI timeline that renders the gate sequence:

```text
Voice Identity
Camera Context
Fusion
Aurora-Lens
VAIG
REHT
RACS
Gateway
Veritas
```

Acceptance:

- `ALLOW`, `STEP_UP`, `DENY` and `INSUFFICIENT_EVIDENCE` are visually distinct.
- The UI shows exact reason and gate for each stop.
- The demo can be run locally without real microphone, camera, cloud API or external account.
- Optional live microphone/camera can be added later behind the same contracts.

## Owned files

Expected new or changed files:

- `src/valo_edge/voiceguard/contracts.py`
- `src/valo_edge/voiceguard/fusion.py`
- `src/valo_edge/voiceguard/aurora_adapter.py`
- `src/valo_edge/voiceguard/scenarios.py`
- `src/valo_edge/voiceguard/timeline.py`
- `src/valo_edge/voiceguard/cli.py`
- `tests/test_voiceguard_contracts.py`
- `tests/test_voiceguard_fusion.py`
- `tests/test_voiceguard_aurora_adapter.py`
- `tests/test_voiceguard_scenarios.py`
- `examples/voiceguard-multimodal/**`
- `docs/lastseen/BUILD_ORDER_VOICEGUARD_MULTIMODAL_MVP.md`
- `README.md`
- `pyproject.toml`

## Demo script

```text
1. "Hey VALO."
   → Voice identity evidence: high confidence, live speaker, trusted session.

2. "Where are my glasses?"
   → LastSeen answers from local visual memory.
   → Veritas records query/observation receipt.

3. "Send this contract to Acme."
   → Camera/OCR attaches document context.
   → Aurora-Lens admits evidence.
   → VAIG marks low risk.
   → REHT clears.
   → RACS ALLOW.
   → Gateway simulates send.
   → Veritas signs receipt.

4. "Transfer five million to the new account."
   → Identity is still high-confidence.
   → VAIG marks high risk.
   → REHT requires step-up.
   → Gateway blocked.
   → Veritas records step-up receipt.

5. "Delete all customer data."
   → VAIG marks destructive action.
   → REHT denies.
   → Gateway blocked.
   → Veritas records denial receipt.
```

## Verification gate

Required before PR is ready:

- full unit test suite green
- focused voiceguard test suite green
- deterministic replay for all demo scenarios
- no real external system calls
- no cloud-only dependency
- no person tracking beyond explicit local enrolled-operator liveness/confidence signal
- existing LastSeen camera safety tests still green
- receipts generated for allow, step-up, deny and insufficient evidence

## Explicit non-goals

- production voice biometric authentication
- production face recognition
- persistent third-party person tracking
- live bank, email, CRM or ERP integration
- cloud model dependency
- replacing REHT with voice, camera, Aurora-Lens, VAIG or RACS
- changing VALO layer identity
