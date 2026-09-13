# ACS/VACS deprecation & RACS compatibility mapping (issue #991, ruling #991.2)

**Status: DEPRECATED as an execution decision layer.** RACS replaces ACS. This document records
the compatibility mapping so existing `vacs/` integrations keep working while new code targets RACS.

## Ruling

> ACS/VACS is deprecated as an execution decision layer. RACS replaces ACS. Preserve only
> genuinely distinct VAIG evaluation artifacts and provide compatibility adapters where removal
> would break active integrations. No new ACS/VACS contracts.

## Compatibility mapping (ACS/VACS → RACS canonical)

| ACS/VACS artifact | RACS canonical contract | Notes |
|-------------------|-------------------------|-------|
| `vacs/schema/acs_packet.schema.json` | `Racs/spec/action-envelope-v0.2.schema.json` | `acs_packet` is "HISTORICAL, superseded by RACS" already; maps to ActionEnvelope |
| `vacs/schema/acs_receipt.schema.json` | `Racs/spec/execution-receipt-v0.2.schema.json` | maps to ExecutionReceipt |
| `vacs/schema/vacs_profile.schema.json` | `Racs/spec/authority-context.yaml` + `policy-context.yaml` | authority + policy data |
| `vacs/src/clearance.py` (admissibility) | `Racs/spec/admissibility-determination-v0.2.schema.json` | REHT clearance space |
| VAIG AARM 6-verdict (`ALLOW/MODIFY/DEFER/DENY/STEP_UP/HALT`) | `Racs/spec/governance-evaluation-v0.2.schema.json` | vocabulary preserved verbatim, MUST NOT be reduced |
| `vacs/src/receipt.py` (WORM) | `Racs/spec/execution-receipt-v0.2.schema.json` + `continuous-integrity-event-v0.2` | digest = SHA-256 (RACS-JCS-1) |

## Rules

1. **No new ACS/VACS contracts.** All new execution-decision work uses RACS/spec.
2. **Preserve distinct VAIG artifacts.** The AARM decision engine, WHY Gate, RRP lifecycle,
   EvidenceCondition and WORM log are VAIG-specific and remain. Only the ACS *packet/receipt
   wire format* is deprecated in favor of RACS.
3. **Compatibility adapter.** `vacs/src/adapter.py` and `execution_adapter.py` translate
   ACS packets ↔ RACS ActionEnvelopes so existing integrations are not broken. Do not remove
   these adapters without a migration issue.
4. **Canonicalization/digest.** Where ACS previously defined its own canonicalization, it now
   inherits RACS-JCS-1 (RFC 8785) + SHA-256 from `Racs/spec/CANONICALIZATION.md`.

## Migration guidance for new code

- Emit RACS `action-envelope-v0.2` instead of `acs_packet`.
- Sign/evaluate with RACS `governance-evaluation-v0.2` (6-verdict).
- Prove execution with RACS `execution-receipt-v0.2`.

See `Racs/spec/SUPERSEDED.md` and `Racs/spec/CANONICAL_CONTRACTS.md` for the authoritative record.
