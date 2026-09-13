# relAIon repository boundary

Canonical home: `nsolland/PersonalAI-OS`.

PersonalAI-OS owns:

- relAIon identity and seed
- Alpha developmental state
- operative memory and forgetting semantics
- self-model and continuity
- learned proficiency and skill-use semantics
- relationships and social development
- Nursery and sleep/consolidation semantics
- capability-provider relationship from Alpha's perspective

valo-platform owns:

- REHT/RACS and execution governance
- generic gateways and evidence infrastructure
- generic append-only history primitives
- generic bitemporal/context compilation primitives
- governed effect paths

Cross-repository rule:

PersonalAI-OS may consume generic primitives from valo-platform. valo-platform must not become the semantic authority for Alpha's identity, development or personal memory.

If a generic primitive was first prototyped in valo-platform, keep the generic primitive there and move the relAIon-specific policy/meaning here.

## Context is a governed projection of history

Context is not memory.

Canonical history and personal memory remain authoritative sources. The model receives only a task-appropriate, governed projection compiled from that history and state.

The canonical flow is:

`history -> graph -> context compiler -> model`

This means:

- a larger context window does not become memory
- retrieval does not become identity or authority
- model-side context retention does not become canonical state
- compaction, embeddings, Git, graph storage, retrieval engines, and frontier-model context mechanisms remain subordinate implementation layers
- context compilation must preserve provenance and be reconstructable
- compiled context must never grant authority that is absent from canonical governed state

Model providers may improve long-context reasoning, retrieval, or goal retention. Those improvements are capability-provider improvements only. They do not move ownership of identity, memory, history, authority, or context policy into the model layer.

The architectural principle is therefore:

> Context is not memory. Context is a governed projection of history.
