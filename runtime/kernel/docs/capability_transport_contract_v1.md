# Capability Transport Contract v1

## Purpose

VALO adopts the useful production-API pattern behind FastAPI/OpenAPI without making FastAPI, HTTP, OpenAPI, or any transport framework part of Kernel authority semantics.

The pattern is:

```text
canonical typed contract
  -> deterministic transport projection
  -> generated machine-readable API schema
  -> generated documentation / SDKs / contract tests
```

The canonical typed contract is the source of truth. Generated transport artifacts are projections.

## Boundary

A transport surface may:
- parse and validate requests against declared schemas
- serialize declared responses
- publish machine-readable schemas such as OpenAPI
- generate SDKs and documentation from those schemas
- enforce transport-local concerns such as request size, protocol framing, streaming, rate limits and connection lifecycle

A transport surface may not:
- create identity, authority, delegation, purpose, rights, standing or clearance
- reinterpret canonical Kernel contracts
- convert successful validation into authorization
- mint a consequence-bearing execution binding
- bypass fresh REHT authorization
- expose a direct effect path

Transport validity means only that a message conforms to the declared transport contract.

## Canonical flow

```text
external caller
  -> transport request validation
  -> canonical VALO input contract
  -> Kernel admission / governed state
  -> Governed Workspace / conformance
  -> sealed exact-action binding
  -> fresh REHT authorization
  -> RACS decision
  -> Gateway / PEP
  -> external effect
  -> Veritas evidence
```

`HTTP 2xx`, successful Pydantic validation, a valid API token, an OpenAPI-conformant request, or a successful model response creates no authority to act.

## Contract-as-code rule

For every public or internal capability route, request and response shapes SHOULD be derived from canonical typed contracts or deterministic projections of them.

The following are generated artifacts and MUST NOT become independent sources of semantic truth:
- OpenAPI documents
- Swagger/ReDoc-style documentation
- generated client SDKs
- JSON Schema exports
- example payloads
- contract-test fixtures

If a generated artifact differs from the canonical contract, the canonical contract wins and the generated artifact must be regenerated.

## Separate schemas by responsibility

Transport request, canonical state/admission, execution binding and transport response are distinct responsibilities and SHOULD remain distinct schemas even when fields overlap.

This prevents:
- caller-controlled fields from entering authoritative state by structural accident
- internal fields from leaking through response serialization
- transport concerns from contaminating Kernel contracts
- authorization evidence from being accepted merely because it is syntactically valid

## Capability route semantics

A capability route describes how a caller can address a bounded capability. It does not describe whether the caller is entitled to produce a real-world effect.

A route declaration may include:
- route identifier and version
- accepted request schema version
- produced response schema version
- transport protocol and method
- idempotency requirements
- streaming/framing semantics
- size and rate constraints
- declared error schema

It must not encode hidden authority shortcuts.

For consequence-bearing actions, the route terminates at the governed execution boundary; only a fresh REHT decision followed by RACS and Gateway/PEP enforcement can produce an effect.

## Replaceability

FastAPI is one possible Python transport implementation because it can derive runtime validation and OpenAPI from typed contracts. It is not a constitutional dependency.

Equivalent transports are admissible if they preserve the same semantic contract and pass the same conformance tests.

Therefore:

```text
FastAPI != authority
OpenAPI != authority
transport success != authorization
capability != right to act
```

## Conformance requirements

A conforming transport implementation must prove at least:

1. malformed or schema-invalid input fails before canonical admission
2. undeclared fields fail closed where the canonical contract forbids them
3. sensitive/internal fields cannot appear in the declared response schema
4. generated machine-readable schema matches the implemented request/response projection
5. transport credentials or transport-local authentication cannot mint Kernel authority
6. non-PASS / DENY / STEP_UP / DEFER / HALT outcomes produce no external effect
7. stale or invalid execution authorization cannot be upgraded by a transport retry
8. idempotency semantics do not bypass fresh consequence-time authorization
9. transport implementation can be replaced without changing canonical authority semantics
10. no transport endpoint exposes an ungoverned direct effect path

## Placement

Kernel owns the canonical semantic boundary and this invariant.

Concrete FastAPI routes, HTTP middleware, OpenAPI publication, server lifecycle, worker configuration and provider-specific network I/O belong outside Kernel, in Gateway or adapter/runtime packages appropriate to the effect path.
