# RVM Edge Substrate Signal

Date: 2026-08-05
Status: Adopted external research signal
Source: https://github.com/ruvnet/rvm
Owner: VALO Research

## Signal

RVM is a Rust-based bare-metal runtime for agentic systems. Its architecture points toward agent execution moving below ordinary application and container layers and into memory, device access, accelerator access, isolation domains and microcontroller-class environments.

The strategic signal for VALO is not that RVM replaces execution governance. It is that the execution boundary is moving closer to the hardware and physical consequence.

## Relevant RVM capabilities

RVM presents a runtime model based on:

- capability-based access
- proof-gated state transitions
- time-bounded device leases
- isolation by agent or partition
- hash-chained witness records
- rollback and reconstruction
- deployment targets extending toward highly constrained edge devices

These capabilities are relevant as a possible substrate for governed edge execution.

## Canonical VALO interpretation

RVM determines where an agent runs, what technical capabilities it can reach, how it is isolated and how runtime transitions are witnessed.

VALO determines whether a specific consequential action has valid authority to occur at that moment.

RVM capability validity is not equivalent to execution authorization.

A valid capability can establish that an actor technically may access a resource. It does not by itself establish mandate, responsibility, admissibility, policy fit, contextual legitimacy or whether the action should be cleared now.

## Architectural relationship

The natural relationship is:

Agent
→ VAIG
→ REHT
→ RVM capability and proof gate
→ device lease or system call
→ physical or digital execution
→ RVM witness
→ Veritas receipt

Canonical boundary:

- VAIG evaluates evidence and uncertainty.
- REHT clears or rejects the proposed action at the execution boundary.
- RVM enforces technical capability, isolation and runtime transition constraints below that boundary.
- Veritas binds clearance, execution and observed outcome into the governed evidence chain.

RVM must not become the source of mandate or authorization in the VALO architecture.

## Product and research consequence

VALO Edge should integrate downward into bare-metal, embedded and device runtimes rather than attempt to replace them.

The integration contract should allow REHT clearance to bind to:

- exact action and parameters
- actor and principal
- mandate and scope
- device identity and attestation
- firmware, model and runtime hashes
- active capability or lease
- evidence age and provenance
- runtime state
- expiry and revocation state

The resulting clearance reference should be mechanically consumable by the RVM enforcement point and correlated with its witness output.

## Verification caution

RVM publishes extensive test and performance claims, but the repository also identifies at least one partition-switch benchmark as a stub and presents several figures as targets. Performance and implementation maturity must therefore be independently reproduced before being treated as verified.

This caution does not weaken the architectural signal. The important development is that agentic runtimes are moving governance-relevant control into kernel, memory, accelerator, device and microcontroller layers.

## Adopted conclusion

RVM is not classified as a direct VALO competitor.

It is classified as:

- an external edge-runtime signal
- a possible enforcement substrate beneath VALO
- a potential adapter and integration target for micro-REHT and Veritas Edge
- evidence that execution governance must extend to the lowest consequential runtime boundary

Canonical formulation:

“RVM determines where agentic execution can run. VALO determines whether the action is authorized to become real.”
