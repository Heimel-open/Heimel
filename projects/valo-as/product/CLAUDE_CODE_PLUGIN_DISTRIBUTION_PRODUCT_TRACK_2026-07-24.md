# Claude Code Plugin Distribution Product Track

Date: 2026-07-24
Status: Adopted product track
Owner: VALO / REHT product architecture

## Product thesis

Package the governed-execution stack as a provider-neutral developer product that can be installed first through Claude Code plugins and later distributed through MCP registries, IDE marketplaces, browser extensions and agent platforms.

The plugin is not a separate governance engine. It is a thin client and distribution surface over the existing Harness → VAIG → REHT → RACS → Receipt chain.

## Initial product

Working name: REHT for Claude Code

Primary outcome:

A developer can install one plugin and place governed checks immediately before consequential tool calls, code changes, deployments, publishing, data disclosure and other external actions.

## First plugin capabilities

- `/governance-check` — evaluate a proposed consequential action before execution
- `/shadow-run` — run the full chain without blocking execution
- `/receipt` — produce and inspect a proof-bearing execution receipt
- `/review-risk` — summarize authority, reversibility, exposure and required step-up
- `/policy-status` — show active mandate, constraints and policy version
- pre-tool-call hook — invoke REHT clearance before configured consequential tools
- post-action hook — bind observed outcome and evidence to the receipt
- MCP bridge — connect Claude Code to the provider-neutral VALO runtime

## Ecosystem scan — what successful plugins prove

Snapshot: Claude Plugin Hub, 2026-07-24.

The dominant products are not general governance platforms. They are installable controls placed directly inside the developer workflow.

### Relevant reference products

- `superpowers`: structured development lifecycle, TDD, debugging, code review, parallel execution and explicit verification checkpoints.
- `caveman`: aggressive context and token compression, including memory and review artifacts.
- `ecc`: broad skills, commands, hooks, security checks and multi-agent orchestration.
- `ponytail`: narrow enforcement of YAGNI, minimal changes and avoidance of speculative complexity.
- `claude-mem` and `mempalace`: persistent searchable memory across sessions.
- `claude-flow`: multi-agent coordination with persistent state.
- `claude-hud`: visible runtime state, tool activity, context health and agent progress.
- `Cadence`: file-backed execution state, one disciplined execution loop and atomic commits.
- `MetaSpace Membrane`: deny-by-default `PreToolUse` membrane, project-only writes, network allowlists and dangerous-command blocking.
- `headroom`: pre-Bash hooks that enforce repository and version-control conditions before tool execution.

### Cross-market consensus

The ecosystem has independently converged on six product patterns:

1. Controls must execute inside the active workflow, not in a separate governance portal.
2. Pre-tool hooks are the natural enforcement point for consequential agent actions.
3. Durable state must live outside the chat transcript and survive session resets.
4. Verification must be explicit before completion is claimed.
5. Users adopt narrow, understandable controls faster than opaque all-in-one systems.
6. Visible status and low-friction local installation are central to trust and adoption.

### Gap left open

Existing plugins enforce workflow discipline, code quality, local security boundaries, memory and agent coordination. They generally do not provide the complete chain required for governed execution:

- principal and mandate binding
- consequence-aware evaluation
- authority validation
- deterministic clearance before action
- step-up to an authorized human
- portable proof-bearing receipts
- separate clearance, execution and outcome evidence
- cross-client policy continuity

This is the product opening for REHT. The closest patterns validate the execution point and delivery mechanism, but they do not replace the Harness → VAIG → REHT → RACS → Receipt chain.

## Product changes adopted from the scan

