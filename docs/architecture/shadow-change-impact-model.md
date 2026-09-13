# Shadow Change-Impact Model

Status: canonical architecture proposal

## Purpose

Adopt the useful pattern behind Readily as a general change-impact and evidence method, not as a healthcare-compliance copy.

The generalized loop is:

Source change -> normalize -> map to governed objects -> propagate dependencies -> detect gaps/divergence -> simulate alternatives -> assess impact -> authorize any real action -> record evidence -> recalibrate.

The same method must work across regulation, contracts, software, assets, maintenance, people/capacity, finance, suppliers, security, models and operational state.

## Responsibility split

### Shadow = distributed sensing and intelligence glue

Shadow is not one large agent and must not become the decision-maker.

Shadow is a mesh of narrow observers/speiders close to each source. Examples:

- regulatory and standards observers
- contract and supplier observers
- software/repository/runtime observers
- asset, sensor and maintenance observers
- financial and market observers
- workforce/capacity observers
- security and identity observers
- model/provider observers
- customer and operational-performance observers

Each observer emits a minimal structured Observation Envelope with:

- observation/event type
- affected entity or asset references
- source and provenance
- observation time and freshness
- confidence/uncertainty
- sensitivity classification
- evidence pointer/hash where allowed
- asserted scope and exclusions

An observation is not automatically a fact.

### Kernel = canonical world state

Kernel decides what the system currently holds as governed state. It resolves observations into facts, uncertainty, relationships, obligations, constraints, resources, authority and time-bounded state.

### BARO = divergence and change significance

BARO detects material divergence between expected state, observed state and governed state. It decides when a change is significant enough to trigger deeper analysis or simulation.

### Factories = simulation and future-state generation

Factories consume governed state plus observations and run:

- scenario simulation
- counterfactuals
- alternative-action comparison
- dependency propagation
- cost/risk/capacity projections
- failure and recovery simulations
- future-state generation

Factories answer "what happens if?"; they do not authorize production action.

### VAIG/Judgment = quality and admissibility assessment

VAIG/Judgment evaluates evidence quality, uncertainty, model admissibility, risk and whether a simulated result is fit to inform action.

### REHT = execution boundary

REHT remains the final authority boundary between analysis/simulation and real execution. Any proposed control, workflow, financial, maintenance, personnel-allocation, software or agent action must be revalidated against current authority and state at execution time.

### Veritas = evidence and outcome record

Veritas records what was observed, what state was used, what was simulated, what was authorized, what was actually executed and what outcome occurred.

## Generalized Readily pattern

The reusable pattern is a Change Impact Graph:

External/internal source change
-> structured Change Object
-> impacted entities/constraints/obligations
-> dependency traversal
-> affected workflows/assets/agents/people/resources
-> gap or divergence
-> replay/simulation
-> proposed response
-> judgment/admissibility
-> REHT authorization
-> execution
-> observed outcome
-> evidence/recalibration.

This is broader than compliance automation. Compliance becomes one domain adapter.

## Example domains

Regulation: new rule -> affected obligations/policies -> replay historical actions -> identify ALLOW/STEP_UP/DENY deltas before enforcement.

Contracts: changed term/SLA -> affected services, prices, suppliers and workflows -> simulate operational/economic impact.

Assets and depreciation: age, utilization, failure history and maintenance cost change -> simulate continue/repair/replace/decommission choices.

Maintenance: sensor or service-state change -> affected production dependencies -> failure probability and downtime scenarios -> authorize maintenance or continued operation.

Workforce/capacity: absence, turnover, workload, queue, overtime, competence coverage or error-rate changes -> team-level capacity/risk state -> simulate redistribution, automation or reduced load. Avoid individual health inference or surveillance unless explicitly lawful and necessary.

Finance: rates, FX, energy, commodity, margin or demand changes -> affected products/workflows/assets -> profitability and exposure scenarios.

Software: dependency/API/provider/repository/runtime change -> affected code paths, tests, workflows and agents -> local swarm analysis -> replay/test -> governed change proposal.

Security: vulnerability, credential, identity or policy change -> affected resources and delegations -> revoke/step-up/containment scenarios.

Models/providers: model version or provider-policy change -> affected admissibility, evaluations and workflows -> revalidation before use.

## Data-boundary rule

Canonical rule: data stays; intelligence travels.

Observers and factory execution should run as close to source data as practical. Shadow should propagate minimal structured observations, not raw sensitive datasets.

For deeper analysis, prefer governed query-to-data over bulk data movement.

## Enterprise deployment model

Canonical enterprise deployment is a customer-dedicated trusted cloud environment shared operationally under explicit delegation.

Customer controls:

- tenant/environment
- encryption keys
- raw data and repositories
- network boundary and egress
- access policy
- retention
- ability to revoke VALO access

VALO receives only delegated, least-privilege, time-bounded, fully logged operational rights to run and maintain the stack.

The complete stack may run inside the customer boundary:

Shadow observers -> Kernel -> BARO -> Factories/swarm -> VAIG/Judgment -> REHT -> RACS/external PEP -> Veritas.

Deployment classes:

1. Trusted customer cloud: default enterprise deployment; full stack and full context remain inside the customer-controlled boundary.
2. On-prem/private/air-gapped: for customers requiring physical, regulatory or sovereign isolation.
3. Managed VALO cloud: for lower-sensitivity workloads where the customer explicitly accepts it.

## Software Factory special case

Software Factory requires broad repository, dependency, test and runtime understanding, often using swarms of specialized agents. The swarm should therefore execute inside the trusted customer boundary.

Build a local code/world graph containing files, symbols, APIs, dependencies, ownership, tests, runtime signals, history, policies and evidence pointers. Agents retrieve only task-relevant context from the graph instead of repeatedly ingesting the whole estate.

Discovery, execution and judgment remain separated. Judgment should preferably use a different provider/model family where available to reduce correlated errors and self-attestation.

External model calls are allowed only through a governed model broker supporting:

- customer-owned provider endpoints where possible
- local models where appropriate
- context minimization
- egress classification
- REHT authorization before sensitive context leaves the boundary
- receipts for every external call

## Core invariant

Shadow sees.
Kernel holds governed truth/state.
BARO detects meaningful divergence.
Factories explore possible futures.
VAIG/Judgment assesses fitness and risk.
REHT decides whether a real action may proceed.
Veritas proves what happened.

No sensing, analysis, model or factory component gains execution authority merely because its inference is strong.