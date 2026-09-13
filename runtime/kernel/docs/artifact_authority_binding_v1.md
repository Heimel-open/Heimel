# Artifact Authority Binding v1

## Normative rule

No artifact carries authority by possession, validity, signature, encryption,
provenance or prior acceptance alone. Authority must be freshly established for
the specific continuation and action.

This applies to model reasoning traces, encrypted opaque state, tool/session
state, cached model context and other artifacts that may cross an invocation
boundary.

## VALO treatment

An artifact may carry data, integrity and provenance. It may not carry
clearance or execution authority.

Any artifact reference returned by a governed worker must therefore carry an
`ArtifactContextBinding` that binds the exact artifact digest to:

- workspace ID and workspace digest;
- invocation and candidate;
- worker and session;
- a continuation nonce;
- an optional predecessor digest;
- an optional producer-model reference for provenance only.

The workspace digest already binds tenant purpose, projected state, capability
scope and expiry. Model identity is therefore not an authorization primitive:
workers remain replaceable. A producer-model reference can improve provenance
without changing authority.

Raw `artifact_refs` without matching context bindings fail closed. Copying a
sealed binding into a different workspace, invocation, candidate or worker also
fails closed.

`single_use_required=true` is a consumption obligation. A worker/harness
adapter must reject reuse of the continuation nonce within its consumption
boundary. Kernel does not turn a replay cache into authoritative state. Action
non-replay remains separately bound by the downstream execution nonce.

## Execution boundary

Context binding does not make an artifact trusted and does not authorize the
action it may influence.

The downstream chain remains:

```text
governed workspace
  -> replaceable worker
  -> bound candidate/artifacts
  -> deterministic conformance
  -> VAIG evaluation
  -> fresh REHT authorization
  -> RACS decision expression
  -> external PEP enforcement
  -> execution
  -> Veritas
```

A valid signature, encryption envelope or provider-issued blob can prove
integrity or origin. It cannot answer whether this actor, in this state, for
this purpose, is entitled to continue or act now.

## Research trigger

This invariant was made explicit after the August 2026 disclosure
"Stealing Reasoning Traces from Proprietary LLM APIs" (arXiv:2608.09867),
which demonstrated that opaque encrypted reasoning artifacts could be replayed
across user/session/model boundaries. The architectural lesson adopted here is
independent of the disclosed provider-specific exploit: cryptographic validity
must never be treated as current execution authority.
