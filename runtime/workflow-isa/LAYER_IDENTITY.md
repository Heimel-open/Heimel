# Layer identity

`valo-workflow-isa` owns **execution flow only**. It has no evaluative identity
and no authority.

Canonical ownership:

- Goal Compiler compiles society functions to Function Graphs.
- Workflow ISA compiles/validates Workflow Graphs and executes flow
  deterministically. It never decides, authorizes, or owns state.
- VALO Kernel owns authoritative world state. Workflow ISA reads it through
  typed Kernel queries only.
- REHT is the sole execution authorization boundary.
- RACS is immutable decision-contract data.
- VALO Gateway mechanically enforces an already-issued clearance and permit.
- Veritas records execution attempts and observable outcomes.
- BARO verifies expected postconditions against observed state.

Forbidden here: LLM planning, policy interpretation, authority creation,
authorization decisions, direct state mutation, direct storage access, and any
claim that the workflow runtime owns the truth.

Workflow ISA owns: node classes (READ/COMPUTE/DECIDE/WAIT/WRITE), control flow,
typed composition, static compilation, durable execution, events, call stack,
and the ports toward Kernel/REHT/RACS/Gateway/Veritas/BARO.
