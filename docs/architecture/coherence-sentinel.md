# Coherence Sentinel

**Status:** Draft architecture note  
**Scope:** VAIG / agentic runtime governance  
**Type:** Lovgiveren component proposal  
**Runtime changes:** None in this PR

---

## Purpose

Coherence Sentinel is the first proposed Lovgiveren component for an agentic runtime.

It is not a permission gate.

It is not another tool policy layer.

It is a runtime observer that asks whether an agentic process remains coherent across repeated transformations: context assembly, tool execution, compaction, delegation, session persistence, and recovery.

Core question:

```text
Am I still the process that should act?
```

In Tofoo terms:

```text
Coherence Sentinel watches whether the agent is still framleis.
```

---

## Background

The paper *Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems* describes a production agent architecture where the model reasons, the harness executes, permissions gate actions, context compaction manages scarce context, subagents isolate delegated work, and append-oriented storage preserves sessions.

That architecture is a strong map of the Tolken: the adaptive interface that explores, acts, and adapts.

However, the paper also identifies long-term capability preservation as an unresolved tension. Memory is treated largely as context management, file-based retrieval, compaction, and session persistence.

From the Phi-Law perspective, this leaves a missing architectural role:

```text
The system manages context.
It does not yet manage coherence.
```

Coherence Sentinel is the first component that begins to fill that gap.

---

## Placement

Coherence Sentinel sits beside the agent loop, observing the agent before and after each transformation.

```text
User prompt
   ↓
Context assembly
   ↓
Coherence Sentinel pre-check
   ↓
Agent loop / model call
   ↓
Tool request
   ↓
Permission / VAIG / WHY Gate
   ↓
Tool execution
   ↓
Tool result
   ↓
Coherence Sentinel post-check
   ↓
Next iteration or recalibration
```

It should observe, not replace, the existing safety layers.

---

## Relationship to Existing Layers

```text
CAN asks capability.
SHOULD asks policy.
WHY asks continuity.
SENTINEL asks coherence.
```

Layer mapping:

| Layer | Question |
|---|---|
| VAIG | Is this admissible? |
| WHY Gate | Does the justification still hold until consequence commitment? |
| WORM | What happened, and can it be audited? |
| SSIP | What must happen when integrity degrades? |
| Coherence Sentinel | Is the agentic process still coherent enough to continue? |

---

## v0.1 Signals

The first version should not attempt to calculate true Phi-Law constants.

Do not start with full K, C0, rho, or spectral operator algebra.

Start with operational proxies.

Minimum signal set:

| Signal | Meaning |
|---|---|
| Context entropy | Is the active context becoming noisy, fragmented, or contradictory? |
| Goal drift | Is the agent drifting away from the user's original intent? |
| Justification stability | Does the explanation remain stable under new evidence? |
| Memory pressure | Are compaction, resume, or subagent summaries threatening continuity? |
| Tool churn | Is the agent retrying, looping, or changing strategy without progress? |
| Contradiction load | Are unresolved contradictions accumulating? |

The output of v0.1 is `tau_hat`, an operational proxy for coherence.

```text
tau_hat before tau.
Sentinel before full Lovgiveren.
```

---

## Recommended Actions

Coherence Sentinel should emit one of the following recommended actions:

```text
CONTINUE
COMPACT
DELEGATE
ASK_USER
HUMAN_REVIEW
HALT
SLEEP_RECALIBRATE
```

The key new action is:

```text
SLEEP_RECALIBRATE
```

This is not ordinary context compaction.

Compaction reduces tokens.

Sleep/recalibration restores continuity.

---

## Sleep / Recalibrate

Sleep/recalibrate means:

```text
Stop the agentic loop.
Summarize what still matters.
Drop what must die.
Preserve what is framleis.
Restart with a clean coherence state.
```

This is the first engineering analogue of sleep in the Phi-Law architecture.

The agent does not merely keep working because it can.

It must periodically prove that it is still the process that should continue.

---

## Minimal Interface Sketch

```python
@dataclass(frozen=True)
class CoherenceSignals:
    goal_drift: float
    context_entropy: float
    justification_instability: float
    memory_pressure: float
    tool_churn: float
    contradiction_load: float

@dataclass(frozen=True)
class CoherenceState:
    tau_hat: float
    action: CoherenceAction
    reasons: list[str]
    previous_hash: str | None
    state_hash: str
```

The first implementation should be deterministic and testable.

No model call is required for v0.1.

---

## Non-Goals

This component does not claim to implement the full Phi-Law.

Out of scope for v0.1:

```text
- true spectral entropy of model weights
- true K calculation
- true C0 derivation
- rho calibration
- Hilbert-space identity formalism
- autonomous self-modification
```

Those belong to research, not the first engineering boundary.

---

## Design Boundary

Coherence Sentinel must not silently override lower-level safety controls.

It may recommend escalation, compaction, review, halt, or recalibration.

It must not bypass:

```text
- deny-first permission rules
- VAIG admissibility decisions
- WHY Gate continuity failures
- WORM audit requirements
- SSIP recovery semantics
```

If there is conflict, the more conservative decision wins.

---

## Why This Matters

Claude Code demonstrates the current production pattern:

```text
model proposes
harness executes
permissions gate
session records
context compacts
```

The next generation must add:

```text
coherence observes
continuity recalibrates
identity survives transformation
```

The future agent is not just a smarter model.

It is a governed runtime that knows when continued action would no longer be coherent.

---

## Short Definition

```text
Coherence Sentinel is a runtime observer that measures whether an agentic process remains coherent across iterative context transformation, tool execution, compaction, delegation, and recovery.
```

Tofoo version:

```text
Coherence Sentinel watches whether the agent is still framleis.
```
