# ACS v0.1 / VACS v0.1

> ⚠️ CANONICAL STATUS: ACS/VACS are the **historical/external** standard. Per
> `PLATFORM_ARCHITECTURE.md` §7, **RACS is the ACTIVE** execution-governance path.
> This directory is retained as a historical implementation adapter only — see
> `vacs/CANONICAL_STATUS.md`. Do not treat ACS/VACS as the active standard.

ACS is the Agent Control Standard.

VACS is the VALO profile / implementation path for ACS (historical).

ACS standardizes the action-control packet and receipt.

VACS maps that packet into VALO authority semantics, VAIG runtime checks, RRP refusal handling, execution handoff and receipt/WORM audit.

## Architecture

```text
ACS-L4: ACTION    -> Send email | Transfer | Edit | Execute
ACS-L3: ACS       -> Intent -> Evidence -> Risk -> Policy -> Decision -> Attestation
ACS-L2: AGENT     -> Planner | Researcher | Coder | Buyer
ACS-L1: MODEL     -> GPT | Claude | Llama | DeepSeek
ACS-L0: COMPUTE   -> GPU | CPU | Cloud | Phone
```

Use `ACS-L0` to `ACS-L4` for these layers. Do not use bare `L0-L4`, because VAIG also has distrust levels.

## Six Primitive Decisions

| Decision | Trigger | Next step |
|---|---|---|
| ALLOW | Low risk, good evidence | Execute |
| MODIFY | Low confidence, acceptable evidence | Execute with modification |
| DEFER | Evidence gap too high | Gather data or request human review |
| DENY | Risk exceeds policy | Block and log |
| STEP_UP | High risk or signoff required | Send to stronger authority |
| HALT | Critical risk | Stop the agent path |

No other primitive decision exists in v0.1.

`DEGRADE` is not an ACS/VACS primitive.

## Structure

```text
vacs/
├── schema/
│   ├── acs_packet.schema.json
│   ├── acs_receipt.schema.json
│   └── vacs_profile.schema.json
├── src/
│   ├── validator.py
│   ├── profile.py
│   ├── policy_engine.py
│   ├── execution_adapter.py
│   ├── receipt.py
│   ├── hashlog.py
│   └── evidence_gap.py
├── examples/
│   ├── allow.json
│   ├── modify.json
│   ├── defer.json
│   ├── deny.json
│   ├── step_up.json
│   ├── halt.json
│   ├── vacs_profile_packet.json
│   ├── execution_handoff_github_allow.json
│   └── execution_handoff_sap_allow.json
├── tests/
│   ├── test_acs.py
│   ├── test_vacs_profile.py
│   └── test_execution_handoff.py
├── PROFILE.md
└── MAPPING_TO_VAIG.md
```

## VACS Profile

VACS adds these authority fields around a valid ACS packet:

- `vacs_profile`
- `principal.who`
- `principal.whom`
- `principal.authority_source`
- `principal.human_signoff`
- `boundary.when`
- `boundary.where`
- `boundary.resources`
- `boundary.forbidden_domains`
- `boundary.execution_method`
- `boundary.execution_provider`

VACS does not decide.

VAIG evaluates.

AARM returns one of the six primitive decisions.

RRP handles refusal or blocked transitions.

Receipt/WORM records the chain.

## Execution Handoff

The execution adapter is universal. It does not execute external side effects.

It prepares a governed handoff only when:

```text
decision == ALLOW
AND computed decision == declared packet decision
AND ACS validates
AND VACS validates when present
AND target is inside boundary resources
AND receipt/hashlog path is available
```

GitHub, SAP, Salesforce, ServiceNow, bank, ERP, cloud and MCP tools should cross the same authority boundary.

Provider-specific wrappers may exist, but they must not create new decision semantics.

## Evidence Gap

```json
{
  "evidence_gap": 0.41
}
```

If the gap is above policy threshold, the agent must not guess.

## Receipt

After each governed decision, ACS can generate an attestation receipt:

```json
{
  "receipt_id": "uuid",
  "packet_id": "uuid",
  "action_hash": "sha256:...",
  "input_hash": "sha256:...",
  "policy_hash": "sha256:...",
  "decision": "ALLOW",
  "timestamp": "2026-06-16T12:00:00Z",
  "signature": "ed25519:..."
}
```

Receipt is process proof, not wisdom proof.

## Run Tests

```bash
cd vacs/tests
python test_acs.py
python test_vacs_profile.py
python test_execution_handoff.py
```

## License

MIT