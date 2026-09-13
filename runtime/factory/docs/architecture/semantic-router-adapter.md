# Semantic Router Adapter

Status: ACTIVE
Boundary: selection only
Authority effect: none

VALO Factory may use semantic routing to select a candidate agent, provider or
tool before governance and execution. The router is not an authorization,
policy, mandate or execution component.

Canonical flow:

Task + precomputed embeddings -> router adapter -> route suggestion -> VAIG /
REHT evaluation -> governed execution boundary -> execution -> Veritas

`RuVectorRouterAdapter` is the first adapter. It is deliberately replaceable
through `RouterRegistry`. The isolated Node connector pins
`@ruvector/router` to `0.1.30` and calls `routeWithEmbedding` only.

Invariants:

- The router receives precomputed embeddings; it does not own an embedder,
  credential, network lookup or model call.
- Router output must state `authority_effect: none`.
- Unknown routes, changed handlers, unsupported fields, invalid scores,
  malformed JSON and connector failures fail closed.
- A route suggestion is not a REHT clearance and cannot be passed directly to
  a gateway as executable authority.
- No router adapter may execute a selected route.
