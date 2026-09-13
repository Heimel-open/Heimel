# External Signal: Dawn Industries VIM — Physical Recovery Authorization

Date: 2026-08-08
Source: https://www.linkedin.com/posts/y-combinator_dawn-industries-is-building-vim-a-system-activity-7491885958452408320-RN27

## Signal

Dawn Industries is building VIM for industrial robot and machine cells. The product pattern moves AI from diagnosis toward bounded physical recovery: observe PLC, robot, sensor and log state, identify a likely fault, propose a recovery action, and progress from recommendation and operator approval toward automation.

This is direct validation of the VALO Edge boundary. Machine safety and interlocks answer whether a command is technically safe enough to execute. They do not establish whether a specific agent is authorized to perform a specific write on a specific device under a valid mandate in the current state.

## VALO Edge adoption

Canonical path:

```text
local diagnosis / model proposal
→ Local VAIG evidence
→ exact recovery proposal
→ micro-REHT authorization
→ RACS outcome
→ Device Enforcement Gateway
→ PLC / robot / actuator command
→ Veritas observation and receipt
```

micro-REHT remains the only authorization boundary. The model, safety system and gateway never create authority.

## Required recovery bindings

A physical recovery authorization must bind at minimum:

- exact device or cell identity
- device attestation where available
- exact action type
- exact write-set: register, tag, parameter and intended value
- firmware and runtime hash; model hash when model identity is relevant to the mandate
- authority envelope, mandate and actor identity
- safety/interlock state as evidence input, never as authority
- required sensor provenance and freshness
- pre-action physical-state predicates
- bounded validity window and expiry
- nonce and one-use permit
- budgets for rate, duration, energy, value or other domain-specific exposure

## State drift

Authorization is invalid when material state changes between proposal and execution. The execution path must fail closed when the bound pre-action state, evidence freshness, software identity, mandate, revocation state or relevant safety state no longer matches the authorization commitment.

A stale recovery plan must be re-evaluated and re-authorized. The gateway must never reinterpret or repair a stale authorization.

## Rollback and recovery-after-failure

Rollback is a new physical consequence and therefore requires a separate proposal and separate micro-REHT authorization. The original recovery permit cannot implicitly authorize rollback, compensation or a second attempt.

Partial execution, timeout and failed execution must be represented as actual outcomes and preserved in Veritas evidence before any subsequent recovery action is considered.

## Product implication

Industrial recovery is a first-class VALO Edge reference case:

```text
AI can diagnose the machine.
Safety can constrain the machine.
REHT decides whether this exact intervention is authorized now.
```

The market transition from read-only industrial AI to write-capable recovery increases the need for runtime execution authority at the physical edge.
