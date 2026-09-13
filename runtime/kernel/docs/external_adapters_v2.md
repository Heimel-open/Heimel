# External Adapters v2

## Status

Temporary reference implementation inside `valo-kernel`.

Migration target: `valo-external-adapters`.

This layer extends the first payment-adapter set with SEPA/SCT Instant, Circle/USDC, Coinbase x402, SAP, Kyriba and Open Banking. The adapters remain contract projections only: no live provider network I/O, no provider credentials, no external effect and no provider-owned authority semantics are introduced.

## Canonical execution rule

Every consequence-bearing provider request must start from an already sealed `ExternalExecutionBinding`:

```text
Authority / Delegation / Purpose
  -> current state + revocation checkpoint
  -> bounded execution lease
  -> per-action lease evaluation
  -> fresh REHT ALLOW
  -> RACS ALLOW | MODIFY
  -> ExternalExecutionBinding
  -> external adapter projection
  -> provider evidence
  -> effect / settlement evidence elsewhere
```

An adapter can describe how an action is represented or transported. It cannot create, widen or reinterpret the right to perform the action.

## Execution ecosystems

### SEPA Credit Transfer

Reference adapter: `sepa.sct.reference.v1`.

The reference projection requires:

- an amount-bound EUR execution binding
- debtor and creditor account references
- instruction identifier
- exact regulated `BankExecutionAcceptance` digest
- idempotency key

The bank acceptance is upstream of the rail projection. The SEPA adapter itself cannot decide that the customer or agent is authorized.

### SEPA Instant Credit Transfer

Reference adapter: `sepa.sct-inst.reference.v1`.

The same canonical binding is used. Only the provider/rail projection changes from SCT to SCT Inst. Authority semantics do not fork because the payment rail changes.

### Circle / USDC

Reference adapter: `circle.usdc.reference.v1`.

The projection binds opaque references for:

- Circle account
- wallet
- destination address
- blockchain
- USDC asset

The reference contract uses Circle only as an execution ecosystem. A Circle wallet, API key or provider-side transfer permission is not treated as enterprise authority.

### Coinbase x402

Reference adapter: `coinbase.x402.reference.v1`.

The projection binds:

- HTTP resource reference
- digest of the payment requirements
- opaque payment-signature reference
- facilitator reference
- network
- asset

The actual payment signature is deliberately not copied into the canonical authority contract. The adapter records only an opaque reference plus the exact requirements digest.

### Open Banking payment initiation

Reference adapter: `open-banking.payment-initiation.reference.v1`.

The projection binds:

- ASPSP reference
- PISP reference
- consent reference
- payment-resource reference
- selected API-profile reference

Customer/PSU consent is provider-side context and evidence. It does not replace enterprise mandate, delegation, purpose, current revocation state or fresh REHT authorization.

## Authoritative-state source adapters

### SAP

Reference adapter: `sap.authoritative-state.reference.v1`.

The reference surface covers bounded observations for:

- budget
- mandate
- purchase order
- counterparty state

The adapter exports no raw SAP business payload. It exports only:

- source-system reference
- source evidence reference
- object reference
- source version
- observation validity window
- source payload digest
- minimal normalized assertions
- sealed observation digest

This keeps the business system authoritative without turning VALO into a replicated ERP data store.

### Kyriba

Reference adapter: `kyriba.treasury-state.reference.v1`.

The reference surface covers:

- mandate
- treasury position
- cash forecast
- account state

The same privacy rule applies: raw treasury state remains in Kyriba. VALO receives opaque evidence references, bounded assertions and cryptographic digests only.

## State observation semantics

`ExternalStateObservation` explicitly carries:

```text
authority_effect = NO_AUTHORITY_CREATION
can_issue_clearance = false
raw_payload_exported = false
external_truth_claim = NO_EXTERNAL_TRUTH_CLAIM
```

A digest can prove that a referenced observation has not changed after sealing. It does not prove that SAP, Kyriba or another external source was factually correct or legally authoritative for every downstream purpose.

Observations are time-bounded. An observation with an expired `valid_until` is not intended to support a fresh consequence-bearing REHT decision.

## Provider evidence

`ExternalAdapterEvidence` binds a provider response to the exact request and canonical execution binding.

Supported dispositions reuse the existing provider outcome contract:

```text
ACKNOWLEDGED
ACCEPTED
REJECTED
PENDING
STEP_UP
```

Even an `ACCEPTED` provider response carries:

```text
settlement_claim = NO_SETTLEMENT_CLAIM
authority_effect = NO_AUTHORITY_CREATION
external_truth_claim = NO_EXTERNAL_TRUTH_CLAIM
```

Provider acceptance is therefore one evidence event in the larger chain, not proof of final settlement, legal validity or liability allocation.

## Anti-override invariant

Provider payloads are rejected if they attempt to supply canonical fields such as:

```text
authority_id
lease_digest
lease_evaluation_digest
revocation_checkpoint_digest
reht_decision_ref
reht_decision_digest
reht_disposition
racs_decision_ref
racs_decision_digest
racs_disposition
action_digest
execution_ref
```

A provider-specific credential, token, consent, intent, wallet permission or payment instruction can therefore never silently widen the canonical VALO authority envelope.

## Reference grounding

The reference names and shapes are intentionally narrow and provider-neutral enough to survive migration to real SDK/API adapters:

- Circle documents REST APIs for wallets, USDC transfers and idempotent requests.
- Coinbase documents x402 as an HTTP 402 payment flow with payment requirements and a payment-signature step.
- SAP exposes sourcing/procurement and business-partner integration surfaces through OData and SOAP APIs.
- Open Banking Read/Write specifications define payment-initiation flows through TPP/PISP and ASPSP relationships with customer consent.
- Kyriba is treated only as an external treasury source in this reference layer; no undocumented provider endpoint semantics are embedded in the contract.

Provider-specific transport details belong in the later `valo-external-adapters` implementation package, not in kernel authority semantics.

## Migration rule

When moved out of kernel, preserve these boundaries unchanged:

1. kernel owns canonical authority/evaluation contracts
2. adapter package consumes those contracts
3. adapter package cannot mint authority
4. provider credentials remain provider-local
5. raw source-system payload stays source-local unless separately authorized
6. non-ALLOW / stale / invalid canonical bindings produce zero provider effect
7. provider evidence feeds Veritas/effect evidence but never rewrites the authority decision
