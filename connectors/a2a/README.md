# Governed A2A production client

`connectors/a2a/client.py` provides the protocol implementation. `connectors/a2a/production.py` is the hardened production surface used by the package export and `bin/valo-a2a-client`.

The client transports only an already governed and exact-digest-bound A2A 1.0 HTTP+JSON operation.

## Supported operations

- `SEND_MESSAGE`
- `GET_TASK`
- `LIST_TASKS`
- `CANCEL_TASK`

Streaming/SSE, JSON-RPC and gRPC fail closed.

## Two-phase use

Prepare the exact wire payload before VAIG/REHT/RACS:

```bash
bin/valo-a2a-client --prepare < client-request.json
```

Place the returned payload digest in the Mandate Envelope, obtain governance artifacts bound to its action digest, then execute:

```bash
export VALO_A2A_RECEIPT_LOG=/var/lib/valo/receipts/a2a.jsonl
export VALO_A2A_AUTHORITY_CHECK_COMMAND='<checker command>'
export VALO_A2A_AGENT_CARD_VERIFY_COMMAND='<signature verifier command>'
bin/valo-a2a-client < governed-client-request.json
```

The execute path fetches and verifies the live Agent Card, validates current authority/delegation/revocation/MAL state, checks the exact payload again, transmits without redirects, inspects the response and emits hash-chained receipts.

## External checker contract

`VALO_A2A_AUTHORITY_CHECK_COMMAND` receives `valo.a2a.authority-check.v1`. A positive result must bind all of:

- principal, source agent and target agent
- authority grant and delegation chain
- purpose
- revocation registry
- MAL profile
- exact action digest

Any missing or mismatched field denies transmission.

`VALO_A2A_AGENT_CARD_VERIFY_COMMAND` receives `valo.a2a.agent-card-verify.v1` and must return a digest-bound `verified: true` result for `SIGNED_AGENT_CARD` trust.

A curated registry may be used through `VALO_A2A_CURATED_REGISTRY`. Direct configuration is disabled unless explicitly enabled and is not the default production trust basis.

## Security invariants

- credential-free HTTPS URLs only
- no redirects
- private networks denied by default
- exact Agent Card, tenant, message/task ID and payload digest binding
- wire receipt written immediately before I/O, without recording credentials
- RACS `ALLOW` required
- `MODIFY` requires resubmission
- response size cannot exceed the envelope-bound artifact limit
- prompt injection, secret material and unsafe `url`/`uri` values are denied and receipted
- A2A completion never grants local execution
- artifacts remain untrusted until a new local REHT check
- authentication tokens never enter contracts or receipts
