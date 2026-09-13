# Governed A2A Connector

## Decision

A2A 1.0 is a first-class connector protocol for agent-to-agent discovery, messages, tasks and artifacts. A2A is transport and interaction semantics; it is not an authority source.

> A2A transports collaboration and delegation. Enterprise Mandate OS determines whether that delegation is legitimate and whether any resulting action may execute.

## Standards anchor

The connector is anchored to A2A specification `1.0.0`, wire header `A2A-Version: 1.0`, extension header `A2A-Extensions`, Agent Cards and the standard HTTP+JSON task/message surface. The production adapter implements HTTP+JSON for `SEND_MESSAGE`, `GET_TASK`, `LIST_TASKS` and `CANCEL_TASK`.

Streaming/SSE, JSON-RPC and gRPC are not silently downgraded. They fail closed until separate governed bindings are implemented.

## Authority boundary

A2A owns discovery, declared capabilities, protocol negotiation, message/task state and artifact transport. It does not establish the enterprise principal, legitimate delegation, target admissibility, revocation state, permission for the exact payload, or permission to execute a returned artifact.

`VAIG evaluates. REHT clears. RACS decides. The A2A connector transports and enforces the resulting boundary.`

## Runtime path

```text
Human / enterprise principal
  -> principal binding and bounded authority grant
  -> source agent
  -> live Agent Card fetch and trust verification
  -> MAL + authority + delegation + revocation check
  -> exact A2A payload preparation and digest
  -> Mandate Envelope
  -> VAIG -> REHT -> RACS
  -> last-moment payload/card binding check
  -> wire-dispatch receipt
  -> HTTP+JSON A2A operation
  -> bounded response and artifact inspection
  -> hash-chained receipt
  -> new REHT check before any local consequence
```

## Implemented contracts

- `valo.a2a.mandate-envelope.v1`
- `valo.a2a.client-request.v1`
- `valo.a2a.client-result.v1`
- `valo.a2a.receipt.v1`
- extension URI `urn:valo:a2a:mandate-envelope:v1`

Reference components:

- `bin/valo-a2a-envelope`
- `bin/valo-a2a-client`
- `connectors/a2a/client.py` — protocol implementation
- `connectors/a2a/production.py` — hardened production surface
- `schemas/a2a_mandate_envelope.schema.json`
- `schemas/a2a_client_request.schema.json`
- `schemas/a2a_receipt.schema.json`

## Exact action binding

The cleared action digest includes principal, source and target agent, Agent Card digest, selected interface, trust basis, MAL profile, authority grant, delegation-chain digest, purpose, scope, constraints, expiry, revocation registry, operation and exact A2A payload digest.

The production client additionally requires semantic agreement for tenant, message ID and task ID. The client prepares the actual wire representation before governance. `--prepare` returns the deterministic payload and digest. The final execute path recomputes the digest directly before network transmission. Mutation after clearance is denied.

`MODIFY` never transmits the original. A replacement requires a new payload, digest, envelope and governance chain.

## Agent Card trust and drift

Before each operation the client:

1. fetches the credential-free HTTPS Agent Card without redirects
2. bounds and parses the card
3. computes its exact canonical digest
4. verifies the cleared HTTP+JSON 1.0 interface and tenant
5. verifies signed-card evidence through an external verifier, or checks a curated registry
6. denies any digest or interface drift after clearance
7. writes selection or drift-denial receipts

Private/non-global addresses are denied by default. Explicit internal deployments may enable them through configuration.

An Agent Card is evidence, not authority. Possession of an endpoint or token creates no mandate.

## Authority, delegation and revocation

The production client requires an external fail-closed checker through `VALO_A2A_AUTHORITY_CHECK_COMMAND`. Its positive result must bind:

- principal and source agent
- target agent
- authority grant
- delegation-chain digest
- purpose
- revocation registry
- MAL profile
- exact action digest

The checker owns current grant state, scope/constraint narrowing, expiry and revocation semantics. A missing, unavailable, malformed or mismatched checker result prevents transmission.

## Transport enforcement

The client sends:

- `A2A-Version: 1.0`
- `A2A-Extensions: urn:valo:a2a:mandate-envelope:v1`
- a non-secret mandate reference bound to envelope and action digest

Authentication tokens are runtime secrets only. They do not enter the client request contract or receipts.

Supported HTTP+JSON routes:

```text
POST /message:send
GET  /tasks/{id}
GET  /tasks
POST /tasks/{id}:cancel
```

Redirects, protocol drift, oversized responses, unexpected content types and unbound payload changes fail closed. Immediately before I/O, the production surface emits a wire-dispatch receipt bound to method, URL, public header values, credential-presence flag and exact body digest. Credential values are excluded.

## Task and artifact governance

A2A task state is communication state, not governance state. `TASK_STATE_COMPLETED` does not authorize local execution.

Returned JSON is bounded by the stricter of runtime configuration and the envelope-bound artifact limit, then inspected for:

- prompt-injection instructions
- recognizable secret material
- unsafe `url` or `uri` values
- artifact size and digest
- task-state transitions
- preserved original response and provenance

Unsafe responses are denied and receipted. Every successful client result sets `local_execution_authorized: false`. Any consequence triggered by an artifact requires a new REHT decision over the local action.

## Receipts

The default runtime requires `VALO_A2A_RECEIPT_LOG`. Receipts are append-only JSONL, fsynced and hash chained. Events cover Agent Card selection/drift, authority verification, outbound authorization, exact wire dispatch, response inspection/denial, task/operation completion and transmission denial.

Receipts contain digests and evidence identifiers, not bearer tokens or raw credentials.

## Runtime configuration

See `config/a2a_connector.yaml.example` and `connectors/a2a/README.md`.

Production enablement requires actual authority/revocation/MAL checking and either signed-card verification or a curated registry. These are separate authority dependencies by design; the transport adapter cannot synthesize them.

## Status

- protocol and authority boundary: implemented
- mandate schema and validator: implemented
- HTTP+JSON non-streaming client: implemented
- hardened production surface: implemented and exported
- live Agent Card trust and drift control: implemented
- authority/delegation/revocation/MAL port: implemented, external checker required
- task/artifact inspection and hash-chained receipts: implemented
- streaming/SSE: fail-closed, not implemented
- JSON-RPC and gRPC: not implemented
- shadow deployment: ready when runtime checkers and secrets are configured
