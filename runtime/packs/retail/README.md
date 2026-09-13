# VALO Retail Pack v1

Domain pack over Function Fabric. It is not a new architectural layer and has no independent authority.

Canonical execution path:

Kernel → Workflow ISA → Function Fabric → reht → RACS → Gateway → Veritas

Governed functions:

- RETAIL_MOVE_INVENTORY
- RETAIL_SET_PRICE
- RETAIL_CREATE_PROMOTION
- RETAIL_CREATE_PURCHASE_ORDER
- RETAIL_REFUND_ORDER

All actions use `RetailActionIntentV1` and produce `RetailExecutionReceiptV1`.

Shopify, SAP and Adobe are provider adapter boundaries. UCP, ACP and AP2 are transport/evidence only and never grant authority.

The first end-to-end proof is `RETAIL_MOVE_INVENTORY` in shadow mode, then bounded live execution. Provider execution requires a valid reht permit, compare-state is fail-closed, idempotency is tenant-bound, provider failures are never represented as executed, and the resulting state is read back and bound to a Veritas receipt.

Run tests:

```bash
python -m pytest -q
```
