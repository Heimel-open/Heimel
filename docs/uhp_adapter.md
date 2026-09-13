# UHP worker adapter

Status: adopted interoperability profile for external harness workers.

VALO treats Unified Harness Protocol (UHP) as a replaceable worker-transport contract, not as an authority or execution-governance layer.

## Boundary

Canonical flow:

`GovernedWorkspaceEnvelope -> UHP worker -> candidate/artifact evidence -> VALO conformance -> fresh state + authority evaluation -> REHT -> RACS -> PEP -> effect -> receipt`

The UHP adapter MUST NOT create a second effect path. A UHP server, HarnessRouter instance, configured harness, model, MCP server, tool policy, session or artifact cannot issue VALO clearance.

`completed` means only that the harness completed its task. It does not mean that any proposed action is authorized.

## Adopted UHP 2026-08-11 semantics

The adapter adopts:

- explicit `UHP-Version: 2026-08-11` negotiation and fail-closed version mismatch handling;
- `GET /v1/uhp` capability discovery;
- opaque harness `base` identifiers so Codex, Claude Code, Hermes and future runtimes remain replaceable;
- `POST /v1/responses` task projection and response/session correlation;
- deterministic `Idempotency-Key` generation and a requirement that governed workers advertise UHP idempotency;
- session continuation only when the server advertises session support;
- explicit model-substitution evidence; a substituted model requires downstream VALO model re-admission;
- cancellation as a separate lifecycle operation;
- artifact/session references and structured evidence correlation;
- structured task lifecycle states and error semantics as transport/runtime evidence.

## Explicit non-adoption

UHP conformance is not execution-governance conformance.

`disabledTools`, MCP configuration, skills, harness scope and UHP permission responses are useful runtime controls, but they are not VALO authority. Their presence does not prove hard enforcement across every harness runtime and they cannot replace fresh authority evaluation, REHT, RACS or the governed effect boundary.

The adapter therefore records tool-enforcement assurance as `UNVERIFIED_BY_UHP`.

## Effect isolation

A governed UHP task requires an `effect_isolation_ref` and `effect_isolation_digest`. This binds the worker projection to external assurance that the selected harness environment has no direct consequence-bearing effect route.

The reference adapter itself performs no network I/O and cannot execute external effects. Runtime deployment remains conformant only when consequence-bearing credentials and effectors are unavailable to the worker except through the governed VALO effect path.

## Worker output

UHP worker output is always `CANDIDATE_ONLY`.

Artifacts are recorded as `ATTACKER_INFLUENCED`, never authoritative state. Artifact identifiers are rejected if they contain path-traversal syntax. Artifact content must be admitted through the normal governed evidence/state boundary before it can influence consequence-bearing decisions.

Observed UHP tool calls are evidence, not authorization.

## Model substitution

If the actual UHP response model differs from the requested model, UHP must explicitly report the fallback and reason. The adapter marks `requires_model_readmission=true`.

Silent model substitution fails closed because downstream admissibility, provenance, cost and evaluation claims would otherwise refer to a model that did not run.

## Deterministic correlation

The VALO UHP request id binds:

- governed workspace digest;
- governed projection digest;
- worker id;
- harness id and descriptor digest;
- requested model;
- task input digest;
- instruction digest;
- continuation response id, if any;
- effect-isolation evidence digest.

The same governed work therefore produces the same request/idempotency identity; changed work or changed bindings produce a different identity.

## Protocol source

Profile: Unified Harness Protocol, normative version `2026-08-11`.

The protocol remains an external interoperability dependency. VALO owns the authority, conformance and effect-boundary semantics above it.
