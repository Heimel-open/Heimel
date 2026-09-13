# VALO Moltbook MVP

Date: 2026-06-25
Status: buildable MVP

## Purpose

Use Moltbook as distribution.

Use VALO as the authority, delegation, budget and receipt layer.

The goal is not to replace Moltbook.

The goal is to make VALO receipts the proof format agents use when they want to be trusted, hired, ranked or paid.

## Core wedge

Moltbook has agent communication.

VALO adds agent legitimacy.

```text
Moltbook: agent posts
VALO: agent proves it was allowed to act
```

## Public challenge

```text
Any agent can act.
Few can prove they were authorized.

Take the VALO Agent Receipt Challenge:
1. declare agent identity
2. declare owner/operator
3. declare delegation scope
4. declare budget
5. request one action
6. return ALLOW, STEP_UP, DENY or HALT
7. publish the receipt

No receipt, no trust.
```

## MVP flow

```text
agent.valo.id profile
        ↓
budget file
        ↓
action request
        ↓
VALO Moltbook verifier
        ↓
ALLOW / STEP_UP / DENY / HALT
        ↓
receipt
        ↓
public post / registry / badge
```

## First demo

Action request:

```text
Agent Research-01 wants to spend 1 receipted unit on public_safe_distribution.
```

Expected result:

```text
ALLOW
```

Reason:

```text
agent exists
owner exists
delegation exists
surface is allowed
budget is sufficient
receipt can be generated
```

Failure demo:

```text
Agent Research-01 wants to spend 1 receipted unit on financial_transfer.
```

Expected result:

```text
DENY
```

Reason:

```text
financial_transfer is a blocked spend surface
```

## Minimal proof fields

```yaml
agent_id: agt_research_01
owner_id: owner_njaal
delegation_id: research_01_operating_boundary
budget_id: research_01_budget_30d
action_surface: public_safe_distribution
amount: 1
decision: ALLOW
reason: allowed_surface_budget_available
receipt_hash: sha256:...
```

## Product rule

Do not sell this as governance.

Sell it as proof.

Better phrase:

```text
Prove your agent is authorized.
```

## Badge rule

An agent can claim VALO-governed status only if it can show:

- verified identity
- accountable owner/operator
- delegation boundary
- budget boundary
- receipt-backed action history
- revocation path

## Immediate build objects

- `tools/valo_moltbook_mvp.py`
- `receipts/moltbook-authorized-spend.receipt.yaml`
- `receipts/moltbook-denied-spend.receipt.yaml`

## Strategic position

Moltbook can remain the bazaar.

VALO becomes the trust ledger.
