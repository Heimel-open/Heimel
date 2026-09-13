# x402 / MPP agentic-commerce adoption

Status: adopted architecture guidance
Date: 2026-08-16

## Finding

Agentic-commerce rails such as x402 and MPP make paid resources discoverable and directly consumable by autonomous software. Explorer surfaces such as x402scan and MPPScan make resources, networks and observed settlement activity visible.

That infrastructure answers useful questions such as what can be bought, over which rail, and what settlement activity was observed. It does not establish whether the represented principal authorized the exact economic action at commit time.

## VALO / REHT position

Payment capability is not execution authority.

A wallet balance, wallet signature, payment-protocol proof, facilitator acceptance, spend cap, successful settlement, explorer entry or service credential MUST NOT be treated as evidence that principal authority exists for the exact action.

The governed chain remains:

```text
service/resource discovery
-> proposed economic action
-> current authoritative state
-> REHT
-> deterministic RACS binding
-> governed Gateway / payment adapter
-> payment + service effect
-> Veritas receipt / observed outcome
```

REHT remains rail-agnostic and provider-agnostic. x402, MPP, wallets, facilitators, chains and settlement providers are replaceable execution substrates, not authority sources.

## Settlement-route binding

For a consequence-bearing purchase, payment or paid service call, the canonical action contract must bind every route field whose mutation changes the economic or external effect. Depending on the action, this includes:

- resource or service identifier;
- amount or maximum amount;
- asset or currency;
- payee / recipient;
- settlement network or rail;
- facilitator / payment processor where material;
- destination account or merchant binding where material;
- validity/freshness and execution-attempt binding.

A permit issued for one route MUST NOT silently authorize another. Changing a material route field after authorization is action drift and requires fresh REHT evaluation before commit.

Examples:

```text
ALLOW(resource=A, amount=1, asset=USDC, network=Base)
!=
ALLOW(resource=A, amount=1, asset=USDC, network=Solana)
```

and:

```text
ALLOW(payee=X)
!=
ALLOW(payee=Y)
```

## Explorer and scanner data

x402scan / MPPScan-style data may be consumed as discovery, telemetry, observation or external evidence. It may help identify resources, networks, counterparties, facilitators and observed settlement state.

It MUST NOT be promoted into authority merely because it is fresh, signed, public, on-chain or independently indexed.

A settlement record proves at most that a settlement event was observed under the relevant protocol semantics. REHT authority evidence must still come from authoritative principal-side state and remain bound to the exact proposed effect.

## Adapter rule

Any x402/MPP/AgentCash-style adapter belongs downstream of REHT and RACS, inside the single governed effect path. Credentials or wallets capable of committing the payment MUST be exclusive to that governed enforcement path; workers, models and orchestrators must not retain an alternate direct-payment route.

The adapter may mechanically translate the already-authorized contract into protocol-specific payment requirements. It MUST NOT broaden amount, asset, payee, network, facilitator, resource or validity semantics, and it MUST fail closed on mismatch.

## Product implication

A governed commerce explorer can join observed settlement to the VALO receipt chain:

```text
principal
-> delegated agent
-> current authority state
-> REHT decision
-> RACS execution contract
-> governed payment/service effect
-> settlement observation
-> Veritas receipt
```

The differentiator is not another payment scanner. It is proof of why the economic effect was allowed to exist, not merely proof that it occurred.

## Canonical invariant

`SETTLEMENT_ROUTE_BINDING`

Material mutation of a consequence-bearing settlement or payment route invalidates prior authorization and requires a fresh authorization decision before effect commit.
