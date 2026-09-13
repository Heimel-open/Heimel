# ACS Compatibility Matrix

Status: implemented (VACS profile) + partial (runtime wiring)  
Related: `vacs/PROFILE.md`, `vacs/MAPPING_TO_VAIG.md`

---

## What ACS is here

ACS (Agent Control Standard) is a draft protocol for structured agent governance — not a ratified standard. VAIG implements a VALO profile of ACS called VACS (VALO Agent Control Standard).

**Allowed claim:** VAIG implements VACS schemas and receipts.  
**Not allowed to claim:** ACS is an adopted standard; VAIG is ACS-certified.

---

## Compatibility matrix

### Schemas

| Schema | Status | Location |
|---|---|---|
| `acs_packet.schema.json` — intent / evidence / risk / policy / decision fields | present | `vacs/schema/acs_packet.schema.json` |
| `acs_receipt.schema.json` — action / input / policy hashes + decision | present | `vacs/schema/acs_receipt.schema.json` |
| `vacs_profile.schema.json` — VALO-specific authority fields | present | `vacs/schema/vacs_profile.schema.json` |

Schema validation is implemented in `vacs/src/validator.py`.

### Decision mapping: AARM → ACS

| AARM Primitive | ACS Equivalent | Status |
|---|---|---|
| `ALLOW` | `decision: allow` | mapped |
| `MODIFY` | `decision: modify` | mapped |
| `DEFER` | `decision: defer` | mapped |
| `DENY` | `decision: deny` | mapped |
| `STEP_UP` | `decision: step_up` | mapped |
| `HALT` | `decision: halt` | mapped |

Mapping documented in `vacs/MAPPING_TO_VAIG.md`.

### Mandatory ACS packet fields

| Field | Required | Status |
|---|---|---|
| `intent` | yes | present in schema |
| `evidence` | yes | present in schema |
| `risk` | yes | present in schema |
| `policy` | yes | present in schema |
| `decision` | yes | present in schema |
| `receipt_hash` | yes | present in schema |

All mandatory fields are present in `acs_packet.schema.json`.

### VACS authority fields (VALO profile)

| Field | Description | Status |
|---|---|---|
| `authority_scope` | Delegation scope for the requesting agent | implemented |
| `evidence_condition` | Pre-intent gate state (VALIDATED / OVERRIDDEN / etc.) | implemented |
| `refusal_id` | Links to RRP refusal lifecycle if decision is DENY/HALT | implemented |
| `worm_hash` | SHA-256 hash of WORM entry | implemented |

See `vacs/PROFILE.md` for the full VALO profile field list.

### External protocol elements

The following ACS elements are external protocol — VAIG does not implement them:

| Element | Why external |
|---|---|
| ACS transport layer (HTTP/JSON-RPC 2.0) | Protocol spec, not runtime |
| A2A (agent-to-agent) hook protocol | ACS extension, not yet wired |
| MCP hook protocol | ACS extension, not yet wired |
| AgBOM (Agent Bill of Materials) | ACS inspect layer, not in VAIG scope |
| Guardian Agent role | Operator-side; VAIG is the Observed Agent side |

---

## What is stable vs draft

| Component | Stability |
|---|---|
| ACS packet schema fields | stable (draft) |
| ACS receipt schema fields | stable (draft) |
| VACS profile fields | stable (draft) |
| AARM → ACS decision mapping | stable |
| Schema validation (`vacs/src/validator.py`) | implemented |
| Policy engine (`vacs/src/policy_engine.py`) | implemented |
| Evidence gap detection (`vacs/src/evidence_gap.py`) | implemented |
| Runtime ACS packet emission | partial — wiring deferred |
| A2A / MCP hook integration | deferred |
| Full conformance test suite | deferred |

---

## Conformance checklist (Phase 2 activation target: July 5–15)

- [x] ACS packet schema present
- [x] ACS receipt schema present
- [x] VACS profile schema present
- [x] Schema validator implemented
- [x] AARM decision → ACS decision mapping documented
- [ ] Runtime ACS packet emission wired into agent_loop
- [ ] A2A hook protocol wired
- [ ] MCP hook protocol wired
- [ ] Conformance test suite green
- [ ] Load test under <500ms latency target

See `VACS_CONFORMANCE_CHECKLIST_2026_06_25.md` for the full four-phase conformance framework.
