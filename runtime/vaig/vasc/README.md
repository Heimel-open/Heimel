# VASC

VASC = Verifiable Agent Safety Control.

Working name: vaksine for agentic AI.

VASC is an experimental implementation track for ACS v0.1, the Agent Control Standard, inside VAIG.

The purpose is not to build another model or another agent. The purpose is to define the control packet that sits between an agent and an action.

```text
L0 Compute  -> GPU / CPU / Cloud / Phone / Edge
L1 Model    -> GPT / Claude / Llama / DeepSeek / local models
L2 Agent    -> Planner / Researcher / Coder / Buyer
L3 VASC/ACS -> Intent / Evidence / Risk / Policy / Decision / Attestation
L4 Action   -> Send email / Transfer money / Edit contract / Execute code
```

## Core thesis

AI governance should not start by asking:

> What does the model believe?

It should ask:

> Why was the agent allowed to do this?

VASC standardizes the action-control layer:

```text
Agent proposal
  ↓
ACS packet
  ↓
Schema validation
  ↓
Policy evaluation
  ↓
Decision primitive
  ↓
Attestation receipt
  ↓
Action / defer / deny / halt
```

## Six decision primitives

| Decision | Meaning |
|---|---|
| `ALLOW` | Execute immediately and generate receipt. |
| `MODIFY` | Execution may proceed only with constrained or rewritten intent. |
| `DEFER` | Evidence is insufficient. Stop and gather data or notify human. |
| `DENY` | Policy violation or unacceptable risk. Block permanently. |
| `STEP_UP` | Requires human or higher-authority approval. |
| `HALT` | System integrity risk. Stop agent activity and escalate. |

## Artificial cortisol

The key field is `evidence_gap`.

`confidence` measures what the model believes.

`evidence_gap` measures what proof is missing.

Rule for v0.1:

```text
if evidence_gap > policy.evidence_gap_threshold:
    decision = DEFER
```

If the evidence gap is too high, confidence is irrelevant. The agent must stop generating plausible action and gather evidence.

## Directory layout

```text
vasc/
  README.md
  schema/
    acs_packet.schema.json
    acs_receipt.schema.json
  src/
    vasc.py
  examples/
    allow.json
    defer.json
    halt.json
```

## Status

Experimental scaffold. Not production-ready.

This is the first reference shape for ACS/VASC before a Rust implementation.
