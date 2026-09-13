# Execution Boundary Architecture

Status: active architecture  
Owner: VALO  
Scope: governed transition from AI proposal to external effect

## Core principle

Reasoning may be probabilistic. Execution authority must be governed deterministically.

The execution boundary separates proposal, governance evaluation, admissibility, enforcement and side effects.

## Active architecture

```text
User / Application / Ambient Overlay
                |
                v
          VALO Harness
   context, tools, workflows, routing
                |
                v
              VAIG
 runtime evidence, policy, risk, integrity
                |
                v
              REHT
     action admissibility semantics
                |
                v
          VALO Core
 deterministic state transitions and halt
                |
                v
            Execution

RACS defines contracts, messages and receipts across the path.
Speider and BARO provide observation and evidence upstream.
```

## Responsibility boundaries

### VALO Harness

Owns:

- context assembly
- model and tool routing
- workflow sequencing
- checkpointing and resume
- bounded retries and fallbacks
- sub-agent delegation
- trace and token accounting

Does not decide admissibility or execution clearance.

### VAIG

Owns:

- runtime evidence evaluation
- policy and authority inputs
- risk and uncertainty signals
- integrity and drift signals
- escalation and refusal preparation

VAIG evaluates conditions. It does not execute external effects.

### REHT

Owns the normative execution question:

```text
Is this action admissible to execute in the current state?
```

REHT considers authority, context, policy, evidence, state, risk and continuous validity.

### VALO Core

Owns:

- deterministic execution-state transitions
- allow, deny, defer, step-up and halt enforcement
- terminal-state integrity
- receipt-triggering invariants
- fail-closed behavior

Core does not reason, create policy or determine human legitimacy.

### RACS

RACS is the clean-room REHT Action Control Standard.

It standardizes:

- action envelope
- authority references
- evidence references
- policy references
- governance state
- decision state
- delegation metadata
- receipt contracts

RACS carries contracts. It does not make decisions.

### Speider and BARO

Speider collects and normalizes source material.

BARO observes patterns, drift, convergence and external reality. BARO produces evidence and never makes governance decisions.

## Execution pipeline

```text
Candidate action
-> governed context
-> runtime evaluation
-> admissibility decision
-> deterministic enforcement
-> external effect or refusal
-> receipt
```

No external effect may occur unless the current decision and state remain valid at the execution boundary.

## Continuous integrity

Authorization at the start is insufficient.

The system must be able to detect when:

- evidence becomes stale
- authority expires or changes
- policy changes
- context drifts
- risk increases
- execution diverges from the approved action
- the environment enters an invalid state

A previously admissible action may therefore be deferred, stepped up or halted before completion.

## Formal boundary

Formal verification claims apply only to the specified state machine and tested invariants. They do not prove:

- truth of external evidence
- correctness of sensors
- legal compliance as a whole
- moral correctness
- physical-system safety beyond the modeled boundary

The TLA+ specification, model checking and related verification evidence are Solland/VALO contributions. The jointly authored MECHA paper remains a separate historical publication with its own explicit contribution split under Zenodo DOI `10.5281/zenodo.20668225`.

## Historical terminology

Earlier drafts used:

- ACS / VACS
- Phi Runtime
- MECHA as an active architecture dependency
- IGL as an execution-boundary dependency

Those terms are historical or external in the current VALO architecture. They are not required runtime dependencies.

Current terms are:

- RACS for protocol contracts
- REHT for admissibility semantics
- VALO Core for deterministic enforcement
- explicit human and organizational authority inputs rather than a collaborator-specific framework

## Architectural invariant

```text
No action crosses the execution boundary unless the action,
its authority, evidence, policy, context and current state
remain admissible at the moment of effect.
```

## Claim maturity

Every implementation claim must be labeled as one of:

- proposed
- specified
- implemented
- tested
- formally checked
- externally validated
- production deployed

AI-generated agreement, repeated wording or multi-model consensus is not independent validation.
