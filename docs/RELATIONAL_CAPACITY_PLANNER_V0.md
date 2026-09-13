# Relational Capacity Planner v0

The planner converts task structure into the minimum governed agent organization that can execute it under declared capability, authority, dependency and communication constraints.

Product position:
- Relational Capacity Planner is not a standalone product.
- It is a VALO capability: relational capacity + relational governance.
- VALO owns the infrastructure for selecting, constraining, sealing and verifying the task-specific agent organization.
- TraXin is the first commercial application: a need is matched to the smallest governed organization of capabilities/agents that can complete the work correctly.

Input:
- required contributions;
- capability required for each contribution;
- optional authority scope per contribution;
- causal dependency graph;
- optional coordination-depth budget;
- candidate agents with capabilities, authority scopes and mutually permitted peers.

Output:
- selected agents;
- contribution-to-agent assignments;
- only the inter-agent relations required by the dependency graph;
- dependency depth.

The planner fails closed when capability is missing, authority is missing, the dependency graph is cyclic, the coordination-depth budget is exceeded, or required inter-agent communication is not mutually permitted.

v0 deliberately does not create emergent channels, delegation paths or communication edges. A relation exists in the plan only when the task requires it and the governed workspace already permits it.

For bounded candidate sets, v0 enumerates organizations by increasing size and returns the first deterministic feasible assignment. The optimization target is minimum selected-agent count subject to governance constraints. It is not yet cost-, latency-, reliability- or X3-threshold-aware.

The resulting plan can now be sealed into a deterministic relational contract. The contract binds:
- exact task id;
- exact selected agent set;
- exact contribution assignments;
- exact source/target relation pairs;
- exact purpose for every permitted relation;
- dependency depth.

The contract digest is recomputed from a canonical payload. Any mutation to membership, assignment, relation, purpose or depth invalidates the seal. Workspace enforcement can then fail closed unless an attempted agent-to-agent interaction exactly matches a relation in the sealed contract.

This contract is a coordination boundary, not execution authority. It does not authorize external effects and cannot substitute for fresh consequence-time authority in the normal VALO path.

Research connection: X3 R241-R245 motivates treating relational structure as a capacity variable rather than metadata. The production boundary remains strict: the research results are evidence for planner design, not runtime authorization.

Commercial application — TraXin:
A work request can be decomposed into necessary contributions and dependencies; the planner selects the smallest feasible governed organization; VALO seals the allowed coordination structure; execution remains subject to normal consequence-time authorization and evidence requirements. The result is not generic multi-agent orchestration, but a governed organization assembled for the exact work to be completed.

Next increments, only if product value warrants them:
1. cost/latency/reliability objective terms;
2. relational-capacity estimates from multiplicity, topology and causal depth;
3. bind the sealed relational contract into governed-workspace compilation/enforcement;
4. planner/execution comparison evidence: proposed graph vs executed graph.
