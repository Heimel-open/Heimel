# Capability providers

PersonalAI/relAIon treats external platforms, harnesses, runtimes, MCP servers, SaaS backends, local tools, regional models and frontier services as replaceable capability providers.

## Governing rule

A capability provider supplies capability. It does not acquire governing authority by being connected.

The provider may expose its own authentication, roles, permissions, policies and guardrails. These are provider-local facts and constraints. They are inputs to the governed decision path, not the canonical authority model.

Canonical effect path:

`model/agent -> capability middleware -> governed effect path -> REHT/RACS -> consequence -> evidence`

No provider may create a direct effect path that bypasses fresh consequence-time authorization. Authority, identity, purpose, delegation, constraints and execution rights remain governed by the PersonalAI/VALO architecture. Effects must remain attributable and evidentiary.

## Capability middleware contract

The middleware is the stable boundary between relAIon/PersonalAI and a changing capability ecosystem. Models, tools, runtimes, open-source projects, MCP servers, local accelerators and hosted services may appear and disappear without redefining the agent.

The middleware owns four functions:

1. **Discovery** — determine which capabilities are actually available now, including local device capabilities, installed runtimes, tools, skills, MCP services, regional services and frontier providers. Discovery is runtime truth, not a static assumption.
2. **Admissibility and selection** — filter discovered capabilities through purpose, disclosure/privacy constraints, authority, execution rights, locality requirements and other governed constraints before optimizing among admissible options for quality, latency, cost, availability and reliability.
3. **Adapters** — expose a stable capability contract upward while translating to provider-specific APIs, model formats, tool schemas, runtimes, hardware accelerators and protocols downward.
4. **Capability stripping** — when adopting open-source software or external harnesses, retain only the capability required. Provider-owned agent loops, identity, memory, goals, authority models, control planes, telemetry, policy layers or unnecessary dependencies must be removed, disabled, sandboxed or subordinated unless explicitly required.

Canonical middleware path:

`capability request -> discover -> admit/filter -> select -> adapt -> execute -> verify -> return result + evidence`

The middleware may know that a capability exists. That does not imply permission to use it. Discovery and authority are separate concerns.

The middleware may select how an already-admissible capability is realized. It may not silently redefine why the capability is needed, what the primary objective is, who has authority, or what consequences are allowed.

## Provider lifecycle

Providers are borrowed, not owned by the architecture.

A provider must be addable, removable or replaceable without changing relAIon identity, canonical memory, goals, authority, governance semantics or upstream capability contracts.

Where an external project contains useful implementation mechanisms, PersonalAI may initially use it behind an adapter and progressively internalize the required mechanisms over time. Internalization must preserve the middleware contract so that upstream behavior does not depend on the original provider.

This applies equally to local inference substrates, model gateways, hosted compute, open-source tools, MCP servers and future capability sources.

## Provider families

### RunAnywhere

RunAnywhere is adopted as a candidate local intelligence substrate and reference implementation for discovery, runtime abstraction and device-local execution.

Useful mechanisms include runtime capability discovery, model/runtime abstraction and execution across heterogeneous local hardware. PersonalAI may use RunAnywhere behind the middleware to realize local capabilities without exposing hardware/runtime details to relAIon.

RunAnywhere must not become the PersonalAI control plane. Its agent loops, model management, routing, telemetry or provider-local policy remain subordinate to the middleware and governed effect path.

Long term, the relevant mechanisms may be implemented natively. RunAnywhere is therefore both a provider and an architectural reference, not a permanent dependency.

Source/context: https://www.runanywhere.ai/

### OpenRouter

OpenRouter is a candidate hosted model-access provider behind the same middleware boundary.

It may supply model availability, provider access and model-routing options. These are execution choices, not governing decisions. PersonalAI must determine admissibility, disclosure boundaries, purpose, authority and locality constraints before any request is eligible for OpenRouter routing.

Model/provider choice may therefore be delegated downward only after the admissible set has been established by the governed middleware.

Source/context: https://openrouter.ai/

### ZeroGPU

