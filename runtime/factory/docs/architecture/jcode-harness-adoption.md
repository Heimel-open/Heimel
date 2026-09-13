# jcode harness adoption

Status: adopted optional harness
Date: 2026-08-09
Owner: VALO Factory
Upstream reference: `1jehuang/jcode@dd8755f7e71f0673911d481b625b8a559c81a8b6` (`v0.71.1`)

## Decision

jcode is adopted as a replaceable coding-agent harness under VALO Factory.
It is not a VALO authority layer, not a model/provider identity, and not a new
architecture layer.

The Factory keeps harness and model/provider selection separate:

```text
BuildOrder / workflow primitive
  -> HeadlessWorkflowHarness
       -> harness_id: native | jcode
       -> provider_id: openai_codex | anthropic_claude_code |
                       google_antigravity | github_copilot
  -> isolated worker workspace/worktree
  -> provider/harness runtime
  -> deterministic tests
  -> independent Reviewer/QC
  -> merge candidate
```

For consequence-bearing runtime actions, the normal VALO boundary remains:

```text
VAIG -> REHT -> RACS -> external enforcement -> Veritas
```

Harness choice has `authority_effect = none`.

## Why jcode fits

The useful upstream properties are:

- low-overhead multi-session operation;
- provider routing across several coding/model providers;
- non-interactive JSON/NDJSON wrapper surfaces;
- parallel-agent operation;
- child-agent spawning and coordinator/worker patterns;
- file-change awareness across concurrent sessions;
- direct and broadcast agent messaging;
- persistent memory and session retrieval;
- SDK/wrapper surfaces suitable for automation.

The upstream project documents the wrapper command:

```text
jcode --quiet --no-update --no-selfdev run --json <prompt>
```

VALO additionally binds an explicit provider identity. Current mapping:

```text
openai_codex          -> jcode provider openai
anthropic_claude_code -> jcode provider claude
google_antigravity    -> jcode provider antigravity
github_copilot        -> jcode provider copilot
```

The VALO plan therefore uses:

```text
jcode --quiet --no-update --no-selfdev --provider <mapped-provider> run --json <prompt>
```

The prompt is represented by a digest in the Factory plan/receipt surface; raw
prompt content is not persisted there.

## Boundary against jcode safety semantics

jcode's own safety system is an upstream product feature, not the VALO
authorization contract. In the referenced upstream design it distinguishes
between automatically allowed actions and actions requiring user permission.
That model does not replace REHT and does not create a VALO permit.

VALO rules:

- jcode permission/approval state is at most evidence;
- jcode cannot grant, expand or revive mandate;
- REHT remains the final authorization boundary for consequence-bearing action;
- provider/harness completion is not proof that the intended outcome occurred;
- Veritas records external effects and BARO/other verification may evaluate the
  observed postcondition.

## Self-development

Self-development is disabled for jcode inside VALO Factory.

Every wrapper plan must contain:

```text
--no-selfdev
```

A harness may not autonomously modify its own control path, VALO governance
code, REHT semantics, RACS contracts, reviewer rules or promotion policy.
Changes to those surfaces must enter the normal BuildOrder -> isolated Writer ->
tests -> independent QC -> merge-candidate path.

## Isolation and ownership

jcode workers inherit the same Factory requirements as any other worker:

- one isolated workspace/worktree per worker mission;
- explicit repository and canonical base SHA;
- explicit branch and claim/owner;
- explicit owned files;
- bounded mission and capability set;
- no writer self-attestation;
- independent QC before promotion;
- exact artifact/test/commit evidence.

Persistent jcode memory is context only. It never becomes mandate, truth or
execution clearance and must yield to current code, tests, policy, receipts and
freshness state.

## Governed swarm runtime

jcode's swarm behavior is adopted as an optional Factory runtime pattern, not as
an authority model. A coordinator may spawn child workers only through an
explicit bounded delegation contract.

```text
Factory claim / parent mission
  -> coordinator
       -> child mission A + owned files A + bounded capabilities
       -> child mission B + owned files B + bounded capabilities
       -> collision check before parallel writes
       -> coordination messages / memory as context only
  -> deterministic tests
  -> independent Reviewer/QC
  -> promotion candidate
  -> fresh reht clearance for consequence-bearing execution
  -> Veritas evidence
```

Canonical swarm rules:

- child worker identity must be distinct from the parent;
- every child receives an explicit mission and owned-file set;
- child owned files must be a subset of the parent's active claim;
- parallel child file sets must not overlap; overlap fails closed before writes;
- child workers do not inherit parent authority, merge rights, deployment rights
  or governance-modification rights;
- authority, reht, RACS, governance, merge, deploy and external-execution
  capabilities cannot be delegated through the swarm contract;
- direct/broadcast agent messages are coordination evidence only and cannot
  create mandate;
- persistent memory must carry provenance and freshness references and remains
  `context_only`;
- self-development remains disabled for every child worker;
- any consequence-bearing child action requires fresh reht clearance at the
  actual execution boundary.

The Factory implementation for these invariants lives in
`lib/jcode_swarm_runtime.py`. It plans and validates delegation/coordination
metadata only. It does not execute agents or authorize effects.

## Read-only gate

The referenced jcode wrapper guide documents stable non-interactive execution,
but does not provide a simple provider-neutral read-only wrapper flag equivalent
to the Factory's existing Codex/Claude/Copilot read-only profiles.

Therefore the jcode harness adapter currently fails closed for
`execution_mode=read_only` rather than claiming an unenforced restriction.
`workspace_write` is the only planned jcode mode until a documented read-only
contract is conformance-tested.

This does not block independent review: Reviewer/QC can continue to use the
existing native read-only provider adapters.

## Canonical invariant

```text
Harness chooses how the worker runs.
Provider identifies which model/runtime serves the worker.
Swarm delegation chooses bounded parallel work, never authority.
Neither parent nor harness may grant execution authority to a child.
REHT decides whether a consequential action may happen now.
Veritas proves what actually happened.
```
