# VACS Mapping to VAIG

Status: v0.1
Scope: ACS packet plus VACS VALO authority profile

## Rule

ACS is the packet and receipt standard.

VACS is the VALO profile that maps ACS packets into VAIG runtime governance, RRP refusal handling and receipt/WORM audit.

VACS does not add decision primitives.

The only primitive decisions are:

- ALLOW
- MODIFY
- DEFER
- DENY
- STEP_UP
- HALT

`DEGRADE` is not a VACS primitive.

## Packet Flow

```text
ACS packet
+ VACS authority profile
-> VAIG validation
-> AARM decision
-> RRP if refusal or blocked transition
-> ACS receipt
-> WORM/hash log
-> execution handoff only if ALLOW
```

## Field Mapping

| ACS / VACS field | VAIG target | Rule |
|---|---|---|
| `acs_version` | ACS compatibility gate | Must be `0.1` |
| `packet_id` | receipt chain | Stable packet reference |
| `agent_id` | actor identity | Must match `principal.who` when VACS is present |
| `intent.action` | IntentFactory / AARM | Action being evaluated |
| `intent.target` | boundary check / execution handoff target | Must be inside `boundary.resources` |
| `intent.scope` | RiskContract | Bounded operational scope |
| `evidence.sources` | EvidenceCondition | Sources must be typed and verified where required |
| `evidence.evidence_gap` | EvidenceCondition | Gap above policy threshold blocks guessing |
| `risk.level` | RiskContract / AARM | Drives DENY, STEP_UP or HALT |
| `confidence` | AARM | Low confidence may produce MODIFY |
| `policy.required_signoff` | Authority gate | Must align with `principal.human_signoff.required` |
| `policy.max_risk_level` | RiskContract | Risk above max produces DENY |
| `policy.evidence_gap_threshold` | EvidenceCondition | Gap above threshold produces DEFER |
| `decision` | AARM result | One of six primitives |
| `vacs_profile` | profile gate | Must be `valo-authority-v0.1` |
| `principal.who` | actor | Must match ACS `agent_id` |
| `principal.whom` | represented party | Who the agent acts for |
| `principal.authority_source` | authority reference | Policy, role, contract, law or explicit human mandate |
| `principal.human_signoff` | signoff event | Required when policy requires signoff |
| `boundary.when` | temporal boundary | When execution may be considered |
| `boundary.where` | domain boundary | Where execution is scoped |
| `boundary.resources` | resource boundary | Target must be inside this list |
| `boundary.forbidden_domains` | hard block list | Action must not be in this list |
| `boundary.execution_method` | execution handoff method | How execution would happen if allowed |
| `boundary.execution_provider` | execution handoff provider | Optional provider hint such as github, sap, salesforce, bank, erp, aws or mcp |

## Decision Ownership

VACS structures authority.

VAIG evaluates governance.

AARM returns the decision.

RRP handles refusal or blocked transitions.

Receipt/WORM records what happened.

The execution handoff adapter prepares external execution only after the decision is ALLOW.

## BARO Boundary

BARO can provide:

- evidence
- source references
- score
- confidence
- risk pressure
- observation receipt

BARO cannot provide:

- execution permission
- policy approval
- human signoff
- final authority

A BARO `ESCALATE` route maps to review or handoff. It is not an ACS/VACS execution decision.

## Execution Rule

An execution adapter may prepare a handoff only if:

```text
decision == ALLOW
AND computed decision == declared packet decision
AND ACS packet validates
AND VACS profile validates when present
AND policy boundary matches target action
AND receipt path is available
```

If the decision is STEP_UP, execution is blocked until valid human signoff exists and a new ALLOW decision is produced.

If the decision is MODIFY, DEFER, DENY or HALT, execution is blocked.

Provider-specific adapters may restrict the provider. The universal adapter accepts any provider that satisfies the same ACS/VACS governance boundary.

## First Implementation Target

The first VACS implementation is intentionally narrow:

- validate ACS v0.1 packet
- validate VACS VALO authority profile
- preserve six primitive decisions
- generate receipt
- append receipt to hash log
- reject target/resource mismatch
- reject signoff mismatch
- reject forbidden action domain
- prepare universal execution handoff only after ALLOW
- preserve GitHub and SAP as provider examples, not as the whole product
