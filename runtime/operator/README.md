# valo-operator

**Operator v1** — a read-only governance API over the domain packs, with
deterministic actions that go through the real REHT boundary. v1.1 candidate.

```text
submit(OperatorRequest)   versioned contract -> registered Function -> full boundary
discover_functions()      read-only Function/capability catalog
kernel_views()            read-only projections (entities, authorities, rights, events)
operator_snapshot()       pack summaries (Case / WorkOrder) + kernel truth
act(function_id, inputs)  resolve + Function Fabric compile -> Workflow ISA
                          -> pack pre-execution admissibility -> fresh execution
                          context -> REHT -> binding -> Gateway -> Veritas -> BARO
                          -> Kernel
```

Stable API contracts (frozen pydantic, `extra="forbid"`, versioned `api_version`
`1.0`):
- `OperatorRequest` — `correlation_id`, `function_id`, `function_version`,
  `inputs`. The caller cannot override effect/risk/authority/postconditions/
  idempotency; unknown functions and unsupported api versions are rejected.
- `OperatorResult` — `correlation_id`, `status`, `decision`, `permit`, `reason`,
  `effect_verified`, `gateway_executions`, `errors`.

Discovery (`discover_functions`, `capabilities`,
`find_functions_by_capability`) is read-only and deterministic.

Session/identity boundary (`OperatorSession`): an explicit identity context —
`tenant_id`, `actor`, `identity_id`, `purpose_id`, `delegation_ref`,
`step_up` — validated against Kernel truth BEFORE anything runs. The session
never grants authority: it names the principal the boundary will evaluate. The
actor must match the registered Function's bound actor, a rights-impacting
Function requires `step_up=True`, and violations return a `REJECTED` result,
never a boundary decision.

Production adapters (`valo_operator.adapters`): real external integrations
over HTTP with the invariant **HTTP 200 from the send is NOT the effect**.
- `HttpGateway` — executes the action against an external HTTP endpoint with
  idempotency keys (replay never re-sends; the external system also dedups by
  id). Network failure -> success=False -> no Kernel transition.
- `HttpVeritas` — OBSERVES the external system's state endpoint after the
  send; `NOTIFY -> delivered`, `ISSUE_DECISION -> decision_issued`. Reality is
  queried, never assumed.
- `ExternalSystem` — an in-process HTTP system for tests, with a configurable
  landing state (DELIVERED/PENDING/FAILED) so "send succeeded but not
  delivered" is exercised.

Operational evidence: every submission records an `EvidenceEntry` in the
runtime's append-only `EvidenceLedger` — correlation_id, instance_id,
function_id, decision, permit, effect_verified, BARO outcome and the
operational receipts. Queryable via `runtime.evidence()`,
`runtime.evidence_by_correlation(cid)`, `runtime.audit(function_id, status)`.
`OperatorResult` carries `instance_id` + `receipts` (authorization, execution,
effect-verified) for the caller. A send that landed PENDING is recorded as
`baro_outcome="diverged"`.

Production Integration Program P0 (`tests/test_production_integration.py`): the
9 acceptance proofs run against TWO REAL standalone external services — the
notifier and the ledger, each its OWN process with its OWN state over HTTP.
No mock as the final effect point: the effect lives in the service process's
state and Veritas verifies it by reading that state back.

1. ALLOW -> actual external effect -> independently verified.
2. DENY -> zero external effect.
3. Revocation between plan and execution -> zero effect.
4. HTTP success without desired state -> NOT verified (BARO diverged).
5. Timeout/unknown outcome -> UNKNOWN, never synthetic success.
6. Retry/idempotency -> no double effect (external service dedups by id).
7. Changed action after permit -> different permit (invalid).
8. Full flow reconstructible from correlation_id + receipts.
9. The same Operator contract drives BOTH services with no adapter-side
   authorization (adapters are pure transport + observation).

