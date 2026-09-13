# Governed Intelligence Substrate v0

Status: architecture seed, not a Kernel responsibility.

## Primary objective

Define a provider-neutral runtime in which models are disposable compute payloads while model nodes, their admissible relationships, execution history, and governed composition can be selected as a capability fabric.

The substrate must never become an alternate authority or effect path. Kernel remains authoritative state; MAL/workspace admission constrains computation; REHT/RACS/Gateway govern consequence.

## System boundary

```text
hardware / accelerator pool
        |
model execution substrate
(load, unload, batch, schedule, isolate)
        |
Governed Intelligence Substrate
        |
  +-----+------+-------+
  |            |       |
node A       node B   node C
(model)      (model)  (tool/model)
  \            |       /
   +---- governed relational graph ----+
                    |
          capability composition
                    |
         candidate computation
                    |
      workspace conformance / MAL
                    |
          fresh Kernel context
                    |
              REHT -> RACS
                    |
                 Gateway
                    |
               REAL WORLD
```

## Model node

A model is not authority and not identity. It is a replaceable execution payload attached to a governed node.

A node descriptor SHOULD expose at least:

- node_id and model/provider/version identity
- capability declarations
- input/output modality
- accelerator, memory and locality requirements
- expected latency and marginal execution cost
- context and data-class admissibility
- purpose/tenant restrictions
- observed quality/reliability evidence
- local runtime state, if explicitly permitted
- available relationship types
- provenance for every mutable property

No descriptor property can manufacture authority, consent, delegation, clearance or standing.

## Relational graph

Routing is allowed to select a single node or a governed composition of nodes. Relationships are first-class runtime objects rather than hidden orchestration state.

Examples:

- verifier-of
- critic-of
- translator-for
- extractor-for
- fallback-for
- complementary-to
- requires
- excludes
- learned-effective-with

A relationship has explicit endpoints, scope, provenance, validity interval and admissibility constraints. Learned relationships are evidence, not authority.

This creates the experimental boundary needed to ask whether useful capability is node-local or relational without allowing emergent topology to bypass governance.

## Router objective

The router does not simply choose the cheapest model. It chooses an admissible execution graph under constraints.

Conceptually:

`route(task, governed_context, node_graph, resource_state) -> execution_graph`

The objective may optimize a policy-defined combination of:

- capability fit
- expected quality
- latency
- monetary/energy cost
- locality/privacy
- reliability
- historical performance
- relational/compositional evidence

Hard admissibility constraints dominate optimization. An inadmissible node or edge is never made admissible by a better score.

## Execution substrate boundary

The lower execution layer may reuse or adapt systems such as Superlinked SIE for commodity concerns:

- model loading/unloading
- GPU/accelerator scheduling
- batching
- queueing
- memory pressure / eviction
- OpenAI-compatible serving surfaces

These mechanisms are replaceable. VALO must not depend on SIE semantics for authority, state admission, governance or evidence integrity.

## Persistent state

Persistent node-local state is optional and explicit. It must be separable from model weights and from Kernel authoritative state.

The substrate may retain bounded operational evidence such as execution history, performance observations and explicitly admitted relational learning. It must not silently turn inference, cache, conversation history or model memory into operative enterprise state.

Any information proposed as persistent operative state follows normal Kernel State Admission.

## Split / merge / composition

The substrate SHOULD make topology operations observable:

- split a composition into constituent nodes
- merge nodes into a temporary execution group
- remove or replace one node
- reset or rewire relationships while preserving node-local state
- preserve relationships while replacing model payloads where semantically valid

These operations are important both operationally and experimentally: they permit measurement of whether capability survives node replacement, relationship reset, split, merge and component turnover.

## Evidence

Every routed execution SHOULD emit an execution receipt containing enough information to replay the routing decision and distinguish node-local from relational contribution where possible:

- task/capability request hash
- governed-context reference/hash
- candidate nodes considered
- hard exclusions and reasons
- selected execution graph
- model/provider/version identities
- relationship versions used
- resource snapshot relevant to routing
- routing policy/version
- outputs and evaluation references
- timestamps and provenance

Execution receipts grant no authority.

## Non-negotiable invariants

1. NO_DIRECT_EFFECT_PATH remains absolute.
2. Models, nodes, relationships and routing scores cannot create authority.
3. Kernel state outranks substrate cache, model memory and learned relationships.
4. Hard governance/admissibility constraints outrank optimization.
5. Provider/model replacement must not alter governance semantics.
6. Emergent or learned node relationships cannot escape the governed workspace.
7. External effect still requires fresh REHT/RACS authorization at consequence time.

## Initial implementation seam

Keep two layers separate:

1. `ModelExecutionAdapter`: load/invoke/unload/health/capacity primitives. SIE can be one implementation.
2. `GovernedNodeRouter`: node descriptors, admissible graph construction, relationship-aware routing and execution receipts.

This separation lets VALO use SIE immediately without making SIE the architecture, while leaving the node/relational substrate as VALO-owned logic.
