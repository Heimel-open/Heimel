# External Payment Adapters v1

## Status

Temporary reference implementation inside `valo-kernel`.

Migration target: `valo-external-adapters`.

These adapters are contract projections only. They perform no live provider network I/O, hold no credentials, issue no authority and execute no external effect.

## Why this layer exists

The same enterprise authority decision must survive translation into different execution ecosystems without becoming four different definitions of authority.

Canonical chain:

```text
Authority / Delegation / Purpose
  -> bounded ExecutionAuthorityLease
  -> current revocation checkpoint
  -> eligible per-action lease evaluation
  -> fresh REHT ALLOW
  -> RACS ALLOW | MODIFY
  -> ExternalExecutionBinding
  -> provider-specific request projection
  -> provider evidence
  -> regulated settlement / effect evidence elsewhere
```

The adapter boundary therefore follows one rule:

> provider semantics may describe how an action is transported or represented, but they may not create, widen or reinterpret the authority to perform it.

## Canonical binding

`ExternalExecutionBinding` cryptographically digest-binds:

- exact `action_id` and `action_digest`
- exact `execution_ref`
- execution endpoint
- execution-authority lease digest
- eligible lease-evaluation digest
- revocation-checkpoint digest
- fresh REHT decision reference/digest with `ALLOW`
- RACS decision reference/digest with `ALLOW` or `MODIFY`
- exact target
- optional amount/currency
- binding and expiry time

The binding cannot be created from an ineligible or stale lease evaluation, REHT non-ALLOW or RACS non-effect disposition.

## Provider projections

### SWIFT / ISO 20022 CBPR+

Reference adapter: `swift.cbpr-plus.reference.v1`.

The current projection supports `pacs.008` and `pacs.009` reference message classes and binds opaque routing/message identifiers plus a required `BankExecutionAcceptance` digest.

SWIFT is treated as a messaging/network projection. The SWIFT adapter does not replace the bank's regulated decision, does not create authority and does not itself claim settlement.

### Visa trusted-agent projection

Reference adapter: `visa.trusted-agent.reference.v1`.

The adapter binds opaque external references for:

- trusted-agent assertion
- merchant
- commerce intent
- payment container

Those provider artifacts are evidence/context only. They do not replace enterprise mandate, delegation, purpose, revocation state or REHT authorization.

### Mastercard Agent Pay projection

Reference adapter: `mastercard.agent-pay.reference.v1`.

The adapter binds opaque external references for:

- agent credential
- merchant
- verifiable intent
- payment credential

The network/provider permission artifact is not treated as general organizational authority.

### Stripe agentic-payments projection

Reference adapter: `stripe.agentic-payments.reference.v1`.

The adapter binds opaque external references for:

- Shared Payment Token
- PaymentIntent
- merchant

A Stripe token or PaymentIntent may carry provider-side limits, but those limits cannot widen the upstream VALO authority envelope.

## Anti-override rule

Provider payloads are prohibited from supplying canonical authority fields such as:

```text
authority_id
lease_digest
lease_evaluation_digest
revocation_checkpoint_digest
reht_decision_ref / digest / disposition
racs_decision_ref / digest / disposition
action_digest
execution_ref
```

Those fields only exist in the canonical binding. A provider adapter can reference the resulting binding digest but cannot rewrite its contents.

## Provider evidence

`ExternalProviderEvidence` records a provider response against the exact sealed request and binding.

Possible dispositions:

```text
ACKNOWLEDGED
ACCEPTED
REJECTED
PENDING
STEP_UP
```

Even `ACCEPTED` carries:

```text
settlement_claim = NO_SETTLEMENT_CLAIM
authority_effect = NO_AUTHORITY_CREATION
```

Provider acceptance is therefore evidence for the larger execution chain. It is not automatically settlement evidence, legal authority or proof that external provider state was true.

## Current conformance target

The v1 tests prove that the same canonical binding can be projected to all four providers while preserving:

- identical action digest
- identical execution reference
- identical authority/REHT/RACS binding digest
- null provider execution capability in the reference layer
- fail-closed behavior on stale/ineligible lease evaluation
- fail-closed behavior on REHT/RACS non-effect decisions
- rejection of provider attempts to override authority fields
- tamper detection before provider evidence can be accepted

## Migration

When moved to `valo-external-adapters`, the contracts should remain unchanged and provider SDK/network implementations should sit behind them.

A production adapter may add transport, authentication, retries, idempotency, rate handling and provider signature verification. It must not change the canonical authority semantics or introduce a direct effect path around REHT/RACS and the regulated/provider enforcement boundary.
