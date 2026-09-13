# Governed Egress Protocol v1

## Decision

CrabTrap is adopted as an optional outbound HTTP/HTTPS transport adapter. Its static rules and LLM judge do not own authorization.

Factory OS owns the provider-neutral governed egress contract. CrabTrap, another proxy, an MCP gateway or a native transport may implement the connector without changing authority semantics.

## Runtime path

```text
Agent / worker
  -> CrabTrap-compatible transport
  -> exact request bytes + canonical metadata digest
  -> valo-egress-gate /v1/authorize
  -> governance broker
  -> VAIG evaluation
  -> REHT clearance
  -> RACS decision
  -> connector verifies request has not changed
  -> upstream execution
  -> bounded response buffer
  -> valo-egress-gate /v1/evaluate-response
  -> allow, redact or deny
  -> agent
  -> receipt chain
```

VAIG evaluates. REHT clears. RACS decides. The connector enforces.

## Authority boundary

1. A matched transport static `DENY` may stop a request early.
2. Static `ALLOW`, passthrough and LLM judge results never authorize forwarding.
3. VAIG, REHT and RACS artifacts must bind to the same canonical request digest.
4. Missing, unavailable, malformed or mismatched governance fails closed.
5. VAIG `FAIL` blocks execution.
6. `STEP_UP`, `DEFER`, `DENY` and `HALT` never forward.
7. `MODIFY` blocks the original request. A replacement must be submitted as a new governed request.
8. WebSocket upgrades are denied in v1 because subsequent frames cannot be governed.
9. Raw credentials, cookies and request bodies do not enter the governance broker. Only header names, body size and body digest are sent.
10. The connector recomputes the canonical digest immediately before forwarding. Any byte or metadata change blocks execution.
11. Upstream text responses must be fully inspected before delivery. Uninspectable encoded or oversized text fails closed.

## Contracts

- `valo.governed-egress.authorize.v1`: connector request for full governance
- `valo.governed-egress.governance-query.v1`: gate-to-broker request
- `valo.governed-egress.stage-query.v1`: broker-to-stage request
- `valo.governed-egress.request.v1`: fully assembled governance evaluation
- `valo.governed-egress.decision.v1`: request enforcement decision
- `valo.governed-egress.response.v1`: upstream response inspection request
- `valo.governed-egress.response-decision.v1`: response allow, redact or deny decision

Canonical schemas:

- `schemas/governed_egress_request.schema.json`
- `schemas/governed_egress_decision.schema.json`
- `schemas/governed_egress_response.schema.json`

## Request binding

The request fingerprint is SHA-256 over canonical JSON containing:

- upper-case HTTP method
- absolute HTTP(S) URL without embedded credentials
- sorted lower-case header names
- body SHA-256
- body size
- content type
- WebSocket flag

The Go connector stores the exact request bytes used to calculate this digest. `VerifyBeforeForward` reconstructs the snapshot immediately before network execution and blocks any mismatch.

## Gate and broker

`bin/valo-egress-gate` exposes:

- `POST /v1/authorize`: invoke the configured governance broker and return the final transport decision
- `POST /v1/evaluate`: validate already assembled VAIG, REHT and RACS artifacts
- `POST /v1/evaluate-response`: inspect an upstream response
- `GET /healthz`: local readiness
- CLI equivalents using `--authorize` and `--response`

The gate binds to loopback by default. A non-loopback bind requires `VALO_EGRESS_ALLOW_REMOTE=1`. Optional bearer protection uses `VALO_EGRESS_SHARED_TOKEN`.

`bin/valo-egress-governance-broker` executes three configured stages in order:

```text
VALO_EGRESS_VAIG_COMMAND
  -> VALO_EGRESS_REHT_COMMAND
  -> VALO_EGRESS_RACS_COMMAND
```

Each stage receives the canonical query and all prior artifacts. Every returned artifact must bind to the same request digest. Missing commands, timeouts, non-zero exit codes, invalid JSON and digest mismatches are terminal failures.

Configure the gate with:

```bash
export VALO_EGRESS_GOVERNANCE_COMMAND=./bin/valo-egress-governance-broker
export VALO_EGRESS_VAIG_COMMAND='<VAIG adapter command>'
export VALO_EGRESS_REHT_COMMAND='<REHT issuer command>'
export VALO_EGRESS_RACS_COMMAND='<RACS decision command>'
bin/valo-egress-gate --serve --bind 127.0.0.1 --port 8082
```

## CrabTrap connector

The production connector is implemented in `connectors/crabtrap/governed` and anchored to upstream `brexhq/CrabTrap@ac871ccc4460249f71cfc8b55ae4ba6130351b74`.

It provides:

- mapping of CrabTrap static and LLM outcomes to advisory transport signals
- exact request-byte snapshot and digest generation
- pre-forward authorization through `/v1/authorize`
- final mutation check immediately before `h.client.Do`
- bounded response buffering
- response inspection through `/v1/evaluate-response`
- deterministic header stripping and body redaction
- fail-closed handling for gate outages and invalid decisions

CrabTrap must run with passthrough fallback disabled. A native CrabTrap `ALLOW` is never sufficient to forward.

The exact insertion points and integration sequence are defined in `connectors/crabtrap/INTEGRATION.md`.

## Response inspection

`bin/valo-response-inspector` is local and deterministic. It does not call a model.

It returns:

- `ALLOW` for inspected content without a blocking signal
- `REDACT` for recognized secret material or sensitive response headers
- `DENY` for prompt-injection patterns, uninspected encoded text and text exceeding the configured inspection bound

Binary responses are not interpreted as instructions, but sensitive headers are still stripped. The default text inspection bound is 1 MiB and can be changed with `VALO_RESPONSE_MAX_TEXT_BYTES`.

## Conformance

Python tests cover request governance, stage brokering, digest binding, fail-closed behavior, response inspection, secret redaction and prompt-injection denial.

Go tests cover CrabTrap signal mapping, authorization payload privacy, exact-byte binding, mutation detection, response redaction, header stripping and blocked response delivery.

CI parses all schemas, compiles all Python executables, runs the Python suite, formats and tests the Go connector, and checks that privileged QC key material is not referenced.
