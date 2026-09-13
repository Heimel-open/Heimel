# relAIon for Copilot+ PC — MVP

## Product promise

A non-technical owner of a Windows Copilot+ PC downloads one signed installer, approves the Windows permissions they choose, and the machine becomes a governed relAIon capability node.

Target experience: download -> install -> consent -> ready.

No command line, model selection, MCP configuration, API keys, or infrastructure knowledge is required.

## Boundary

relAIon does not replace Windows and does not bypass Windows security or consent. Windows remains the operating substrate. relAIon becomes the personal capability control plane above it. VALO is the mandatory consequence authorization boundary for every effect routed through relAIon.

## Installation contract

The installer MUST:

1. Verify supported Windows/Copilot+ PC prerequisites and hardware capabilities.
2. Install the signed relAIon application and local service/runtime components.
3. Detect CPU/GPU/NPU capability and select an admissible local inference route automatically.
4. Bootstrap a local model route when available; cloud inference is disabled by default.
5. Create local encrypted relAIon state and device identity.
6. Register supported relAIon capability surfaces/connectors with Windows where supported.
7. Start the VALO Windows capability adapter before enabling effectful capabilities.
8. Present human-readable, capability-specific permission requests. No blanket consent.
9. Run a self-test proving model inference, authorization gate, denied-effect containment, and receipt generation.
10. Mark the PC READY only after the self-test passes.

Any failed prerequisite or governance self-test MUST leave effectful capability routes disabled.

## First-run UX

### Screen 1 — This PC becomes your relAIon

Explain three properties only:
- Work can stay on this PC.
- relAIon asks before receiving new kinds of access.
- Actions are governed separately from access.

### Screen 2 — Choose access

Initial capability grants are explicit and individually reversible, for example:
- Documents
- Calendar
- Browser-assisted tasks
- Notifications

Default: minimum access. Local processing preferred.

### Screen 3 — Ready

Show:
- Local AI: READY / LIMITED / UNAVAILABLE
- relAIon control plane: READY
- Handlingsrett gate: ACTIVE
- Connected capabilities: N
- Remote processing: OFF by default

Then expose one primary interaction surface: Ask relAIon.

## Runtime architecture

User intent
-> relAIon orchestrator
-> capability discovery
-> normalized EffectRequest
-> VALO / REHT fresh commit-time authorization
-> ALLOW | DENY | ESCALATE
-> Windows App Action / contained MCP / local capability provider
-> effect
-> evidence receipt

There MUST NOT be a relAIon-controlled direct effect path around the authorization boundary.

## Local-first routing

Routing preference:

1. Local admissible capability/model on this device.
2. Trusted capability on another user-authorized relAIon node.
3. Explicitly authorized remote provider.
4. Otherwise fail/ask rather than silently exporting data.

Remote inference is a capability decision, not an implementation default.

## Consumer abstraction

The user never needs to know these implementation terms:
- Foundry Local
- Windows ML
- ONNX
- NPU/TOPS
- MCP
- ODR
- REHT/RACS

The product language is:
- On this PC
- On another device you trust
- Online service
- Ask first
- Allowed
- Blocked
- Needs your decision

## MVP capability set

The first pilot only needs enough capability to prove the product:

1. Local conversation/inference.
2. Read a user-approved document and answer from it.
3. Propose a write/update to a test document.
4. Route the write through the VALO Windows capability adapter.
5. Demonstrate ALLOW, DENY and ESCALATE without any direct bypass.
6. Produce a visible receipt: what was requested, what authority was used, what happened, and when.
7. Demonstrate offline operation for the local path.

## Definition of READY

A machine is a relAIon PC only when all are true:

- Device identity established.
- Local state protected.
- At least one inference route operational.
- Capability registry operational.
- VALO consequence gate operational.
- Negative test proves denied effects do not reach the provider.
- Receipt generation operational.
- User can revoke granted capability access.

Installation alone does not establish READY.

## Pilot success criterion

Give a factory-standard Copilot+ PC to a person with no technical competence.

Without terminal access or developer assistance, they must be able to:

1. Download relAIon.
2. Install it.
3. Understand and choose permissions.
4. Ask relAIon to perform a useful local task.
5. See relAIon execute an authorized effect.
6. See relAIon stop an unauthorized effect.
7. Disconnect the internet and continue a local task.

If this succeeds, the PC has been converted from a generic AI PC into a governed personal capability node.