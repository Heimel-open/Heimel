# SSIP Boundary

> ⚠️ CANONICAL STATUS: ACS/VACS are the **historical/external** standard (see
> `vacs/CANONICAL_STATUS.md`). **RACS is the ACTIVE** execution-governance path
> per `PLATFORM_ARCHITECTURE.md` §7.

SSIP remains separate in v0.1.

ACS (historical) standardizes action-control packets and receipts.

VACS (historical) maps ACS into VALO authority semantics and execution handoff.

SSIP may later consume a validated ACS/VACS handoff, but it is not part of the primitive decision layer.

SSIP must not add primitive decisions, bypass VACS authority checks, replace human signoff, or execute STEP_UP, DEFER, DENY or HALT.