ZeroGPU is a candidate hosted compute/capability provider for workloads that benefit from externally supplied GPU capacity.

It is treated as borrowed compute behind an adapter. Availability of GPU capacity does not imply authority to disclose data or execute a workload remotely. The middleware must first establish that remote execution is admissible and then expose only the least necessary task/data surface.

ZeroGPU-specific scheduling, environment and runtime details remain provider-local and replaceable.

## Contextual capability selection

Capability selection is a runtime reasoning process, not a fixed toolbox attached to an agent.

Canonical lifecycle:

`objective + context -> capability need -> lookup -> compare -> governed decision -> temporary bind -> execution -> release`

The agent first reasons about the capability actually required by the objective and current context. Only then does it discover candidate providers. Candidates are compared against relevant context and constraints such as task fit, existing architecture, language/runtime, authority, risk, compliance, locality, cost, latency and availability.

Discovery must therefore not lead reasoning: the set of available tools must not silently redefine the problem or the primary objective.

A selected provider is temporarily bound to the task. Selection does not grant authority. The provider remains subordinate to consequence-time authorization and the canonical governed effect path. After the scoped use, the binding is released; the provider does not become part of agent identity merely because it was previously useful.

Provider or model recommendations are proposals, not authority. Product descriptions, defaults, rankings and model preferences may influence discovery evidence, but cannot independently determine execution rights.

This yields the operational sequence:

`reason -> lookup -> compare -> decide -> bind -> use -> release`

and preserves the architectural rule:

`identity != toolbox`

External empirical support: Armature's coding-agent study found substantial variation in tool selection across agents and repository contexts, reinforcing that capability choice is contextual rather than a stable property of agent identity.

Source/context: https://armature.tech/blog/which-tools-coding-agents-install

## One fractal architecture

Fractal compute is not a separate architecture. It is the same recursive node -> middleware -> supernode architecture instantiated over models and compute.

The governing pattern is singular: nodes expose capabilities; middleware discovers and routes those capabilities; supernodes compose work and results. The same pattern recursively applies to intelligence, capabilities, models, compute and routing. These are manifestations of one architecture, not independent architectural layers or tracks.

A model is therefore simply one possible capability provider/node. A job is not bound to one model, machine or tier. It may be decomposed into independently routable subjobs. Each subjob is assigned to the smallest sufficient available capability according to task requirements such as capability, latency, cost, confidence, privacy, hardware and availability. Subjobs may execute concurrently across local models, local nodes, regional nodes, supernodes or frontier providers. Their results are composed by a parent node, which may itself be only one subjob inside a larger job.

The recursive pattern is:

`node -> middleware -> supernode`

Applied to work:

`job -> subjobs -> capability routes -> nodes/models -> partial results -> parent composition`

Any node may act simultaneously as executor, decomposer, composer and child of another node. The same orchestration contract applies from multiple models on one machine through machines, clusters, regions and supernodes-of-supernodes. There is no architectural requirement for a fixed number of tiers.

Local versus cloud is not the governing abstraction. The router asks whether the work can be satisfied at the current locality and escalates only when necessary. As local capability improves, work naturally collapses downward without changing the architecture.

Terms such as fractal intelligence, fractal compute and fractal routing describe properties or views of this one recursive architecture. They must not be promoted into separate governing architectures.

The middleware is the connective tissue: discovery, decomposition, routing, provider adaptation, composition and evidence propagation. It must not assume that any capability permanently belongs to a particular locality, model class or provider.

Recursive decomposition does not relax governance. Every effectful branch remains subordinate to the primary objective and the canonical governed effect path. Splitting work cannot split, manufacture or bypass authority. Parent composition must preserve provenance so the resulting outcome can be traced to the subjobs, providers and evidence that produced it.

## Causal-relational parallel displacement

Fractal Monte Carlo-style population search is useful as a precursor for parallel displacement: many concurrent branches explore alternative trajectories, weak branches can lose compute, and promising branches can receive more compute. PersonalAI generalizes this from homogeneous walkers over a fixed state-space distance metric to heterogeneous intelligence allocation over task trajectories.

