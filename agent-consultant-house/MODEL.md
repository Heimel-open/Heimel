# Model

## Entities

### HumanOwner

Owns or funds agents.

Fields:

- `cash`
- `portfolio`
- `risk_preference`
- `yield_received`

### Agent

Performs work.

Fields:

- `domain`
- `skill`
- `cost`
- `reputation`
- `balance`
- `owner`
- `failure_count`
- `completed_count`

### Task

Work request.

Fields:

- `domain`
- `reward`
- `risk`
- `required_skill`
- `authority_required`

### VALOGate

Pre-execution admissibility layer.

Checks:

- agent reputation
- task risk
- authority requirement
- skill fit
- owner risk policy

Returns:

- `ALLOW`
- `STEP_UP`
- `DENY`
- `HALT`

### Receipt

Proof of market event.

Fields:

- `task_id`
- `agent`
- `decision`
- `quality`
- `payout`
- `owner_yield`
- `audit_hash`

### BARO Signal

Observation layer.

Consumes receipts and emits:

- agent drift
- repeated denials
- rising STEP_UP rate
- domain concentration
- owner exposure
- market health

## Market Loop

```text
Task posted
-> agents bid
-> VALO checks authority/risk
-> selected agent executes
-> quality is scored
-> receipt is written
-> payout settles
-> reputation updates
-> owner receives yield
-> BARO observes market signal
```

## Boundary

This pilot does not implement real crypto settlement.

It models the economic logic first.

Wallet, token, staking, and exchange mechanics should come after receipts and authority control work.
