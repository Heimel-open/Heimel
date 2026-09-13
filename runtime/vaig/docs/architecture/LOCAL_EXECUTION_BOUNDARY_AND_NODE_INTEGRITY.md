# Local Execution Boundary and Node Integrity

Status: active VALO architecture
Date: 2026-07-11

## Principle

Governance must remain effective at the point where consequence is committed.

A centrally governed system is not sufficient if a consequential action can occur through an unmanaged browser, endpoint, local agent, extension, personal account or external automation path.

## Problem

AI execution increasingly occurs through:

- employee laptops and mobile devices
- browser extensions and browser agents
- local models and endpoint agents
- Office and email clients
- personal AI accounts
- unmanaged SaaS automations
- developer tools and local scripts
- embedded workflow agents

This creates two related risks:

1. **Local-node risk** — consequence occurs outside the central runtime boundary.
2. **Invisible-node risk** — the organization does not know that the execution path exists.

## Active architecture

```text
Node and connector observations
        ↓
Speider / BARO
        ↓
Node Integrity Reality Package
        ↓
VAIG runtime evaluation
        ↓
REHT admissibility determination
        ↓
VALO Core enforcement
        ↓
External consequence
        ↓
RACS receipt
```

## Node Integrity Reality Package

A package may contain:

```json
{
  "node_id": "node-123",
  "managed_node": true,
  "approved_tool": true,
  "connector_id": "connector-456",
  "transition_type": "external_write",
  "consequence_class": "high",
  "authority_evidence_ref": "evidence-1",
  "stop_right_present": true,
  "escalation_path_present": true,
  "human_review_required": true,
  "receipt_capable": true,
  "integrity_state": "verified",
  "observed_at": "2026-07-11T00:00:00Z",
  "evidence_refs": ["evidence-1", "evidence-2"]
}
```

BARO observes and packages evidence. BARO does not decide.

## VAIG evaluation

VAIG evaluates runtime conditions such as:

- whether the node is managed
- whether the tool or connector is approved
- whether credentials are valid and properly scoped
- whether authority evidence is current
- whether the node can preserve receipts
- whether the action is reversible
- whether required review can occur before consequence
- whether execution context has drifted

VAIG emits structured evaluation evidence. It does not independently grant authority.

## REHT admissibility

REHT asks:

> Is this action still admissible at this node, through this tool, under the current authority, evidence, policy, context and risk state?

Possible outcomes include:

- `ALLOW`
- `MODIFY`
- `DEFER`
- `STEP_UP`
- `DENY`
- `HALT`

## Core enforcement

VALO Core enforces the selected bounded state transition.

Core does not infer social legitimacy, invent authority or reinterpret organizational policy. It enforces the supplied governed state transition and preserves terminal safety properties.

## RACS receipt

The resulting receipt should link:

- action envelope
- node identity
- connector and tool identity
- authority evidence
- policy fingerprint
- context fingerprint
- VAIG evaluation
- REHT outcome
- Core transition
- external result
- immutable evidence references

## Shadow IT handling

Shadow IT is treated as an observation and governance-coverage problem.

Speider and BARO may identify:

- unregistered tools
- unknown browser extensions
- personal AI accounts used for company work
- unapproved automation endpoints
- unmanaged local agents
- missing receipt paths
- execution outside approved connectors

The observation itself does not authorize blocking or remediation. Any consequence-bearing response must pass through VAIG, REHT and Core.

## Control rule

```text
Central policy is not enough.
The consequential transition must remain governable where it occurs.
```

## Non-dependencies

This active architecture has no runtime dependency on MECHA, EFA, WHY Gate, RRP or other historical collaboration frameworks.