Vendor neutrality (`test_vendor_neutral.py`): the SAME Operator chain drives
TWO different vendor protocols purely via configuration. `VendorConfig` +
`ConfiguredGateway`/`ConfiguredVeritas` absorb every vendor difference (auth
headers, idempotency-header names, paths, state fields, success states) — a
real Stripe/Twilio/ServiceNow endpoint is a config change, never a VALO
architecture change. The vendor-shaped standalone service ENFORCES the vendor
protocols (auth header required, idempotency header, vendor paths/fields), and
the same `submit()` contract drives the payments vendor (PAY) and the
messaging vendor (NOTIFY) with no adapter-side authorization.

Reference product demo (`examples/reference_demo.py`, tests in
`test_reference_demo.py`): the SAME Operator API drives BOTH domain flows
end-to-end to their terminal state — the Public flow (application ->
register -> review -> decision -> notify -> appeal deadline -> finalize ->
close) and the Trades flow (workorder -> register -> schedule -> reserve ->
dispatch -> execute -> invoice -> payment -> reconcile -> close), each with
evidence recorded per correlation_id.

Deployment surfaces over ONE `OperatorRuntime` (same authorization chain, no
change when you switch entry point):
- **Library** — `build_public_runtime()` / `build_trades_runtime()` then
  `runtime.submit(request, session)`.
- **Sidecar/service** — `ServiceHandler(runtime)` with JSON-able
  request/response dispatch (mount behind HTTP/gRPC/queue).
- **Gateway/API** — `Gateway(runtime)` HTTP adapter: `POST /submit`,
  `GET /discover`, `/capabilities`, `/views`, `/snapshot`.

Principles:
- **Read-only views.** The operator never mutates Kernel state; every
  projection is derived from the immutable snapshot the Kernel returns.
- **No free actions.** `act()` submits a REGISTERED Function by FunctionRef +
  typed inputs. Effect type, risk, authority requirement, requested-transition
  semantics, postconditions, idempotency policy and typed inputs/outputs all
  come from the Function Fabric contract — the caller can override none of
  them. Unknown function ids are rejected before anything runs.
- **No own authorization, no own state machine.** REHT is injected; the packs
  own their pre-execution domain admissibility.
- **Deterministic + correlated.** Same context + same action -> same outcome/
  permit; the REHT decision reported for an action is correlated to that
  workflow instance (never a stale decision from a reused REHT).

## AI Work OS convergence

Operator is also the canonical operational surface for the AI Work OS. The
adopted convergence loop is:

```text
Current State -> Ideal State -> Gap -> Discover/Build -> Operate
              -> Veritas/BARO verify -> Learn -> next proposal
```

Current State must come from fresh observable state; Ideal State must carry
verifiable acceptance criteria. Persistent memory is context/evidence only,
capability routing remains provider-neutral, high-impact judgment prefers a
different provider from execution when available, and learning re-enters via
the governed Factory loop rather than mutating live authority or policy.

See `docs/LIFEOS_WORK_OS_ADOPTION.md` for the canonical pattern adoption.
See `docs/ATLAS_RETAIL_WORK_OS_ADOPTION.md` for the canonical candidate-state,
field-ownership and verified multi-destination publication pattern.
See `docs/MEDIVOX_HEALTH_WORK_OS_ADOPTION.md` for the canonical health-workflow
pattern: candidate records/actions, exact effect decomposition and verified downstream effect.
See `docs/SWAN_GTM_SIGNAL_ACTION_ADOPTION.md` for the canonical GTM pattern:
provider-neutral signals become evidence and CandidateActions before registered, REHT-authorized and independently verified external effects.
See `docs/HELM_DECISION_SURFACE_ADOPTION.md` for the Operator/UI pattern:
one named action question per governance surface, explicit evidence provenance,
and producer/verifier separation without moving authority into the UI.

Depends on: frozen core v1.0.0 (kernel/ISA/FF), `valo-reht` (v1.1 candidate),
and both domain packs.
