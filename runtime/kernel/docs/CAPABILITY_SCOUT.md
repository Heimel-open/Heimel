# Capability Scout

Status: proposed general VALO capability
Owner: nsolland
Scope: cross-product (VALO, Heimel and future products)

## Purpose

Capability Scout continuously discovers external capabilities and skills that may reduce build effort, improve capability coverage, replace weaker implementations, or unlock new product behavior.

The Scout does not search for tools as an end in itself. It searches for useful capabilities.

A repository, MCP server, API, local model, SaaS service, CLI, agent package, library, hosted service or internal service is treated only as a possible capability provider.

## Core rule

Capability discovery is not capability authorization.

Finding a provider never grants it authority, credentials, network access, execution rights, data access or a direct effect path.

All execution remains subject to the normal VALO authority and evidence path.

## Pipeline

DISCOVER -> QUALIFY -> COMPARE -> WRAP -> REGISTER -> ROUTE -> GOVERN -> EXECUTE -> EVIDENCE

### 1. Discover

Search candidate sources including:

- GitHub repositories and releases
- MCP registries and servers
- public and private APIs
- local models and runtimes
- SaaS services
- package registries
- research code and reference implementations
- internal services

Discovery output must identify the actual capability, not merely the product name.

### 2. Qualify

For every candidate, capture at minimum:

- capability name and description
- provider and source
- input contract
- output contract
- side effects
- credentials and permissions required
- data accessed or disclosed
- execution location
- network requirements
- cost model
- expected latency
- rate or resource limits
- licence
- maintenance/activity signal
- maturity/reliability signal
- evidence/receipt support
- known failure modes
- consequence classes for which it may be admissible

Unknown fields remain UNKNOWN. Missing information must not be inferred into a positive qualification.

### 3. Compare

Compare the candidate against the current capability registry and active product needs.

The Scout should promote a candidate only when it can state one or more concrete deltas:

- fills a capability gap
- materially improves an existing capability
- replaces a more expensive implementation
- replaces a weaker or less maintainable implementation
- reduces operational effort
- enables a currently blocked product capability
- provides materially better evidence, reliability, latency or cost

Duplicate capability without a meaningful delta is noise and should be suppressed.

### 4. Wrap

Qualified providers are exposed behind a capability contract. Product code should depend on the contract, not the provider implementation where practicable.

A wrapper must make explicit:

- provider identity/version
- invocation contract
- authority requirements
- constraints
- side effects
- expected evidence
- failure semantics
- timeout/retry semantics

### 5. Register

Registration records capability availability. It does not grant execution authority.

The registry should support multiple providers for one capability and preserve provider/version lineage.

### 6. Route

Capability Route selects an admissible provider for a requested capability based on current requirements such as consequence, policy, locality, privacy, latency, cost, evidence and reliability.

The provider is an implementation choice. The capability is the stable abstraction.

### 7. Govern

Before consequence, the normal VALO path applies. Authority and constraints must be resolved fresh at execution/commit time. No provider receives an ungoverned direct effect path.

### 8. Evidence

Execution must return sufficient evidence to identify what capability ran, through which provider/version, under which authority/constraints, with what result and side effects.

## Scout output

The Scout is not a news feed.

It should produce concise actionable findings such as:

- `GAP`: capability missing from current registry
- `BETTER`: candidate materially improves an existing provider
- `REPLACE`: candidate can replace an internal or external dependency
- `PRODUCT_FIT`: candidate maps directly to a current product need
- `TEST`: candidate is promising but requires bounded evaluation
- `IGNORE`: duplicate, weak, stale, irrelevant or insufficiently evidenced

Each promoted finding should answer:

1. What capability does this provide?
2. What do we have today?
3. What is the material delta?
4. Where is it useful (VALO/Heimel/other)?
5. What authority, data or consequence risk does it introduce?
6. What is the cheapest bounded test that can validate the claimed value?

## Learning from rejection

Scout decisions should retain rejection reasons so repeated low-value patterns are suppressed. Rejection history is advisory filtering evidence, not authorization policy.

Examples:

- duplicate capability
- marketing-only project
- stale/unmaintained
- unacceptable licence
- excessive permission surface
- weak evidence
- no product fit
- worse than current provider
- unnecessary framework dependency

## Product examples

Roomit may consume discovered capabilities such as session replay, forms, UI components, persistence, notifications or billing without coupling its architecture to a specific provider.

Private products may consume discovered capabilities such as media generation, publishing, notifications, persistence or audience research while keeping Reality Engine/world state semantics independent from those providers.

## Non-goals

Capability Scout must not:

- autonomously install arbitrary software into production
- grant credentials or permissions
- bypass REHT/RACS or other consequence-time controls
- treat popularity as proof of capability
- replace bounded technical evaluation with README claims
- silently make a discovered framework the system architecture

## Architectural principle

External tools are capability providers, not the intelligence and not the authority layer.

The stable path is:

provider -> capability contract -> capability route -> authority/constraints -> governed execution -> evidence

The Scout exists to reduce human time spent finding and triaging those providers while preserving Handlingsrett.
