# Stablecoin + Agentic Payments — Handlingsrett Reference Case

## Status

Adopted external market/reference case. Not a normative dependency and not code evidence.

Source: Forrester Consulting, *How Financial Services Leaders Approach The Stablecoin Evolution*, June 2026, commissioned by AWS Marketplace. The study surveyed 521 global financial-services technology and business strategy decision-makers in March–April 2026.

## What the source supports

Forrester reports that stablecoins are moving from speculative crypto framing toward transactional utility. In the study, 70% of financial-institution respondents said stablecoins were an organizational priority, 65% said stablecoin offerings would soon become table stakes, and cross-border business and person-to-person payments were the leading current use cases.

The report also explicitly links stablecoins with agentic AI. It describes financial institutions investigating agentic-AI + stablecoin/blockchain combinations for global payments, and records interview views that trusted agent systems combined with stablecoins and smart contracts could materially reduce manual treasury operations.

The report does not define an execution-authority architecture. It does, however, identify the operational conditions that make one necessary: always-on value movement, shorter settlement times, automation, regulatory/security concerns, auditability requirements, and reliance on third-party infrastructure.

## VALO adoption

Stablecoin is treated as an effect rail, not an authority source.

```text
AI / agent proposes payment
        |
        v
current Kernel state + authority + purpose + constraints
        |
        v
fresh consequence-time REHT authorization
        |
        v
RACS deterministic effect decision
        |
        v
sealed ExternalExecutionBinding
        |
        v
stablecoin / bank / provider execution rail
        |
        v
provider evidence
        |
        v
Veritas / settlement-effect evidence
```

The authority question remains invariant across rails:

> Is this principal entitled to cause this exact consequence, under the current state and constraints, now?

A wallet, API key, smart contract, stablecoin balance, provider permission, PaymentIntent, payment token, agent credential or blockchain signature may be necessary transport/provider material. None creates or widens organizational authority.

## Demonstrator

`examples/demonstrator_8_stablecoin_agentic_payment.py` encodes a treasury case:

1. An agent is granted authority to initiate USDC payments up to 50,000 to a bounded supplier scope.
2. The agent prepares a 45,000 USDC payment while that authority is active.
3. Before consequence time, the old mandate is revoked and replaced with a 25,000 limit.
4. The Kernel execution context is rebuilt from current state.
5. Deterministic REHT-style evaluation sees the current 25,000 ceiling and denies the 45,000 payment.
6. The mock Gateway is never called; possession of the wallet/provider route cannot bypass the denial.
7. A new 20,000 USDC action is evaluated against the same fresh authority and is allowed to reach the mock Gateway.

This is the stablecoin form of authority drift: the speed and programmability of the rail increase the importance of checking authority at the effect boundary; they do not remove it.

## Invariants

- `NO_DIRECT_EFFECT_PATH`: provider/stablecoin transport is reachable only after fresh authorization and deterministic effect decision.
- provider capability is not enterprise authority.
- authority is evaluated at consequence time, not inherited from workflow start.
- changed or revoked mandate is visible before effect.
- amount/currency/target scope cannot be widened by the provider payload.
- denied actions produce zero provider effect.
- provider acceptance is evidence, not authority and not automatically final settlement proof.

## Existing alignment

This case specializes existing `external_payment_adapters_v1` / `external_adapters_v2` semantics. Circle/USDC, x402, SWIFT, Visa, Mastercard, Stripe, SEPA and Open Banking remain execution ecosystems or projections around one canonical authority boundary; the rail does not fork Handlingsrett semantics.
