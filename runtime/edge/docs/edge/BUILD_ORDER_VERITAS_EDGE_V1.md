# Build Order: Veritas Edge V1

Status: ACTIVE
Repository: `nsolland/valo-edge`
Canonical base: `4763e06bcf94c0048cf25a98845184c2337ceb0c`
Branch: `feat/veritas-edge-v1`

## Boundary

Veritas Edge records and verifies evidence. It never evaluates, authorizes, upgrades, retries or executes a consequence.

## Target

- authorization receipt before gateway execution
- enforcement receipt from the gateway boundary
- execution observation after driver outcome
- append-only local hash chain
- boot-epoch continuity
- failure, partial and compensation records
- self-verifiable export package for later reconciliation
- evidence for both action and non-action

## Gate

It must be possible to verify locally, without a model or network connection, what was authorized, what the gateway accepted, what the driver reported, and whether an expected consequence did not occur.