The important difference is that branch distance is not assumed to be known in advance.

For relAIon, relevant separation is causal and relational, not merely representational. Two branches may look different while depending on the same causal structure, and two nearly identical branches may sit on opposite sides of a small relational change that later produces radically different reachable futures. History, ordering and relational structure therefore participate in the geometry.

This means the geometry used for compute allocation may itself be unresolved while exploration is running:

`partial relational state -> provisional geometry -> parallel exploration -> new relations/order -> geometry reorientation -> revised causal distance -> compute reallocation`

Accordingly, early pruning must distinguish at least three cases:

- known redundant: safe candidate for pruning or collapse
- known materially relevant: candidate for additional compute
- geometrically unresolved: preserve at the cheapest sufficient level until later relational evidence can orient the space

UNKNOWN causal significance must not be treated as low significance.

Compute allocation should therefore not optimize for superficial answer diversity. It should preserve materially distinct or still-unresolved causal geometries long enough to determine whether they change the primary objective's reachable outcome space.

A useful conceptual replacement for simple `reward × distance` is:

`branch utility × causal-relational significance`

where causal-relational significance may remain provisional or UNKNOWN until sufficient history, ordering and relationship structure has accumulated.

The resulting rule is:

- branches remain subordinate to the primary objective
- compute may move between branches dynamically
- branches may recursively decompose and escalate to different capability classes
- redundant branches may collapse
- materially divergent branches may expand
- unresolved geometry is preserved rather than prematurely discarded
- parent composition re-evaluates branch relationships as the causal geometry becomes better oriented

This makes parallel displacement more than exploration/exploitation. It is also preservation of unresolved geometry while the system learns the geometry of the causal cone it is traversing.

Reference precursor: Fractal Monte Carlo / Fractal AI, arXiv:1803.05049.

### Zite

Zite is adopted as a candidate software capability provider/backend.

Useful capabilities include business-software infrastructure such as data, authentication, roles/permissions, deployment/runtime and agent-accessible operations through MCP. PersonalAI may route appropriate software-building or application capabilities to Zite when it is the best available provider.

Zite is explicitly not adopted as the governance layer. Zite-local roles and permissions do not replace REHT/RACS authority resolution. They remain provider-local constraints and evidence inputs.

This preserves provider replaceability: Zite can be added, removed or substituted without redefining PersonalAI identity, memory, authority, governance or the canonical governed effect path.

Source/context: https://lnkd.in/p/eDGSTQ9X

## DBX

DBX is adopted as a candidate database capability provider and adapter layer.

DBX exposes a broad database surface through MCP and CLI, including connection discovery, schema inspection/context, SQL execution, Redis and MongoDB operations, with local, Web and Docker execution paths. PersonalAI may route database capabilities through DBX rather than owning a bespoke connector for every supported database.

DBX remains subordinate and replaceable. Its connection allowlists, read/write modes, SQL safety checks, authentication and other provider-local controls are useful defense-in-depth constraints, but they do not define canonical authority or execution rights.

The governed route is:

`model/agent -> capability route -> REHT/RACS consequence-time authorization -> DBX adapter/MCP -> database -> effect evidence`

A DBX operation that can mutate external state must not obtain authority merely because DBX permits it. Purpose, identity, delegation, scope, constraints and execution rights are resolved by PersonalAI/VALO before the consequential operation. The resulting effect and relevant provider evidence must remain attributable and replayable.

Schema discovery and read-only inspection may be exposed as lower-risk capabilities under explicit scope. Write, destructive, connection-management and high-risk operations remain governed effects and fail closed when authority cannot be established.

DBX can therefore be added, removed or replaced without redefining PersonalAI identity, memory, authority, governance or the canonical governed effect path.

Source/context: https://github.com/t8y2/dbx

## Design invariant

Capabilities are stable concepts. Providers, models, runtimes, hardware and tools are transient implementations.

The middleware therefore owns the capability abstraction, not the provider.

**Borrow the capability. Do not adopt the system.**