- Make the pre-tool-call hook the primary product surface, not an optional secondary feature.
- Add file-backed session continuity for policy, mandate, pending step-up and receipt references.
- Add a compact runtime status line showing mode, active mandate, policy version and last decision.
- Keep the initial surface deliberately small: one hook, one status view and four core commands.
- Support atomic governed tasks so one proposal maps cleanly to one clearance and one receipt chain.
- Provide explicit verification checkpoints before the plugin may report a governed task as complete.
- Add deny-by-default project, network, shell and external-action policy packs.
- Preserve local-first operation and allow the remote runtime to be added without changing the plugin contract.
- Treat multi-agent orchestration as an upstream proposal source; no orchestrator receives execution authority.
- Avoid competing with TDD, memory or workflow plugins. Integrate with them and govern their consequential actions.

## Architectural boundaries

- Claude Code observes and proposes; it does not grant itself authority.
- The plugin never embeds independent authorization logic that can drift from REHT/RACS.
- VAIG evaluates evidence and uncertainty; REHT clears; RACS enforces the runtime decision.
- Human authority remains final where policy requires step-up.
- Missing runtime, malformed evidence or unavailable policy must fail closed for configured consequential actions.
- Shadow mode is the default onboarding mode.
- Policies, mandates and receipts remain portable and vendor-neutral.
- Memory is context, not authority.
- A successful test, review or workflow checkpoint is evidence, not clearance.
- A pre-tool hook may block or defer execution but may not manufacture authorization locally.

## Distribution sequence

1. GitHub repository and signed release artifacts
2. Claude Code plugin packaging and Claude Plugin Hub listing
3. MCP server and registry distribution
4. VS Code and compatible IDE extensions
5. Browser extension and desktop overlay integration
6. OpenAI, Gemini and other agent-client adapters

## Commercial packaging

- Community: local shadow mode, basic policies and receipt inspection
- Team: shared policies, approval routing, central receipts and dashboards
- Enterprise: self-hosted runtime, identity and IAM integration, custom policy packs, audit export and support

The Claude integration is a channel, not a separate product fork. Pricing and entitlements must map to the same runtime service used by other clients.

## Build order

### Track A — plugin shell

- create dedicated repository or package directory
- add manifest, commands, skills and hooks
- implement local configuration with all consequential tools disabled by default
- add a mock runtime adapter for deterministic demos
- add compact runtime status line
- add file-backed session continuity

### Track B — runtime bridge

- define provider-neutral MCP/API contract
- bind action proposal, principal, mandate, context and policy version
- return ALLOW, MODIFY, DEFER, DENY, STEP_UP or HALT
- preserve deterministic action and decision references
- expose a stable adapter contract for Claude Code, Codex and later clients

### Track C — receipts and evidence

- emit clearance receipt before execution
- emit separate execution/outcome receipt after action
- provide local receipt viewer and export
- ensure unavailable or malformed backends never become synthetic approval
- bind workflow checks, tests and reviews as evidence without treating them as authorization

### Track D — onboarding and distribution

- publish shadow-mode starter policy
- create installation and five-minute demo flow
- submit to Claude Plugin Hub
- add provenance, signing, permissions and security documentation
- measure install-to-first-shadow-run and shadow-to-enforced conversion
- publish integration examples for `superpowers`-style workflows and multi-agent orchestrators

## Initial acceptance gates

- installs without modifying existing repositories unexpectedly
- no configured consequential action crosses the boundary without a runtime decision
- shadow mode never blocks but records the decision that would have applied
- enforcement mode fails closed on missing clearance
- every executed governed action has a clearance reference and execution receipt
- plugin removal leaves user repositories and portable governance data intact
- session reset does not lose active policy, mandate or pending step-up state
- status view never exposes secrets or sensitive receipt payloads
- third-party workflow, memory and orchestration plugins cannot bypass the governed hook

## Strategic value

This product track turns the execution-governance chain into an installable developer product and creates a low-friction route into teams already using coding agents. Claude Plugin Hub is the first distribution channel, not an architectural dependency or exclusive platform.

The ecosystem already validates the delivery model: hooks, commands, persistent state and visible verification inside the developer workflow. REHT adds the missing authority, consequence, clearance and evidence chain at the exact point where proposed action becomes real.