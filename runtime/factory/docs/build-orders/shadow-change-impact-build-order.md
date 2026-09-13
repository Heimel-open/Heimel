# Build Order — Shadow Change-Impact Capability

Owner: VALO Factory
Status: active delivery definition
Depends on: valo-kernel governed world state, REHT execution boundary, Veritas receipts, BARO divergence semantics

## Goal

Turn the generalized Readily method into a reusable platform capability for continuous sensing, impact propagation, simulation and governed response across compliance, operations, assets, workforce capacity, finance, software, suppliers, security and models.

## P0 — Contracts first

Define stable contracts before domain-specific agents:

- ObservationEnvelope
- ChangeObject
- ImpactEdge / ImpactSet
- SimulationRequest / SimulationResult
- EvidencePointer
- SensitivityClass
- Freshness / Validity window
- ProposedResponse
- AuthorizationImpact

Required invariants:

- observations are not facts by default
- provenance and time are mandatory
- sensitivity and egress policy are explicit
- every impact edge is explainable to its source/change object
- simulation output has no execution authority
- REHT is required before any real action
- receipts bind input state, simulation version, decision and outcome

## P1 — Shadow observer fabric

Implement a registry and runtime for narrow observers running close to source systems.

Initial adapter families:

- regulatory/standards
- contracts/suppliers
- software/repository/runtime
- assets/maintenance/sensors
- finance/market
- workforce/capacity at lawful, minimal granularity
- security/identity
- model/provider changes

Observers should emit deltas and evidence references, not bulk raw data.

## P2 — Change Impact Graph

Map ChangeObjects onto Kernel entities, relationships, obligations, constraints, resources, authority and workflows.

Provide deterministic traversal:

change -> impacted governed objects -> dependent workflows/resources/agents -> candidate simulations.

BARO consumes graph deltas to determine material divergence and trigger threshold.

## P3 — Factory simulation API

Factories consume a sealed world-state snapshot plus ImpactSet and generate multiple future-state branches.

Minimum scenarios:

- continue unchanged
- stop/defer
- modify controls/workflow
- substitute asset/provider/personnel capacity
- repair/replace/decommission
- step-up authority or review

Simulation results must include assumptions, uncertainty, resource impact, cost/risk/capacity impact and stop conditions.

## P4 — Historical replay

Replay previous receipts/events against proposed constraints or changed state.

Output concrete authorization deltas such as:

- historical ALLOW remains ALLOW
- ALLOW -> STEP_UP
- ALLOW -> MODIFY
- ALLOW -> DENY
- unresolved because evidence/state is insufficient

This is the bridge from Readily-style impact mapping to operational consequence testing.

## P5 — Trusted customer cloud deployment

Make trusted customer cloud the default enterprise reference architecture.

Run Shadow observers, local graphs, swarm/factories, Kernel-side state, VAIG/Judgment, REHT and Veritas inside a customer-controlled tenant/environment.

Controls:

- customer-owned data and keys
- private network/endpoints
- egress allow-list and policy enforcement
- JIT/JEA VALO operational access
- full admin/access receipts
- immediate customer revocation
- optional confidential computing
- no training on customer data

On-prem/air-gapped remains supported for stricter boundaries. Managed VALO cloud remains optional for lower-sensitivity workloads.

## P6 — Software Factory local swarm

Deploy discovery, execution and judgment agents inside the trusted customer boundary.

Create a local code/world graph so agents retrieve bounded task context instead of moving or repeatedly ingesting whole repositories.

External model broker must support customer-owned endpoints, local models, context minimization, egress classification and REHT authorization before sensitive context crosses the boundary.

## Acceptance gates

A delivery is acceptable when:

1. A synthetic change can be ingested and represented as a ChangeObject with provenance, time and sensitivity.
2. The impact graph deterministically identifies affected Kernel objects and workflows.
3. BARO can classify a meaningful divergence from the change.
4. A factory can simulate at least three future-state alternatives without execution authority.
5. Historical replay can show authorization deltas under the changed condition.
6. REHT is the only component able to clear a proposed real action.
7. Veritas can reconstruct observation -> state -> simulation -> authorization -> execution/outcome.
8. The full path can run without raw customer data leaving the customer-controlled boundary.

## Non-goals

- building a Readily clone
- centralizing raw customer data in VALO
- turning Shadow into a monolithic reasoning agent
- letting simulations self-authorize
- inferring sensitive individual health/psychological state without explicit lawful purpose and necessity

## Canonical principle

Data stays. Intelligence travels.

Shadow senses. Kernel holds state. BARO detects change. Factories explore futures. Judgment evaluates. REHT authorizes. Veritas proves.