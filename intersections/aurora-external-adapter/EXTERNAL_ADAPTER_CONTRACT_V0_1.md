# Aurora-Lens external adapter contract v0.1

Title: Aurora-Lens external adapter contract v0.1
Author: Njål Solland
Original IP owner: Margaret Stokes for Aurora-Lens semantics/runtime; Njål Solland / VALO Research for the independent external client mapping and conformance harness
Contributors: Margaret Stokes — review and approval pending
Status: draft
Based on: Aurora-Lens v3.0.1 Phase 0 transfer package received 11 August 2026 and observable v3.0.1 OpenAI-compatible proxy surface
Changes from prior version: replaces the earlier in-VALO adapter topology with an external optional call boundary
Permitted use: internal joint research and Phase 0 implementation under applicable transfer terms; no transfer or implied re-licensing of Aurora-Lens proprietary IP
Related synthesis: `../aurora-lens-reht/INTERFACE_PROFILE_V0_1.md`

Content type: FELLES SYNTESE / boundary implementation

## Topology

Aurora-Lens is external to VALO and to any other caller.

`caller -> independently deployed Aurora-Lens -> response`

The caller may choose to call or not call Aurora-Lens. Calling Aurora-Lens does not make Aurora-Lens part of the caller's architecture or authority chain.

The reference client in this directory is a transport/conformance shim only. It contains no Aurora-Lens policy logic.

## Observable Phase 0 service surface

The transferred v3.0.1 wheel exposes an OpenAI-compatible proxy with:

- `GET /health`
- `POST /v1/chat/completions`
- governance metadata returned under the top-level `aurora` object

The client preserves Aurora's native governance vocabulary:

- `PASS`
- `SOFT_CORRECT`
- `CONTAIN`
- `FORCE_REVISE`
- `HARD_STOP`

For convenience only, `PASS` and `SOFT_CORRECT` are classified as admitted; `CONTAIN`, `FORCE_REVISE`, and `HARD_STOP` are classified as non-admit. The adapter must never upgrade or rewrite the native Aurora outcome.

## Request contract

Minimum request:

```json
{
  "model": "aurora-lens",
  "messages": [
    {"role": "user", "content": "..."}
  ],
  "stream": false
}
```

Optional transport headers supported by the reference client:

- `Authorization: Bearer <token>`
- `X-Aurora-Session-Id: <session-id>`
- `X-Aurora-Operator-Detail: true`

## Response contract

The external client requires:

```json
{
  "choices": [
    {"message": {"role": "assistant", "content": "..."}}
  ],
  "aurora": {
    "governance": "PASS | SOFT_CORRECT | CONTAIN | FORCE_REVISE | HARD_STOP"
  }
}
```

The `aurora` block is authoritative for the Aurora-Lens result. The assistant body alone is not sufficient evidence of admission.

The client may also expose opaque trace fields when present, including `session_id`, `audit_id`, `turn`, and the complete unmodified `aurora` object.

## Fail-closed rules

The external client fails closed when:

1. the service is unreachable;
2. the service returns non-JSON;
3. the top-level response is not an object;
4. the `aurora` governance block is absent;
5. `aurora.governance` is missing or outside the known v3.0.1 vocabulary.

It does not infer admission from HTTP 200 or from the presence of assistant text.

## Non-authority rule

This adapter is not an authorization engine. If VALO is a caller, any VALO execution authorization remains entirely within VALO's own canonical execution boundary. If another system is the caller, that system remains responsible for its own downstream authority.

## IP boundary

The proprietary Aurora-Lens wheel, source implementation and transferred test suite remain external licensed artefacts and are not committed to this shared repository. Only the independently written client/conformance boundary and acceptance evidence are stored here.
