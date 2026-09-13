# Google Factory Model / Harness Engineering adoption

Status: adopted external validation
Date: 2026-08-15
Owner: VALO Factory
Source: Google, *The New SDLC With Vibe Coding* (May 2026), Addy Osmani, Shubham Saboo, Sokratis Kartakis
Dependency effect: none

## Decision

VALO adopts the verified control implications of Google's Factory Model and
Harness Engineering as reinforcement of the existing VALO Software Factory and
governed-workspace architecture.

This adoption does not create a new architecture layer and does not introduce a
Google runtime dependency.

The core distinction is:

```text
Factory Model       = build the system that produces software
Harness Engineering = engineer the machinery surrounding the worker/model
VALO governance     = decide whether a specific consequence-bearing action may occur now
```

The harness is therefore an implementation pattern inside a governed workspace.
It is not an authority source and it does not replace the VALO execution-governance
boundary.

## External evidence adopted

The source describes the developer's primary output as the system that produces
code rather than code itself. That system combines specifications/context,
agents, tests and quality gates, feedback loops and guardrails.

The source describes the harness around a model as including, in practical
terms:

- instructions and rule files;
- tools, MCP servers and APIs;
- sandboxes and execution environments;
- orchestration and specialist hand-offs;
- guardrails and deterministic hooks;
- evals and testing;
- observability and tracing;
- deployment/runtime configuration and scaling;
- session and memory state.

VALO adopts this as the implementation vocabulary for worker execution inside a
governed workspace.

## Canonical VALO placement

The Factory/Harness pattern sits inside the existing governed path:

```text
Kernel authoritative state
  -> governed workspace / harness
  -> worker
  -> conformance return
  -> fresh state + Authority State
  -> reht
  -> RACS
  -> PEP / governed effect path
  -> execution receipt
  -> Veritas
```

The worker may be a coding agent, model, deterministic tool, specialist agent or
other replaceable implementation worker. Harness choice and model/provider
choice are operational decisions only.

`authority_effect = none`

A harness may constrain what a worker can see or call. It may sandbox execution,
run tests, route feedback, apply hooks and collect traces. None of those facts can
create, expand, revive or substitute for current execution authority.

## Factory contract

The Factory should optimize the system that produces correct output, not raw
code-generation volume.

Canonical factory flow:

```text
specification + governed context
  -> bounded mission
  -> governed workspace / harness
  -> worker execution
  -> deterministic tests + evals
  -> feedback / correction loop
  -> independent conformance return
  -> governed delivery / effect boundary
  -> evidence and outcome verification
```

The developer/operator role therefore moves toward specification, architecture,
constraint design, evaluation, review and exception judgment.

## The 80% problem

VALO adopts the source's "80% problem" as a Software Factory design assumption:
agents can generate the obvious majority of a well-specified implementation very
quickly, while the residual risk concentrates in edge cases, error handling,
integration points, ambiguous requirements, business assumptions and subtle
correctness failures.

The high-risk tail is dangerous because generated code can look plausible and
may pass shallow tests.

Therefore:

```text
raw generation speed != correct completion
```

Factory success is bounded by correct completion: the work must close correctly
within mandate, tests, evals, conformance and governance. Correct stop, defer,
step-up or rejection is preferable to unsupported completion.

## Tests, evals and evidence

Tests remain the contract for deterministic behavior. Evals cover non-deterministic
quality and trajectory properties that deterministic tests cannot fully express.

VALO narrows trajectory evidence to externally observable facts:

- tool calls and tool results;
- state transitions;
- retrieved inputs with provenance;
- test and eval results;
- sandbox/runtime events;
- conformance artifacts;
- execution decisions and receipts.

Hidden chain-of-thought, private reasoning, filler tokens, self-reported rationale
or confidence are non-authoritative telemetry. They cannot satisfy provenance,
evidence, admissibility, mandate, approval or execution authority.

## Context engineering

VALO adopts context engineering as both an engineering control and an economic
control.

Prefer dense, governed, task-relevant context over indiscriminate static context.
The workspace should distinguish:

- static context that must always be present because it defines stable role,
  boundaries or hard rules;
- dynamic context loaded only when needed through skills, retrieval and tools.

Context is input to the worker, not truth or authority by possession. Retrieved
or remembered material must preserve provenance/freshness where it can influence
consequence-bearing decisions.

Skills are portable procedural context. They may improve capability and token
efficiency, but they carry no governance authority.

## Intelligent model routing

VALO adopts intelligent model routing as a Factory/render-broker optimization:

- use frontier models where ambiguity, architecture or difficult judgment
  justifies the cost;
- use smaller/faster/cheaper models for bounded lower-complexity work where the
  required quality can be demonstrated;
- keep routing independent from authority, admissibility and effect policy.

Canonical rule:

```text
MODEL_ROUTING_NOT_POLICY
```

A cheaper or stronger model cannot weaken conformance, evidence, current
authority or governed-effect requirements.

## Production substrate

Persistent memory, scoped permissions, eval coverage, observability, CI gates,
sandboxing, traces and zero-trust development practices are required production
substrate for serious agents.

They are necessary but insufficient for execution governance.

A production harness still cannot answer by itself whether an exact action is
currently authorized. Consequence-bearing execution remains subject to fresh
state/authority, reht, deterministic RACS decisioning, the bounded PEP/effect
path, receipts and Veritas outcome evidence.

## Invariants

`FACTORY_OUTPUT_IS_SYSTEM`
The primary Factory asset is the repeatable system that turns governed intent
into verified output, not an individual generated code artifact.

`HARNESS_INSIDE_GOVERNED_WORKSPACE`
Harness machinery operates within the bounded workspace contract; it does not
sit above governance.

`HARNESS_NO_AUTHORITY`
Instructions, hooks, sandboxes, approvals, tools, memory, model identity or
successful harness completion cannot create execution authority.

`CONTEXT_NOT_AUTHORITY`
Context, memory, retrieved documents, skills and examples may inform work but
cannot manufacture mandate, admissibility or permission.

`OBSERVABLE_TRAJECTORY_ONLY`
Only externally observable actions/results may be used as trajectory evidence.
Hidden reasoning is never authoritative evidence.

`CORRECT_COMPLETION_OVER_RAW_SPEED`
The Factory optimizes for correctly closed work within contract, not maximum
code/output volume or minimum latency.

`MODEL_ROUTING_NOT_POLICY`
Model selection and routing optimize cost/capability only and cannot weaken any
governance requirement.

`PRODUCTION_SUBSTRATE_REQUIRED`
Production workers require engineered context, tests/evals, scoped capabilities,
observability and isolation appropriate to their risk.

`GOVERNED_EFFECT_PATH`
No harness, worker, tool, model or orchestration path may bypass fresh authority
and the canonical governed effect path for consequence-bearing execution.

## Relationship to existing Factory harnesses

Existing adapters such as `jcode`, Claude Code project surfaces, native headless
workers and other replaceable harnesses remain concrete implementations under
this model.

See `docs/architecture/jcode-harness-adoption.md` for the existing explicit
boundary: harness choice determines how the worker runs and has no authority
effect.

## Market interpretation

The source's closing direction is treated as external validation that software
generation is becoming increasingly commoditized while durable engineering value
moves toward verification, judgment, direction and the systems surrounding
generation.

VALO extends that convergence one control layer further: governed state, current
authority, deterministic execution clearance, a single bounded effect path and
verifiable outcomes.

External Factory/Harness terminology is evidence and interoperability language.
VALO execution-governance semantics remain canonical.
