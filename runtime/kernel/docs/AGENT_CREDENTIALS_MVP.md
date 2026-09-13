# Agent Capability Credentials MVP

This MVP defines a portable, independently attestable capability credential for software agents.

It is intentionally narrower than execution authority.

## Core distinction

A credential answers:

> Has this agent demonstrated this bounded capability under a named conformance suite, and is that evidence still trusted and valid?

It does not answer:

> May this agent perform this action now?

The latter remains a fresh REHT / Kernel authority decision at the consequence boundary.

## Minimal flow

1. An agent is evaluated against a named, versioned conformance suite.
2. The evaluator records immutable evidence by digest.
3. A trusted issuer signs a bounded capability credential.
4. A relying runtime verifies issuer trust, signature, subject, capability, scope, validity and revocation.
5. A successful check returns `ADMISSIBLE` for capability only.
6. Execution still requires independent authority and consequence-time governance.

## Credential fields

- `credential_id`: globally unique credential reference.
- `issuer_id`: independent issuer or certification authority.
- `subject_agent_id`: the agent identity the credential belongs to.
- `capability_id`: machine-readable capability class.
- `scope`: bounded operations/resources covered by the credential.
- `risk_class`: issuer-defined assurance/risk profile.
- `issued_at`, `valid_from`, `valid_until`: temporal validity.
- `conformance.test_suite` and `test_suite_version`: reproducible test definition.
- `conformance.passed`, `failed`: assessment result.
- `conformance.evidence_digest`: content-addressed evidence receipt.
- `signature`: Ed25519 issuer signature over the unsigned credential payload.

## Fail-closed checks

The reference gate denies when any of the following is true: no matching credential exists; issuer is not trusted; signature fails; credential is revoked; credential is outside its validity window; requested scope exceeds credential scope; or agent/capability identity does not match.

## Why this matters

The architecture separates four things that are commonly collapsed:

- capability: what the agent has demonstrated it can do;
- credential: who attests to that demonstration;
- authority: what the agent is permitted to do now;
- evidence: what can later be replayed and verified.

That separation is the basis for an IEEE-like professional credential layer for agents without turning certification into authority.

## MVP interoperability target

The first external profile should standardize three artifacts: capability taxonomy, conformance suite identity/versioning, and signed credential envelope. VALO can remain the reference conformance/evidence implementation while independent issuers and runtimes interoperate on the credential format.

## Non-goals

The MVP does not define a global PKI, issuer accreditation scheme, public revocation service, capability taxonomy governance body, or universal risk classification. Those are federation/standardization layers above the minimal executable contract.
