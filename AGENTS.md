# AGENTS.md — valo-operator

## What this is

Operator v1: a thin governance API over the domain packs. It exposes read-only
views of Kernel truth and submits deterministic actions through the real REHT
boundary. No UI.

## Non-negotiable invariants

- **Read-only views.** The operator never writes Kernel state. Views are
  derived from the immutable snapshot `KernelEngine.state()` returns.
- **No free actions.** `act()` resolves a REGISTERED Function (FunctionRef +
  typed inputs) and compiles it through Function Fabric. Effect type, risk,
  authority, requested transition, postconditions, idempotency and typed
  inputs/outputs come from the registered Function contract — never from the
  operator caller. Unknown function ids are rejected. Callers cannot downgrade
  an effect, strip postconditions, or drop idempotency.
- **Every action runs the full boundary.** The compiled Function runs via the
  Workflow ISA runtime: pack pre-execution admissibility -> execution context
  -> REHT -> binding -> Gateway -> Veritas -> BARO -> Kernel event. No bypass.
- **Correlated decisions.** The REHT decision reported for an action is
  sliced from the decision log at the moment that instance started, so a
  reused REHT never yields a stale decision.
- **Stable, versioned public contracts.** `OperatorRequest` / `OperatorResult`
  are frozen pydantic with `extra="forbid"` and `api_version`. `submit()` is
  the frozen entry surface: it takes a versioned request and returns a
  versioned result tied to the caller's `correlation_id`. Unsupported
  `api_version` and unknown function ids are rejected before anything runs.
- **Session/identity boundary.** `OperatorSession` (tenant/actor/identity/
  purpose/delegation/step-up) is validated against Kernel truth before
  anything runs. The session never grants authority; violations return a
  REJECTED result. The session actor must match the registered Function's
  bound actor, and a rights-impacting Function requires `step_up=True`.
- **HTTP 200 is not the effect.** Production adapters separate the Gateway
  send (idempotency keys, receipts) from the Veritas observation of the
  external system's state. `HttpVeritas` queries reality; BARO compares the
  postcondition against observed state. A send that landed PENDING/FAILED
  diverges -> no EffectVerified, no Kernel transition.
- **Every submission is evidenced.** `OperatorResult` carries the workflow
  instance_id and operational receipts (authorization, execution external id,
  effect-verified receipt). The runtime records an append-only
  `EvidenceLedger` per correlation_id with BARO outcome; audit queries are
  read-only.
- **Vendor differences are configuration, never architecture.** The nine
  proofs follow the adapter unchanged. `VendorConfig` + `ConfiguredGateway`/
  `ConfiguredVeritas` absorb auth headers, idempotency-header names, paths,
  state fields and success states; the ACTION -> EFFECT-KEY mapping is the
  Function's semantics, not the vendor's. A real third-party endpoint is a
  config change.
- **Production integration = no mock as the final effect point.** The 9
  acceptance proofs run against two REAL standalone services (own process, own
  state, real HTTP). The adapters are pure transport + observation — they
  carry no authorization logic; the effect lives in the service's state and
  Veritas verifies it by reading it back.
- **One runtime, any surface.** `OperatorRuntime` binds a pack's registry +
  Kernel adapter + real REHT + Gateway/Veritas/BARO. Library, `ServiceHandler`
  (sidecar) and `Gateway` (HTTP) all expose the SAME runtime and therefore the
  SAME authorization chain — switching surface never changes the boundary.
- **Read-only discovery.** `discover_functions` / `capabilities` /
  `find_functions_by_capability` list the registered Function contract surface
  deterministically; they never mutate anything and never authorize.
- **No authorization logic here.** REHT is injected; the operator owns no
  authorize() code and no parallel state machine.
- **Deterministic.** Same context + same action -> same outcome; permit is
  bound to the exact action contract.

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
# install the six dependency anchors (kernel/ISA/FF frozen v1.0.0 + reht + packs)
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m compileall -q src tests
```
