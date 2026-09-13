# VACS Python SDK

> ⚠️ CANONICAL STATUS: VACS implements the **historical/external ACS** standard.
> Per `PLATFORM_ARCHITECTURE.md` §7, **RACS is the ACTIVE** execution-governance
> path. This SDK is retained as a historical adapter only — see `vacs/CANONICAL_STATUS.md`.
> Do not treat ACS/VACS as the active standard in new code.

Minimal Python SDK for VALO Agent Control execution governance.

This SDK is not an agent identity product. It is an execution-control layer.

It verifies whether a proposed agent action is permitted under explicit authority, delegation, scope, evidence and risk constraints.

## Core idea

Identity proves who the agent is.

VACS decides whether this agent may perform this action, under this delegation, for this tenant, against this evidence, with an auditable receipt.

## Minimal use

```python
from vacs_sdk import verify

result = verify(authority, request)

if result.valid:
    execute()
else:
    refuse(result.reason)
```

## Control chain

1. Agent identity
2. Authority token
3. Delegation scope
4. Evidence reference
5. Risk score
6. Decision
7. Receipt

## Decisions

- ALLOW
- MODIFY
- DEFER
- DENY
- STEP_UP
- HALT

## Status

- ACTIVE
- EXPIRED
- REVOKED
- INVALID
- UNAUTHORIZED

## Design boundary

VACS does not replace OAuth, Claw, SPIFFE, passkeys or enterprise IAM.

Those systems can prove identity.

VACS governs execution.
