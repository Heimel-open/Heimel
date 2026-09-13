# Work claim: External Adapters v2

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 2d36acd81324a3de55f5728365318822e050097f
Branch: feat/external-adapters-v2

Active delivery: extend the temporary in-kernel external adapter reference layer with SEPA/SCT Instant, Circle/USDC, Coinbase x402, SAP, Kyriba and Open Banking while preserving one canonical execution-authority boundary and keeping provider/source semantics non-authoritative.

Owned files:
- src/valo_kernel/external_adapters/ecosystems.py
- src/valo_kernel/external_adapters/__init__.py
- tests/test_external_ecosystem_adapters.py
- docs/external_adapters_v2.md
- .workclaims/external-adapters-v2.md

Migration target:
- move the complete external adapter package later to `valo-external-adapters` without changing canonical kernel semantics.

Invariants:
- external adapters never create, widen or reinterpret enterprise authority
- no adapter issues REHT/RACS clearance or performs live network I/O in this reference layer
- every consequence-bearing execution projection is bound to an exact sealed ExternalExecutionBinding
- SEPA/SCT Instant projections require a regulated bank-acceptance digest
- Circle and x402 artifacts remain payment/provider evidence, never general organizational authority
- Open Banking consent/provider artifacts do not replace enterprise mandate or REHT authorization
- SAP and Kyriba observations export only opaque state/evidence references, digests and bounded assertions; raw sensitive source payload is not copied into the canonical contract
- stale source observations and stale execution bindings fail closed
- provider/source payloads cannot override canonical action, lease, revocation, REHT or RACS fields
- provider acceptance is not settlement evidence; cryptographic/digest binding does not prove external truth or legal validity