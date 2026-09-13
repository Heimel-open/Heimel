# VALO Retail Pack

VALO Retail Pack is a domain package over Function Fabric for governed retail execution. It does not introduce a new architectural layer, authority model, or decision engine.

Canonical path:

Kernel → Workflow ISA → Function Fabric → reht → RACS → Gateway → Veritas

## What the module does

Retail Pack converts retail business intent into explicit, typed execution requests that can be authorized at the execution boundary and verified after provider execution.

It governs five actions:

- `RETAIL_MOVE_INVENTORY`
- `RETAIL_SET_PRICE`
- `RETAIL_CREATE_PROMOTION`
- `RETAIL_CREATE_PURCHASE_ORDER`
- `RETAIL_REFUND_ORDER`

Every request is expressed as `RetailActionIntentV1`. The contract binds actor, authority chain, purpose, jurisdiction, target resource, desired change, expected before-state/version, value, risk, validity, idempotency and evidence.

Before any provider call, the intent is evaluated against action-specific retail rules and must receive a valid reht permit. Shopify, SAP and Adobe remain execution providers behind adapter boundaries. UCP, ACP and AP2 may transport data or evidence, but never confer authority.

## Execution guarantees

The module is designed to fail closed when authority, evidence, freshness or compare-state is missing. Large-value actions can require `STEP_UP`. Tenant-bound idempotency prevents duplicate execution. Provider errors are recorded as failures, never as completed actions. Successful execution is read back from the provider and bound to `RetailExecutionReceiptV1` and Veritas evidence.

## First proof

The first end-to-end proof is `RETAIL_MOVE_INVENTORY`.

A warehouse move is proposed with an expected inventory version and before-state. Retail Pack validates stock, reservations and safety stock, reht authorizes the exact action, the adapter checks the permit at the execution boundary, and the provider result is read back. If inventory has changed before execution, the action is denied rather than applied against stale state.

The proof runs first in shadow mode, then as bounded live execution.

## Product meaning

Retail Pack gives retailers a reusable execution-control layer for AI agents, workflows and automation. Existing commerce and ERP systems remain systems of record. Retail Pack decides whether the concrete action is admissible for execution now, enforces the permit at the provider boundary, and produces evidence of what actually happened.