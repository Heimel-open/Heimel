# Work claim: External Payment Adapters v1

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 1f704a0384968c1324c046f82da62c77e2f7436b
Branch: feat/external-payment-adapters-v1

Active delivery: add temporary in-kernel reference adapter contracts for SWIFT, Visa, Mastercard and Stripe so the same canonical VALO execution-authority binding can be projected to heterogeneous payment ecosystems without creating provider-specific authority semantics.

Owned files:
- src/valo_kernel/external_adapters/__init__.py
- src/valo_kernel/external_adapters/payments.py
- tests/test_external_payment_adapters.py
- docs/external_payment_adapters_v1.md
- .workclaims/external-payment-adapters-v1.md

Migration target:
- move this package later to a dedicated `valo-external-adapters` repository without changing canonical contract semantics.

Invariants:
- provider adapters consume canonical authority/evaluation/REHT/RACS bindings; they never create, widen or reinterpret authority
- every request remains bound to exact action, execution_ref, lease evaluation, revocation checkpoint, REHT and RACS evidence
- provider-specific fields cannot override canonical authority fields
- no adapter performs live network I/O or external effects in this reference layer
- provider acknowledgement/acceptance is not settlement evidence and never implies legal authority
- SWIFT is treated as messaging/network projection; regulated bank acceptance remains a separate upstream decision
- Visa/Mastercard/Stripe provider artifacts are opaque external references/evidence, not substitutes for enterprise mandate or REHT authorization
