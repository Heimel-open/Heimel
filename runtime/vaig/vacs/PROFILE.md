# VACS Profile

> ⚠️ CANONICAL STATUS: VACS is the **superseded** VALO profile for the **historical/external**
> ACS standard. Per `PLATFORM_ARCHITECTURE.md` §7, **RACS is the ACTIVE** execution-governance
> path. This directory is retained as a historical implementation adapter only — see
> `vacs/CANONICAL_STATUS.md`. Do not treat ACS/VACS as the active standard.

Status: v0.1 implementation seed  
Scope: VALO profile / implementation path for ACS (historical)

## 1. Naming

ACS means Agent Control Standard.

VACS means the VALO profile and implementation path for ACS.

ACS is the standard.

VACS is the VALO-specific profile that maps ACS packets and receipts into VAIG, RRP, EvidenceCondition, RiskContract and WORM.

## 2. What ACS is

ACS is a TCP/IP-inspired control layer for autonomous AI agents.

It is not TCP/IP as a network protocol.

It is inspired by TCP/IP in role: a standardized control layer above agent, model and compute layers.

ACS standardizes the action-control packet, not the model.

## 3. Layer model

```text
ACS-L4 ACTION  -> Send email | Transfer | Edit | Execute
ACS-L3 ACS     -> Intent | Evidence | Risk | Policy | Decision | Attestation
ACS-L2 AGENT   -> Planner | Researcher | Coder | Buyer
ACS-L1 MODEL   -> GPT | Claude | Llama | DeepSeek
ACS-L0 COMPUTE -> GPU | CPU | Cloud | Phone
```

Use ACS-L0 to ACS-L4 when referring to these layers.

Do not use bare L0-L4, because VAIG also has distrust levels and other historical layer language.

## 4. VACS role inside VALO

VALO defines the architecture.

VAIG runs the control.

ACS standardizes the control packet and receipt.

VACS maps ACS into VALO authority semantics, VAIG runtime checks, RRP refusal handling and receipt/WORM audit.

RRP handles refusal-to-governable-state lifecycle.

Receipt / WORM preserves audit evidence.

## 5. Current ACS packet fields

The current ACS packet schema requires:

- acs_version
- packet_id
- agent_id
- timestamp
- intent
- evidence
- risk
- confidence
- policy
- decision

Current allowed decisions:

- ALLOW
- MODIFY
- DEFER
- DENY
- STEP_UP
- HALT

## 6. Current VACS profile fields

The current VACS profile schema adds:

- vacs_profile
- principal.who
- principal.whom
- principal.authority_source
- principal.authority_reference
- principal.human_signoff
- boundary.when
- boundary.where
- boundary.resources
- boundary.forbidden_domains
- boundary.execution_method

Optional handoff field:

- boundary.execution_provider

These fields do not replace ACS.

They bind the ACS packet to VALO authority semantics.

## 7. Current ACS receipt fields

The current ACS receipt schema requires:

- receipt_id
- packet_id
- action_hash
- input_hash
- policy_hash
- decision
- timestamp

Optional:

- signature

## 8. Mapping to VAIG

See `vacs/MAPPING_TO_VAIG.md` for the field-level map.

| ACS / VACS concept | VAIG / VALO mapping |
|---|---|
| intent | src/vaig/rrp/intent.py |
| evidence | EvidenceCondition |
| risk | RiskContract tier and domain |
| policy | RiskContract / AARM / operator policy |
| decision | AARM decision |
| attestation | Receipt / WORM |
| evidence_gap | EvidenceCondition / contract validation gap |
| refusal | RRP RefusalEvent / RefusalLifecycle |
| authority | AuthorityAssignment / MECHA / BOA / Operators |
| execution handoff | vacs/src/execution_adapter.py |

## 9. Boundary

VACS does not decide.

VACS structures the VALO profile around ACS packets and receipts.

VAIG evaluates and governs.

AARM decides.

RRP resolves refusal transitions.

MECHA determines human decision legitimacy outside the machine runtime.

The execution handoff adapter does not execute external side effects. It prepares a provider-agnostic handoff only after validation and an ALLOW decision.

## 10. Public claim

Allowed:

VACS is an early VALO profile for ACS-style action-control packets, receipts and execution handoff boundaries.

Not allowed:

VACS / ACS is already an adopted external market standard.

## 11. Current implementation work

Implemented seed:

- universal execution handoff adapter
- GitHub handoff example
- SAP handoff example
- provider-specific GitHub wrapper
- tests proving only ALLOW can cross the execution boundary

Next work:

- Add receipt fixtures for all six decisions.
- Add formal conformance checklist for ACS baseline versus VACS profile.
- Add provider fixtures for Salesforce, ServiceNow, cloud and banking/ERP flows.
- Decide whether SSIP remains separate or becomes an ACS implementation surface.
