# Build Order: Agent Ecosystem Pattern Adoption — 2026-08-07

Status: implemented

## Sources read

- Meta Muse Code: terminal-native long-horizon coding worker, parallel subagents, persistent activity/event history and resumable work.
- CopilotKit Channels SDK: normalize one agent runtime into collaboration channels such as Slack and Teams, including durable threads and native approval interactions.
- Shieldstral: small policy-adaptive text/multimodal safety classifier.
- Rippling AI Spend Console: attribute AI spend across providers and correlate it with organizational/business metrics.
- Annotate screen-recording-as-prompt pattern: use captured visual behavior and annotations as high-bandwidth work intake.

## Canonical adoption

External products are not new VALO layers. They are replaceable capability providers, instruments, transports, or design signals behind VALO-owned contracts.

### 1. Muse Code -> execution-worker provider pattern

Factory workers may be terminal-native, persistent and internally parallel. The provider still receives a bounded mission in an isolated worktree and must emit evidence. Persistent local logs are useful evidence, not self-attestation. Independent QC remains mandatory. A provider swap must not change authority or governance semantics.

`schemas/worker-provider-receipt.schema.json` binds provider identity/version, mission digest, append-only event-log digest, result digest, parallel-worker count and resume state. Provider activity has `authority_effect=none`.

### 2. CopilotKit Channels -> channel adapter pattern

Slack, Teams and later channels are transport surfaces. Channel identity, conversation state and approval controls are inputs/evidence. None of them grants execution authority. Consequence-bearing actions still bind an execution context and cross REHT immediately before execution. The implementation belongs in `nsolland/valo-gateway`.

### 3. Shieldstral -> VAIG policy-safety instrument pattern

A policy-adaptive classifier is a VAIG measurement source. Its model identity, policy identity and result become evidence. Missing measurement must never become 0 risk. The classifier may raise distrust or contribute to aggregation; it never authorizes an action. The implementation belongs in `nsolland/VAIG`.

### 4. Rippling AI Spend Console -> ACE economic observability

The useful pattern is not a vendor dashboard. It is the link from AI resource consumption to verified outcomes. `config/tokenomics-policy.json` now measures token/model cost together with human time, retries, rework, technical debt, cleanup, monitoring, opportunity cost and cancelled opportunity cost. Positive value includes time saved, faster outcomes, enabled opportunities and verified business outcomes.

AI spend without an outcome reference is cost telemetry, not ROI. `schemas/ace-economics-receipt.schema.json` makes that machine-enforceable: an ROI claim requires a non-empty outcome reference, while economics always has `authority_effect=none`.

### 5. Annotate -> multimodal work intake

Screen recordings, screenshots, video and timestamped annotations can enter the factory as structured work evidence through `schemas/work-intake-artifact.schema.json`. Every artifact is digest-bound and records expected versus observed behavior. Media may improve task specification; it never carries authority.

## Machine-readable anchors

- `config/ecosystem-adoptions.json`
- `config/tokenomics-policy.json` v1.1.0
- `schemas/worker-provider-receipt.schema.json`
- `schemas/ace-economics-receipt.schema.json`
- `schemas/work-intake-artifact.schema.json`
- `tests/test_ecosystem_adoptions.py`

## Non-negotiable boundary

No external agent, channel UI, classifier, spend metric or captured prompt can create authority. VAIG evaluates. REHT remains the final authorization boundary for consequence-bearing execution. Gateway enforces the cleared action. Receipts and outcome evidence establish what actually happened.
