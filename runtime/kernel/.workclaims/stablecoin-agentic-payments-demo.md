# Work Claim — Stablecoin Agentic Payments Demo

Owner: ChatGPT / nsolland

Base SHA: `0a8205f8a3c169eede7b7d8e50c4d66a950d5c32`

Branch: `feat/stablecoin-agentic-payments-demo`

Active delivery: adopt stablecoin + agentic AI as a concrete Handlingsrett reference case and add an executable demonstrator showing consequence-time authority control for programmable money.

Owned files:
- `.workclaims/stablecoin-agentic-payments-demo.md`
- `docs/stablecoin_agentic_payments_case.md`
- `examples/demonstrator_8_stablecoin_agentic_payment.py`

Dependencies:
- existing Kernel authority and execution-context semantics
- existing REHT/RACS/Gateway/Veritas boundary definitions
- existing external payment adapter semantics

Invariants:
- stablecoin/provider rails transport effects; they do not create authority
- an agent must not gain authority from possession of a wallet, token, PaymentIntent, smart contract, or provider credential
- authority is re-read at consequence time
- revoked or exceeded authority fails closed before external effect
- successful effect evidence remains bound to the exact authorized action
- no direct effect path around REHT/RACS/Gateway

Source basis:
Forrester Consulting, June 2026, commissioned by AWS Marketplace: *How Financial Services Leaders Approach The Stablecoin Evolution*. Adopted as an external market/reference case only; it is not code evidence or a normative protocol dependency.
