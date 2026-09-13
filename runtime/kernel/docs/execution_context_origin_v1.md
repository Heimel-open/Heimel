# Kernel execution-context origin proof v1

Kernel can seal one resolved execution context so REHT can distinguish an
unmodified Kernel result from a caller-constructed mapping. The seal proves
origin and integrity only. It does not admit truth, grant authority, issue
clearance, or authorize execution.

## Production flow

1. `build_execution_context(...)` resolves current tenant state, workspace
   dependencies, authority records, purpose, time, nonce and the requested
   transition.
2. `seal_execution_context(context, signer=...)` copies the mapping and adds
   `origin_proof`. The input mapping is never mutated.
3. The complete sealed mapping is RFC 8785 canonicalized. Its
   `sha256:<hex>` digest becomes the RACS `kernel_context_digest`.
4. REHT recomputes that full digest, removes `origin_proof`, recomputes the
   signed content digest, verifies the tenant-scoped key and signature, then
   performs its own fresh authority and purpose evaluation.

The full lineage digest includes the proof itself. Determinations, clearances,
permits and receipts therefore identify the exact proof REHT accepted.

## Origin-proof contract

`origin_proof` has exactly these fields:

| Field | Rule |
|---|---|
| `schema_version` | `kernel_execution_context_origin.v1` |
| `canonicalization` | `RACS-JCS-1` (RFC 8785) |
| `digest_algorithm` | `SHA-256` |
| `signature_algorithm` | `Ed25519` |
| `kernel_id` | configured signer identity |
| `key_id` | configured rotation-safe key identity |
| `tenant_id` | exact execution-context tenant |
| `issued_at` | exact resolved Kernel context time |
| `content_digest` | RFC 8785 SHA-256 digest before `origin_proof` is added |
| `signature` | unpadded base64url Ed25519 signature |

The signature input is:

```text
UTF8/bytes("VALO-KERNEL-CONTEXT-V1\\0")
    || RFC8785(origin_proof without signature)
```

Do not change the domain separator, field set, canonicalization profile or
digest formatting without a new schema version and shared negative vectors.

## Key boundary

`KernelContextSigner` is the production abstraction. A KMS or HSM adapter can
implement it without exposing private key material to Kernel state.
`Ed25519KernelContextSigner` is the reference software implementation and
accepts an injected 32-byte seed. Neither implementation may serialize a
private key into world state, the execution context, logs or receipts.

REHT trust configuration must bind every accepted public key to:

- one `kernel_id` and `key_id` pair;
- an explicit set of tenants (wildcards are forbidden);
- a timezone-aware, half-open validity interval `[valid_from, valid_until)`.

## Fail-closed review cases

Reviewers must demonstrate rejection of missing proofs, unknown proof fields,
changed context content, changed proof metadata, invalid signatures, untrusted
keys, cross-tenant keys, inactive keys, stale `issued_at`, malformed RFC 8785
content and silent re-sealing.

The positive test is not sufficient: a verifier that accepts a well-shaped but
unsigned mapping defeats the boundary.

