# Local AI Is Not Trusted AI

**Status:** Draft architecture note  
**Scope:** VAIG positioning / governance architecture  
**Runtime changes:** None  
**Core changes:** None

---

## Thesis

```text
Local AI is not trusted AI.
```

Moving inference onto the device reduces latency.

It does not reduce governance risk.

```text
Location changed.
Architecture did not.
```

Trust is built in architecture, not geography.

---

## Why This Matters

The market is moving toward local inference, AI PCs, on-device agents, and edge workflows.

That movement is real.

But it does not remove the core control problem.

A local model can still:

```text
- follow injected instructions
- leak local data
- act through tools without proper authorization
- drift from user intent
- accumulate context debt
- generate false claims
- write unsafe files
- call unsafe local services
- operate without auditability
```

Local execution changes where the model runs.

It does not prove that the action is authorized, admissible, explainable, or recoverable.

---

## The Mistake

The common assumption is:

```text
Cloud AI is risky.
Local AI is safe.
```

That is false.

A better framing:

```text
Cloud AI has remote trust risk.
Local AI has local consequence risk.
```

If a local agent can touch files, credentials, terminals, browsers, databases, local APIs, enterprise data, or connected devices, then local inference can create local harm at machine speed.

---

## Architecture, Not Geography

Locality answers one question:

```text
Where does inference happen?
```

It does not answer:

```text
Who authorized this action?
Was the action admissible?
Was the tool call safe?
Was the reason still valid?
Was evidence preserved?
Can the system recover?
Is the process still coherent?
```

Those are governance questions.

They require architecture.

---

## VAIG Positioning

VAIG applies across deployment locations:

```text
cloud
edge
local
on-device
AI PC
enterprise workstation
agent runtime
MCP-connected workflow
```

The deployment target changes.

The execution boundary remains.

---

## Stack Correction

Common agent stack framing:

```text
LLM thinks.
RAG remembers.
Agent acts.
MCP connects.
```

VAIG correction:

```text
LLM proposes.
Agent acts.
MCP connects.
VAIG governs admissibility.
WHY verifies continuity.
WORM preserves evidence.
SSIP handles degradation and recovery.
Sentinel checks coherence.
```

Short form:

```text
MCP connects agents.
Connection is not control.
```

---

## Local Agents Still Need Gates

A local agent still needs:

| Requirement | Why |
|---|---|
| Governance | policies, oversight, accountability |
| Data quality controls | provenance, lineage, quality checks |
| Model assurance | validation, testing, monitoring |
| Security | access control, encryption, threat protection |
| Auditability | traceability, logging, explainability |
| Recovery | rollback, incident response, degraded-mode operation |
| Coherence monitoring | drift, contradiction, memory pressure, identity continuity |

None of these are guaranteed by running locally.

---

## The Execution Boundary

A trusted local agent must still pass through an execution boundary before consequence-bearing action.

```text
Before file write.
Before shell execution.
Before API call.
Before database mutation.
Before sending message.
Before triggering workflow.
Before committing change.
```

The boundary must ask:

```text
Is this action allowed?
Is this action admissible?
Is the justification still valid?
Will evidence be preserved?
Can the system recover if wrong?
Is the acting process still coherent?
```

---

## Relation to Coherence Sentinel

Local AI makes Coherence Sentinel more important, not less.

When an agent runs close to the user's data and tools, drift has shorter distance to consequence.

The Sentinel question remains:

```text
Is this still the process that should act?
```

That question applies whether inference happens in a cloud model, a local model, an AI PC, or an on-device runtime.

---

## Design Rule

```text
Do not treat deployment location as a trust boundary.
```

Trust boundary must be architectural:

```text
identity
authorization
admissibility
continuity
evidence
recovery
coherence
```

---

## Summary

```text
Local AI reduces latency.
Local AI can reduce data exposure.
Local AI may improve sovereignty.

But local AI is not trusted AI.

Trust is built in architecture, not geography.
```
