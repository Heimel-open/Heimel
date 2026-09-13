# Just-In-Time Semantic Disclosure v1

## Principle

`LEAST_SEMANTIC_PRIVILEGE`: a component receives no more consequence-bearing meaning than it needs to perform its current role.

`JUST_IN_TIME_SEMANTIC_DISCLOSURE`: once an exact consequence-bearing action has passed workspace conformance, its concrete semantics cross the Kernel boundary only as ciphertext addressed to the REHT execution boundary. The clear action is disclosed only inside that boundary immediately before fresh authorization and possible commit.

This is least privilege applied to meaning, not only identity, capability or data.

## Path

```text
worker intent
    -> governed workspace conformance
    -> exact action commitment
    -> SEAL(boundary public key)
    -> sealed execution binding
    -> REHT execution boundary
    -> fresh state + authority + evidence context
    -> UNSEAL
    -> verify commitment
    -> REHT decision
    -> RACS
    -> Gateway COMMIT
    -> effect
    -> Veritas receipt
```

The normal cross-boundary object is `SealedWorkspaceExecutionBinding`. It contains the action commitment and encrypted `SealedConsequenceAction`; it does not contain a clear `ProposedAction`.

## Cryptographic envelope

v1 uses an ephemeral X25519 key agreement with the execution boundary public key, HKDF-SHA256 key derivation and AES-256-GCM authenticated encryption. Associated data binds the ciphertext to tenant, work unit, workspace, action identity and commitment, recipient boundary/key, seal time, validity and disclosure audience.

The boundary private key is not part of Kernel state or the sealed envelope. Production confidentiality therefore depends on custody of that private key at the execution boundary, for example through KMS/HSM/TEE-backed key release. A schema claim alone is not a confidentiality boundary.

## Hard invariants

1. `NO_PLAINTEXT_EFFECT_PATH`: the clear consequence action is not carried in the sealed execution binding.
2. `BOUNDARY_KEY_CUSTODY`: only the designated execution boundary possesses or can obtain the private key required for disclosure.
3. `EXACT_ACTION_COMMITMENT`: disclosure must reproduce the exact action digest sealed before boundary crossing.
4. `FRESH_DISCLOSURE_CONTEXT`: disclosure binds to one REHT evaluation with fresh state, authority and evidence digests and must occur inside the envelope validity window.
5. `UNSEAL_NE_EXECUTE`: successful disclosure has `execution_effect=NONE`; it creates no authority, clearance or external effect.
6. `NULL_EFFECT_ON_DISCLOSURE_FAILURE`: wrong boundary, wrong key, expiry, tampering or commitment mismatch fails closed before authorization or execution.
7. `NO_DIRECT_EFFECT_PATH` remains unchanged: only the downstream governed REHT -> RACS -> Gateway path may reach a consequence-bearing tool.

## Ownership

Kernel owns governed state, conformance and sealing of the exact action leaving Kernel. REHT owns fresh exact-action authorization after JIT disclosure. RACS owns deterministic decision/effect-path semantics. Gateway owns bounded commit/enforcement. Veritas owns effect/outcome evidence.

The mechanism is provider-neutral. KMS, HSM, TEE and confidential-compute implementations are interchangeable key-custody substrates and do not become authoritative VALO dependencies.
